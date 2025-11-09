"""
Production-ready regex engine with timeout protection and cross-platform support.

This module provides a robust regex execution engine that:
- Supports multiple backends (regex module, threading, signals)
- Provides timeout protection against catastrophic backtracking
- Caches compiled patterns for performance
- Tracks metrics for monitoring
- Works across all platforms (Windows, Linux, macOS)
"""

import logging
import queue
import re
import sys
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from re import Match, Pattern
from typing import Any, Callable, Optional, Union

# Try to import the regex module (better timeout support)
try:
    import regex  # type: ignore[import-untyped]

    REGEX_AVAILABLE = True
except ImportError:
    REGEX_AVAILABLE = False

# Check if we're on a Unix system (for signal-based timeouts)
SIGNALS_AVAILABLE = hasattr(sys, "platform") and sys.platform != "win32"
if SIGNALS_AVAILABLE:
    import signal


# ============================================================================
# Configuration and Enums
# ============================================================================


class TimeoutBehavior(Enum):
    """Defines behavior when a regex operation times out."""

    RAISE_EXCEPTION = "raise"  # Raise RegexTimeoutError
    RETURN_NONE = "return_none"  # Return None/empty result
    RETURN_ORIGINAL = "original"  # Return input unchanged (current behavior)
    LOG_AND_CONTINUE = "log"  # Log error and return None


class BackendPriority(Enum):
    """Priority order for backend selection."""

    REGEX_MODULE = 1  # Best: native timeout support, cross-platform
    THREADING = 2  # Good: works everywhere, some overhead
    SIGNAL = 3  # OK: Unix only, not thread-safe
    FALLBACK = 4  # Last resort: no timeout protection


@dataclass
class RegexConfig:
    """Configuration for regex engine behavior."""

    # Timeout settings
    default_timeout: float = 1.0  # Default timeout in seconds
    timeout_behavior: TimeoutBehavior = TimeoutBehavior.RAISE_EXCEPTION

    # Operation-specific timeouts
    compile_timeout: float = 1.0
    search_timeout: float = 0.5
    sub_timeout: float = 2.0
    findall_timeout: float = 3.0

    # Caching
    cache_size: int = 128  # Number of compiled patterns to cache
    cache_enabled: bool = True

    # Monitoring
    enable_metrics: bool = True
    log_slow_patterns: bool = False
    slow_threshold_ms: float = 100.0

    # Backend selection
    preferred_backend: Optional[str] = None  # None = auto-select
    allow_fallback: bool = True  # Allow fallback to weaker backends

    # Logging
    logger: Optional[logging.Logger] = None


# ============================================================================
# Exceptions
# ============================================================================


class RegexTimeoutError(Exception):
    """Raised when a regex operation exceeds its timeout."""

    def __init__(
        self,
        pattern: str,
        input_length: int,
        timeout: float,
        backend: str,
        operation: str = "search",
    ):
        self.pattern = pattern
        self.input_length = input_length
        self.timeout = timeout
        self.backend = backend
        self.operation = operation

        # Truncate pattern for display
        pattern_display = pattern[:100] + "..." if len(pattern) > 100 else pattern

        message = (
            f"Regex {operation} timed out after {timeout}s\n"
            f"Pattern: {pattern_display}\n"
            f"Input length: {input_length} chars\n"
            f"Backend: {backend}\n"
            f"Suggestion: Simplify pattern, increase timeout, or check for "
            f"catastrophic backtracking"
        )
        super().__init__(message)


class RegexBackendError(Exception):
    """Raised when no suitable regex backend is available."""


# ============================================================================
# Metrics Tracking
# ============================================================================


@dataclass
class RegexMetrics:
    """Tracks regex operation statistics."""

    total_operations: int = 0
    timeouts: int = 0
    errors: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

    # Pattern -> timeout count
    timeout_patterns: dict[str, int] = field(default_factory=dict)

    # Pattern -> list of execution times (ms)
    pattern_timings: dict[str, list[float]] = field(default_factory=dict)

    # Lock for thread-safe updates
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def record_operation(self) -> None:
        """Record a regex operation."""
        with self._lock:
            self.total_operations += 1

    def record_timeout(self, pattern: str) -> None:
        """Record a timeout event."""
        with self._lock:
            self.timeouts += 1
            self.timeout_patterns[pattern] = self.timeout_patterns.get(pattern, 0) + 1

    def record_error(self) -> None:
        """Record an error event."""
        with self._lock:
            self.errors += 1

    def record_cache_hit(self) -> None:
        """Record a cache hit."""
        with self._lock:
            self.cache_hits += 1

    def record_cache_miss(self) -> None:
        """Record a cache miss."""
        with self._lock:
            self.cache_misses += 1

    def record_timing(self, pattern: str, duration_ms: float) -> None:
        """Record pattern execution time."""
        with self._lock:
            if pattern not in self.pattern_timings:
                self.pattern_timings[pattern] = []
            # Keep only last 100 timings per pattern to avoid unbounded growth
            if len(self.pattern_timings[pattern]) >= 100:
                self.pattern_timings[pattern].pop(0)
            self.pattern_timings[pattern].append(duration_ms)

    def get_slowest_patterns(self, n: int = 10) -> list[tuple[str, float]]:
        """Get N slowest patterns by average execution time."""
        with self._lock:
            averages = [
                (pattern, sum(times) / len(times))
                for pattern, times in self.pattern_timings.items()
                if times
            ]
            return sorted(averages, key=lambda x: x[1], reverse=True)[:n]

    def get_timeout_rate(self) -> float:
        """Get percentage of operations that timed out."""
        with self._lock:
            if self.total_operations == 0:
                return 0.0
            return (self.timeouts / self.total_operations) * 100.0

    def get_cache_hit_rate(self) -> float:
        """Get cache hit rate percentage."""
        with self._lock:
            total = self.cache_hits + self.cache_misses
            if total == 0:
                return 0.0
            return (self.cache_hits / total) * 100.0


# ============================================================================
# Pattern Cache
# ============================================================================


class PatternCache:
    """Thread-safe LRU cache for compiled regex patterns."""

    def __init__(self, maxsize: int = 128):
        self.maxsize = maxsize
        self._lock = threading.RLock()
        # Key: (pattern, flags, backend_name) -> compiled pattern
        self._cache: dict[tuple[str, int, str], Any] = {}
        # Track access order for LRU
        self._access_order: list[tuple[str, int, str]] = []

    def get(self, pattern: str, flags: int, backend_name: str) -> Optional[Any]:
        """Get cached compiled pattern."""
        key = (pattern, flags, backend_name)

        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                self._access_order.remove(key)
                self._access_order.append(key)
                return self._cache[key]
            return None

    def put(self, pattern: str, flags: int, backend_name: str, compiled: Any) -> None:
        """Add compiled pattern to cache."""
        key = (pattern, flags, backend_name)

        with self._lock:
            # If already cached, update and move to end
            if key in self._cache:
                self._access_order.remove(key)
                self._cache[key] = compiled
                self._access_order.append(key)
                return

            # Check if cache is full
            if len(self._cache) >= self.maxsize > 0:
                # Remove least recently used
                oldest = self._access_order.pop(0)
                del self._cache[oldest]

            # Add new entry
            self._cache[key] = compiled
            self._access_order.append(key)

    def clear(self) -> None:
        """Clear all cached patterns."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()

    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)


# ============================================================================
# Abstract Backend Interface
# ============================================================================


class RegexBackend(ABC):
    """Abstract interface for regex backends."""

    def __init__(self, config: RegexConfig):
        self.config = config
        self.metrics = RegexMetrics() if config.enable_metrics else None

    @abstractmethod
    def compile_pattern(self, pattern: str, flags: int = 0) -> Pattern[str]:
        """Compile a regex pattern."""

    @abstractmethod
    def search(
        self,
        pattern: Pattern[str],
        string: str,
        timeout: Optional[float] = None,
    ) -> Optional[Match[str]]:
        """Search with timeout protection."""

    @abstractmethod
    def match(
        self,
        pattern: Pattern[str],
        string: str,
        timeout: Optional[float] = None,
    ) -> Optional[Match[str]]:
        """Match with timeout protection."""

    @abstractmethod
    def sub(
        self,
        pattern: Pattern[str],
        repl: Union[str, Callable[[Match[str]], str]],
        string: str,
        count: int = 0,
        timeout: Optional[float] = None,
    ) -> str:
        """Substitute with timeout protection."""

    @abstractmethod
    def findall(
        self,
        pattern: Pattern[str],
        string: str,
        timeout: Optional[float] = None,
    ) -> list[str]:
        """Find all matches with timeout protection."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Backend name for logging/metrics."""

    @property
    @abstractmethod
    def priority(self) -> BackendPriority:
        """Backend priority for auto-selection."""

    @property
    @abstractmethod
    def supports_timeout(self) -> bool:
        """Whether this backend supports true timeouts."""

    def _record_metrics(
        self, operation: str, pattern_str: str, duration_ms: float
    ) -> None:
        """Record metrics if enabled."""
        if self.metrics:
            self.metrics.record_operation()
            self.metrics.record_timing(pattern_str, duration_ms)

            if (
                self.config.log_slow_patterns
                and duration_ms > self.config.slow_threshold_ms
            ):
                logger = self.config.logger or logging.getLogger(__name__)
                logger.warning(
                    f"Slow regex {operation} detected ({duration_ms:.2f}ms): "
                    f"pattern={pattern_str[:50]}"
                )


# ============================================================================
# Backend Implementations
# ============================================================================


class RegexModuleBackend(RegexBackend):
    """Backend using the 'regex' module with threading-based timeout."""

    def __init__(self, config: RegexConfig):
        if not REGEX_AVAILABLE:
            raise RegexBackendError("regex module not available")
        super().__init__(config)

    @property
    def name(self) -> str:
        return "regex_module"

    @property
    def priority(self) -> BackendPriority:
        return BackendPriority.REGEX_MODULE

    @property
    def supports_timeout(self) -> bool:
        # Uses threading-based timeout since regex 2.5.159 doesn't have native timeout
        return True

    def compile_pattern(self, pattern: str, flags: int = 0) -> Pattern[str]:
        """Compile using regex module."""
        try:
            return regex.compile(pattern, flags)  # type: ignore[no-any-return]
        except regex.error as e:
            # Convert regex.error to re.error for compatibility
            raise re.error(str(e), pattern, getattr(e, "pos", 0)) from e

    def _run_with_timeout(
        self,
        func: Callable[[], Any],
        timeout: float,
        pattern_str: str,
        input_length: int,
        operation: str,
    ) -> Any:
        """Run a function with threading-based timeout."""
        result_queue: queue.Queue = queue.Queue()
        exception_queue: queue.Queue = queue.Queue()

        def worker() -> None:
            try:
                result = func()
                result_queue.put(result)
            except Exception as e:
                exception_queue.put(e)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            # Timeout occurred
            if self.metrics:
                self.metrics.record_timeout(pattern_str)
            raise RegexTimeoutError(
                pattern_str, input_length, timeout, self.name, operation
            )

        # Check for exceptions
        if not exception_queue.empty():
            raise exception_queue.get()

        # Get result
        if not result_queue.empty():
            return result_queue.get()

        return None

    def search(
        self,
        pattern: Pattern[str],
        string: str,
        timeout: Optional[float] = None,
    ) -> Optional[Match[str]]:
        """Search using regex module with threading timeout."""
        start = time.perf_counter()

        try:
            # Only use timeout wrapper if timeout is explicitly set
            if timeout is not None or self.config.search_timeout > 0:
                timeout_val = (
                    timeout if timeout is not None else self.config.search_timeout
                )
                result = self._run_with_timeout(
                    lambda: pattern.search(string),
                    timeout_val,
                    pattern.pattern,
                    len(string),
                    "search",
                )
            else:
                # No timeout - run directly
                result = pattern.search(string)

            duration_ms = (time.perf_counter() - start) * 1000
            self._record_metrics("search", pattern.pattern, duration_ms)
            return result  # type: ignore[no-any-return]
        except RegexTimeoutError:
            raise
        except (regex.error, Exception):
            if self.metrics:
                self.metrics.record_error()
            raise

    def match(
        self,
        pattern: Pattern[str],
        string: str,
        timeout: Optional[float] = None,
    ) -> Optional[Match[str]]:
        """Match using regex module with threading timeout."""
        timeout_val = timeout or self.config.search_timeout

        try:
            return self._run_with_timeout(  # type: ignore[no-any-return]
                lambda: pattern.match(string),
                timeout_val,
                pattern.pattern,
                len(string),
                "match",
            )
        except RegexTimeoutError:
            raise
        except (regex.error, Exception):
            if self.metrics:
                self.metrics.record_error()
            raise

    def sub(
        self,
        pattern: Pattern[str],
        repl: Union[str, Callable[[Match[str]], str]],
        string: str,
        count: int = 0,
        timeout: Optional[float] = None,
    ) -> str:
        """Substitute using regex module with threading timeout."""
        start = time.perf_counter()
        timeout_val = timeout or self.config.sub_timeout

        try:
            result = self._run_with_timeout(
                lambda: pattern.sub(repl, string, count),
                timeout_val,
                pattern.pattern,
                len(string),
                "sub",
            )
            duration_ms = (time.perf_counter() - start) * 1000
            self._record_metrics("sub", pattern.pattern, duration_ms)
            return result  # type: ignore[no-any-return]
        except RegexTimeoutError:
            raise
        except (regex.error, Exception):
            if self.metrics:
                self.metrics.record_error()
            raise

    def findall(
        self,
        pattern: Pattern[str],
        string: str,
        timeout: Optional[float] = None,
    ) -> list[str]:
        """Find all using regex module with threading timeout."""
        timeout_val = timeout or self.config.findall_timeout

        try:
            return self._run_with_timeout(  # type: ignore[no-any-return]
                lambda: pattern.findall(string),
                timeout_val,
                pattern.pattern,
                len(string),
                "findall",
            )
        except RegexTimeoutError:
            raise
        except (regex.error, Exception):
            if self.metrics:
                self.metrics.record_error()
            raise


class SignalBackend(RegexBackend):
    """Backend using stdlib 're' with SIGALRM timeout (Unix only, not thread-safe)."""

    def __init__(self, config: RegexConfig):
        if not SIGNALS_AVAILABLE:
            raise RegexBackendError(
                "Signal-based timeout not available on this platform"
            )
        super().__init__(config)

    @property
    def name(self) -> str:
        return "signal_re"

    @property
    def priority(self) -> BackendPriority:
        return BackendPriority.SIGNAL

    @property
    def supports_timeout(self) -> bool:
        return True

    def compile_pattern(self, pattern: str, flags: int = 0) -> Pattern[str]:
        """Compile using stdlib re."""
        return re.compile(pattern, flags)

    def _run_with_threading_timeout(
        self,
        func: Callable[[], Any],
        timeout: float,
        pattern_str: str,
        input_length: int,
        operation: str,
    ) -> Any:
        """Run a function with threading-based timeout (fallback for non-main threads)."""
        result_queue: queue.Queue = queue.Queue()
        exception_queue: queue.Queue = queue.Queue()

        def worker() -> None:
            try:
                result = func()
                result_queue.put(result)
            except Exception as e:
                exception_queue.put(e)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            # Timeout occurred
            if self.metrics:
                self.metrics.record_timeout(pattern_str)
            raise RegexTimeoutError(
                pattern_str, input_length, timeout, self.name, operation
            )

        # Check for exceptions
        if not exception_queue.empty():
            raise exception_queue.get()

        # Get result
        if not result_queue.empty():
            return result_queue.get()

        return None

    def _run_with_signal_timeout(
        self,
        func: Callable[[], Any],
        timeout: float,
        pattern_str: str,
        input_length: int,
        operation: str,
    ) -> Any:
        """Run a function with signal-based timeout (Unix only, main thread only)."""
        # Signals only work in the main thread - fall back to threading for worker threads
        if threading.current_thread() != threading.main_thread():
            return self._run_with_threading_timeout(
                func, timeout, pattern_str, input_length, operation
            )

        def timeout_handler(signum: int, frame: Any) -> None:
            raise RegexTimeoutError(
                pattern_str, input_length, timeout, self.name, operation
            )

        # Set the signal handler and alarm
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.setitimer(signal.ITIMER_REAL, timeout)

        try:
            result = func()
            signal.setitimer(signal.ITIMER_REAL, 0)  # Cancel the alarm
            return result
        except RegexTimeoutError:
            signal.setitimer(signal.ITIMER_REAL, 0)  # Cancel the alarm
            if self.metrics:
                self.metrics.record_timeout(pattern_str)
            raise
        finally:
            signal.signal(signal.SIGALRM, old_handler)  # Restore old handler

    def search(
        self,
        pattern: Pattern[str],
        string: str,
        timeout: Optional[float] = None,
    ) -> Optional[Match[str]]:
        """Search using stdlib re with signal timeout."""
        start = time.perf_counter()
        timeout_val = timeout or self.config.search_timeout

        try:
            result = self._run_with_signal_timeout(
                lambda: pattern.search(string),
                timeout_val,
                pattern.pattern,
                len(string),
                "search",
            )
            duration_ms = (time.perf_counter() - start) * 1000
            self._record_metrics("search", pattern.pattern, duration_ms)
            return result  # type: ignore[no-any-return]
        except RegexTimeoutError:
            raise
        except Exception:
            if self.metrics:
                self.metrics.record_error()
            raise

    def match(
        self,
        pattern: Pattern[str],
        string: str,
        timeout: Optional[float] = None,
    ) -> Optional[Match[str]]:
        """Match using stdlib re with signal timeout."""
        timeout_val = timeout or self.config.search_timeout

        try:
            return self._run_with_signal_timeout(  # type: ignore[no-any-return]
                lambda: pattern.match(string),
                timeout_val,
                pattern.pattern,
                len(string),
                "match",
            )
        except RegexTimeoutError:
            raise
        except Exception:
            if self.metrics:
                self.metrics.record_error()
            raise

    def sub(
        self,
        pattern: Pattern[str],
        repl: Union[str, Callable[[Match[str]], str]],
        string: str,
        count: int = 0,
        timeout: Optional[float] = None,
    ) -> str:
        """Substitute using stdlib re with signal timeout."""
        start = time.perf_counter()
        timeout_val = timeout or self.config.sub_timeout

        try:
            result = self._run_with_signal_timeout(
                lambda: pattern.sub(repl, string, count),
                timeout_val,
                pattern.pattern,
                len(string),
                "sub",
            )
            duration_ms = (time.perf_counter() - start) * 1000
            self._record_metrics("sub", pattern.pattern, duration_ms)
            return result  # type: ignore[no-any-return]
        except RegexTimeoutError:
            raise
        except Exception:
            if self.metrics:
                self.metrics.record_error()
            raise

    def findall(
        self,
        pattern: Pattern[str],
        string: str,
        timeout: Optional[float] = None,
    ) -> list[str]:
        """Find all using stdlib re with signal timeout."""
        timeout_val = timeout or self.config.findall_timeout

        try:
            return self._run_with_signal_timeout(  # type: ignore[no-any-return]
                lambda: pattern.findall(string),
                timeout_val,
                pattern.pattern,
                len(string),
                "findall",
            )
        except RegexTimeoutError:
            raise
        except Exception:
            if self.metrics:
                self.metrics.record_error()
            raise


class StdlibBackend(RegexBackend):
    """Fallback backend using stdlib 're' module with threading-based timeout."""

    @property
    def name(self) -> str:
        return "stdlib_re"

    @property
    def priority(self) -> BackendPriority:
        return BackendPriority.FALLBACK

    @property
    def supports_timeout(self) -> bool:
        return True

    def compile_pattern(self, pattern: str, flags: int = 0) -> Pattern[str]:
        """Compile using stdlib re."""
        return re.compile(pattern, flags)

    def _run_with_timeout(
        self,
        func: Callable[[], Any],
        timeout: float,
        pattern_str: str,
        input_length: int,
        operation: str,
    ) -> Any:
        """Run a function with threading-based timeout."""
        result_queue: queue.Queue = queue.Queue()
        exception_queue: queue.Queue = queue.Queue()

        def worker() -> None:
            try:
                result = func()
                result_queue.put(result)
            except Exception as e:
                exception_queue.put(e)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            # Timeout occurred
            if self.metrics:
                self.metrics.record_timeout(pattern_str)
            raise RegexTimeoutError(
                pattern_str, input_length, timeout, self.name, operation
            )

        # Check for exceptions
        if not exception_queue.empty():
            raise exception_queue.get()

        # Get result
        if not result_queue.empty():
            return result_queue.get()

        return None

    def search(
        self,
        pattern: Pattern[str],
        string: str,
        timeout: Optional[float] = None,
    ) -> Optional[Match[str]]:
        """Search using stdlib re with threading timeout."""
        start = time.perf_counter()
        timeout_val = timeout or self.config.search_timeout

        try:
            result = self._run_with_timeout(
                lambda: pattern.search(string),
                timeout_val,
                pattern.pattern,
                len(string),
                "search",
            )
            duration_ms = (time.perf_counter() - start) * 1000
            self._record_metrics("search", pattern.pattern, duration_ms)
            return result  # type: ignore[no-any-return]
        except RegexTimeoutError:
            raise
        except Exception:
            if self.metrics:
                self.metrics.record_error()
            raise

    def match(
        self,
        pattern: Pattern[str],
        string: str,
        timeout: Optional[float] = None,
    ) -> Optional[Match[str]]:
        """Match using stdlib re with threading timeout."""
        timeout_val = timeout or self.config.search_timeout

        try:
            return self._run_with_timeout(  # type: ignore[no-any-return]
                lambda: pattern.match(string),
                timeout_val,
                pattern.pattern,
                len(string),
                "match",
            )
        except RegexTimeoutError:
            raise
        except Exception:
            if self.metrics:
                self.metrics.record_error()
            raise

    def sub(
        self,
        pattern: Pattern[str],
        repl: Union[str, Callable[[Match[str]], str]],
        string: str,
        count: int = 0,
        timeout: Optional[float] = None,
    ) -> str:
        """Substitute using stdlib re with threading timeout."""
        start = time.perf_counter()
        timeout_val = timeout or self.config.sub_timeout

        try:
            result = self._run_with_timeout(
                lambda: pattern.sub(repl, string, count),
                timeout_val,
                pattern.pattern,
                len(string),
                "sub",
            )
            duration_ms = (time.perf_counter() - start) * 1000
            self._record_metrics("sub", pattern.pattern, duration_ms)
            return result  # type: ignore[no-any-return]
        except RegexTimeoutError:
            raise
        except Exception:
            if self.metrics:
                self.metrics.record_error()
            raise

    def findall(
        self,
        pattern: Pattern[str],
        string: str,
        timeout: Optional[float] = None,
    ) -> list[str]:
        """Find all using stdlib re with threading timeout."""
        timeout_val = timeout or self.config.findall_timeout

        try:
            return self._run_with_timeout(  # type: ignore[no-any-return]
                lambda: pattern.findall(string),
                timeout_val,
                pattern.pattern,
                len(string),
                "findall",
            )
        except RegexTimeoutError:
            raise
        except Exception:
            if self.metrics:
                self.metrics.record_error()
            raise


# ============================================================================
# Main Regex Engine
# ============================================================================


class RegexEngine:
    """
    Main regex engine with automatic backend selection and timeout protection.

    This is the primary interface for all regex operations in jsonshiatsu.
    """

    _instance: Optional["RegexEngine"] = None
    _lock = threading.RLock()

    def __init__(self, config: Optional[RegexConfig] = None):
        self.config = config or RegexConfig()
        self.backend = self._select_backend()
        self.cache = (
            PatternCache(self.config.cache_size) if self.config.cache_enabled else None
        )
        self.logger = self.config.logger or logging.getLogger(__name__)

        # Log backend selection
        self.logger.info(f"RegexEngine initialized with backend: {self.backend.name}")

    def _select_backend(self) -> RegexBackend:
        """Select the best available backend."""
        # If user specified a preference, try that first
        if self.config.preferred_backend:
            if self.config.preferred_backend == "regex" and REGEX_AVAILABLE:
                return RegexModuleBackend(self.config)
            elif self.config.preferred_backend == "signal" and SIGNALS_AVAILABLE:
                return SignalBackend(self.config)
            elif self.config.preferred_backend == "stdlib":
                return StdlibBackend(self.config)
            else:
                # Preferred backend doesn't exist or not recognized
                if self.config.allow_fallback:
                    # Fall back to signal (if available) or stdlib
                    if SIGNALS_AVAILABLE:
                        return SignalBackend(self.config)
                    return StdlibBackend(self.config)
                else:
                    raise RegexBackendError(
                        f"Preferred backend '{self.config.preferred_backend}' not available"
                    )

        # No preference specified - auto-select by priority
        backends: list[tuple[BackendPriority, type[RegexBackend]]] = []

        # Priority 1: regex module (best)
        if REGEX_AVAILABLE:
            backends.append((BackendPriority.REGEX_MODULE, RegexModuleBackend))

        # Priority 2: signal-based (Unix only, works well)
        if SIGNALS_AVAILABLE:
            backends.append((BackendPriority.SIGNAL, SignalBackend))

        # Priority 3: stdlib fallback (last resort)
        if self.config.allow_fallback:
            backends.append((BackendPriority.FALLBACK, StdlibBackend))

        if not backends:
            raise RegexBackendError(
                "No regex backend available. Install 'regex' module: pip install regex"
            )

        # Sort by priority and create best backend
        backends.sort(key=lambda x: x[0].value)
        backend_class = backends[0][1]
        return backend_class(self.config)

    def _get_compiled_pattern(self, pattern: str, flags: int = 0) -> Pattern[str]:
        """Get compiled pattern from cache or compile new one."""
        # Check cache first
        if self.cache:
            cached = self.cache.get(pattern, flags, self.backend.name)
            if cached:
                if self.backend.metrics:
                    self.backend.metrics.record_cache_hit()
                return cached  # type: ignore[no-any-return]

        # Cache miss - compile pattern
        if self.backend.metrics:
            self.backend.metrics.record_cache_miss()

        compiled = self.backend.compile_pattern(pattern, flags)

        # Add to cache
        if self.cache:
            self.cache.put(pattern, flags, self.backend.name, compiled)

        return compiled  # type: ignore[no-any-return]

    def search(
        self,
        pattern: str,
        string: str,
        flags: int = 0,
        timeout: Optional[float] = None,
    ) -> Optional[Match[str]]:
        """
        Search for pattern in string with timeout protection.

        Args:
            pattern: Regex pattern string
            string: Input string to search
            flags: Regex flags (re.IGNORECASE, etc.)
            timeout: Timeout in seconds (None = use default)

        Returns:
            Match object if found, None otherwise

        Raises:
            RegexTimeoutError: If operation times out (depending on config)
        """
        compiled = self._get_compiled_pattern(pattern, flags)
        try:
            return self.backend.search(compiled, string, timeout)  # type: ignore[no-any-return]
        except RegexTimeoutError:
            return self._handle_timeout(pattern, string, "search")  # type: ignore[no-any-return]

    def match(
        self,
        pattern: str,
        string: str,
        flags: int = 0,
        timeout: Optional[float] = None,
    ) -> Optional[Match[str]]:
        """Match pattern at start of string."""
        compiled = self._get_compiled_pattern(pattern, flags)
        try:
            return self.backend.match(compiled, string, timeout)  # type: ignore[no-any-return]
        except RegexTimeoutError:
            return self._handle_timeout(pattern, string, "match")  # type: ignore[no-any-return]

    def sub(
        self,
        pattern: str,
        repl: Union[str, Callable[[Match[str]], str]],
        string: str,
        count: int = 0,
        flags: int = 0,
        timeout: Optional[float] = None,
    ) -> str:
        """
        Replace pattern matches in string with timeout protection.

        Returns original string on timeout (configurable).
        """
        compiled = self._get_compiled_pattern(pattern, flags)
        try:
            return self.backend.sub(compiled, repl, string, count, timeout)  # type: ignore[no-any-return]
        except RegexTimeoutError:
            return self._handle_timeout(pattern, string, "sub")  # type: ignore[no-any-return]

    def findall(
        self,
        pattern: str,
        string: str,
        flags: int = 0,
        timeout: Optional[float] = None,
    ) -> list[str]:
        """Find all non-overlapping matches."""
        compiled = self._get_compiled_pattern(pattern, flags)
        try:
            return self.backend.findall(compiled, string, timeout)  # type: ignore[no-any-return]
        except RegexTimeoutError:
            return self._handle_timeout(pattern, string, "findall")  # type: ignore[no-any-return]

    def _handle_timeout(self, pattern: str, string: str, operation: str) -> Any:
        """Handle timeout according to configured behavior."""
        behavior = self.config.timeout_behavior

        if behavior == TimeoutBehavior.RAISE_EXCEPTION:
            raise  # Re-raise the RegexTimeoutError

        elif behavior == TimeoutBehavior.RETURN_NONE:
            return None if operation != "sub" else ""

        elif behavior == TimeoutBehavior.RETURN_ORIGINAL:
            if operation == "sub":
                return string
            return None

        elif behavior == TimeoutBehavior.LOG_AND_CONTINUE:
            self.logger.error(f"Regex {operation} timed out on pattern: {pattern[:50]}")
            return None if operation != "sub" else string

    def get_metrics(self) -> Optional[RegexMetrics]:
        """Get current metrics (if enabled)."""
        return self.backend.metrics

    def clear_cache(self) -> None:
        """Clear the pattern cache."""
        if self.cache:
            self.cache.clear()


# ============================================================================
# Singleton Accessor
# ============================================================================

_global_engine: Optional[RegexEngine] = None
_global_engine_lock = threading.RLock()


def get_engine(config: Optional[RegexConfig] = None) -> RegexEngine:
    """
    Get or create the global RegexEngine instance.

    Args:
        config: Optional configuration. Only used on first call.

    Returns:
        Global RegexEngine instance
    """
    global _global_engine

    if _global_engine is None:
        with _global_engine_lock:
            if _global_engine is None:
                _global_engine = RegexEngine(config)

    return _global_engine


def reset_engine() -> None:
    """Reset the global engine (mainly for testing)."""
    global _global_engine
    with _global_engine_lock:
        _global_engine = None
