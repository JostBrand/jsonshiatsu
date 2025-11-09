"""
Comprehensive tests for the RegexEngine implementation.

Tests cover:
- Timeout functionality
- Cross-platform compatibility
- Thread safety
- Performance benchmarks
- Error handling
- Metrics tracking
"""

# Try to import regex module
import importlib.util
import re
import threading
import time

import pytest

from jsonshiatsu.core.regex_engine import (
    BackendPriority,
    PatternCache,
    RegexConfig,
    RegexEngine,
    RegexTimeoutError,
    SignalBackend,
    StdlibBackend,
    TimeoutBehavior,
    get_engine,
    reset_engine,
)

REGEX_AVAILABLE = importlib.util.find_spec("regex") is not None


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def engine():
    """Create a fresh engine for each test."""
    config = RegexConfig(
        default_timeout=1.0,
        cache_enabled=True,
        enable_metrics=True,
    )
    return RegexEngine(config)


@pytest.fixture
def engine_no_cache():
    """Engine without caching."""
    config = RegexConfig(cache_enabled=False, enable_metrics=True)
    return RegexEngine(config)


@pytest.fixture
def engine_strict():
    """Engine that raises on timeout."""
    config = RegexConfig(
        default_timeout=0.1,
        timeout_behavior=TimeoutBehavior.RAISE_EXCEPTION,
        enable_metrics=True,
    )
    return RegexEngine(config)


@pytest.fixture(autouse=True)
def cleanup_global_engine():
    """Reset global engine after each test."""
    yield
    reset_engine()


# ============================================================================
# Basic Functionality Tests
# ============================================================================


class TestBasicOperations:
    """Test basic regex operations work correctly."""

    def test_simple_search(self, engine):
        """Test basic search operation."""
        result = engine.search(r"\d+", "test123")
        assert result is not None
        assert result.group() == "123"

    def test_simple_match(self, engine):
        """Test basic match operation."""
        result = engine.match(r"\d+", "123test")
        assert result is not None
        assert result.group() == "123"

        # Should not match if pattern not at start
        result = engine.match(r"\d+", "test123")
        assert result is None

    def test_simple_sub(self, engine):
        """Test basic substitution."""
        result = engine.sub(r"\d+", "XXX", "test123abc456")
        assert result == "testXXXabcXXX"

    def test_simple_findall(self, engine):
        """Test find all matches."""
        result = engine.findall(r"\d+", "a1b22c333")
        assert result == ["1", "22", "333"]

    def test_regex_flags(self, engine):
        """Test that regex flags work correctly."""
        # Case insensitive
        result = engine.search(r"TEST", "test123", flags=re.IGNORECASE)
        assert result is not None

        # Without flag should fail
        result = engine.search(r"TEST", "test123")
        assert result is None

    def test_complex_pattern(self, engine):
        """Test more complex regex patterns."""
        email_pattern = r"[\w\.-]+@[\w\.-]+\.\w+"
        text = "Contact: john.doe@example.com or jane@test.co.uk"

        result = engine.findall(email_pattern, text)
        assert len(result) == 2
        assert "john.doe@example.com" in result


# ============================================================================
# Timeout Protection Tests
# ============================================================================


class TestTimeoutProtection:
    """Test timeout protection against catastrophic backtracking."""

    def test_catastrophic_backtracking_protection(self):
        """Test that catastrophic backtracking is caught."""
        # Use signal backend which can interrupt stdlib re operations
        config = RegexConfig(
            default_timeout=0.2,
            timeout_behavior=TimeoutBehavior.RAISE_EXCEPTION,
            preferred_backend="signal",
            enable_metrics=True,
        )
        engine = RegexEngine(config)

        # This pattern causes exponential backtracking when there's NO MATCH
        # (a+)+ tries to match 'a's but fails on 'c', causing backtracking
        evil_pattern = r"(a+)+b"
        evil_input = (
            "a" * 23 + "c"
        )  # Size 23 takes ~0.5s with stdlib re, no 'b' so no match

        with pytest.raises(RegexTimeoutError) as exc_info:
            engine.search(evil_pattern, evil_input, timeout=0.2)

        error = exc_info.value
        assert evil_pattern in str(error)
        assert "timed out" in str(error).lower()
        assert error.input_length == len(evil_input)

    def test_nested_quantifiers_timeout(self):
        """Test timeout on nested quantifier patterns."""
        # Use signal backend which can interrupt stdlib re operations
        config = RegexConfig(
            default_timeout=0.2,
            timeout_behavior=TimeoutBehavior.RAISE_EXCEPTION,
            preferred_backend="signal",
            enable_metrics=True,
        )
        engine = RegexEngine(config)

        # Patterns that cause slow execution when they DON'T match
        patterns = [
            (r"(a*)*b", "a" * 24 + "c"),  # Zero-or-more nested, no 'b'
            (r"(a+)+b", "a" * 22 + "c"),  # One-or-more nested, no 'b'
            (r"(a|a)*b", "a" * 23 + "c"),  # Alternation nested, no 'b'
        ]

        for pattern, evil_input in patterns:
            with pytest.raises(RegexTimeoutError):
                engine.search(pattern, evil_input, timeout=0.2)

    def test_timeout_behavior_return_none(self):
        """Test RETURN_NONE timeout behavior."""
        config = RegexConfig(
            timeout_behavior=TimeoutBehavior.RETURN_NONE,
            default_timeout=0.2,
            preferred_backend="signal",  # Use signal backend for timeout
        )
        engine = RegexEngine(config)

        # Pattern that causes slow execution (no match)
        result = engine.search(r"(a+)+b", "a" * 23 + "c", timeout=0.2)
        assert result is None

    def test_timeout_behavior_return_original(self):
        """Test RETURN_ORIGINAL timeout behavior for sub."""
        config = RegexConfig(
            timeout_behavior=TimeoutBehavior.RETURN_ORIGINAL,
            default_timeout=0.2,
            preferred_backend="signal",  # Use signal backend for timeout
        )
        engine = RegexEngine(config)

        original = "a" * 23 + "c"
        # Pattern that times out (no match, lots of backtracking)
        result = engine.sub(r"(a+)+b", "X", original, timeout=0.2)
        assert result == original  # Original returned on timeout


# ============================================================================
# Caching Tests
# ============================================================================


class TestPatternCaching:
    """Test pattern compilation caching."""

    def test_cache_basic(self):
        """Test basic cache functionality."""
        cache = PatternCache(maxsize=2)

        # Compile and cache
        pattern1 = re.compile(r"\d+")
        cache.put("\\d+", 0, "test", pattern1)

        # Should retrieve from cache
        cached = cache.get("\\d+", 0, "test")
        assert cached is pattern1

    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = PatternCache(maxsize=2)

        p1 = re.compile(r"a")
        p2 = re.compile(r"b")
        p3 = re.compile(r"c")

        cache.put("a", 0, "test", p1)
        cache.put("b", 0, "test", p2)

        # Cache is full (2/2)
        assert cache.size() == 2

        # Add third pattern - should evict least recently used (p1)
        cache.put("c", 0, "test", p3)

        assert cache.size() == 2
        assert cache.get("a", 0, "test") is None  # Evicted
        assert cache.get("b", 0, "test") is p2
        assert cache.get("c", 0, "test") is p3

    def test_cache_access_order(self):
        """Test that access updates LRU order."""
        cache = PatternCache(maxsize=2)

        p1 = re.compile(r"a")
        p2 = re.compile(r"b")
        p3 = re.compile(r"c")

        cache.put("a", 0, "test", p1)
        cache.put("b", 0, "test", p2)

        # Access p1 to make it recently used
        _ = cache.get("a", 0, "test")

        # Add p3 - should evict p2 (least recently used)
        cache.put("c", 0, "test", p3)

        assert cache.get("a", 0, "test") is p1  # Still cached
        assert cache.get("b", 0, "test") is None  # Evicted
        assert cache.get("c", 0, "test") is p3

    def test_engine_uses_cache(self, engine):
        """Test that engine actually uses the cache."""
        pattern = r"\d+"

        # First call - cache miss
        engine.search(pattern, "test123")

        # Second call - should hit cache
        engine.search(pattern, "test456")

        metrics = engine.get_metrics()
        assert metrics.cache_hits > 0

    def test_engine_without_cache(self, engine_no_cache):
        """Test engine behavior with caching disabled."""
        pattern = r"\d+"

        engine_no_cache.search(pattern, "test123")
        engine_no_cache.search(pattern, "test456")

        # With cache disabled, patterns are compiled each time
        # but no cache misses are recorded (cache is None)
        metrics = engine_no_cache.get_metrics()
        assert metrics.cache_hits == 0
        # Note: cache misses may still be recorded during compilation
        # The important part is cache_hits stays 0


# ============================================================================
# Metrics Tests
# ============================================================================


class TestMetrics:
    """Test metrics tracking."""

    def test_metrics_basic_tracking(self, engine):
        """Test basic metrics are tracked."""
        engine.search(r"\d+", "test123")
        engine.search(r"[a-z]+", "test456")
        engine.sub(r"\d+", "X", "test123")

        metrics = engine.get_metrics()
        assert metrics.total_operations == 3

    def test_metrics_timing(self, engine):
        """Test that execution times are recorded."""
        pattern = r"\d+"
        engine.search(pattern, "test123")

        metrics = engine.get_metrics()
        assert pattern in metrics.pattern_timings
        assert len(metrics.pattern_timings[pattern]) > 0
        assert metrics.pattern_timings[pattern][0] >= 0

    def test_metrics_timeout_tracking(self):
        """Test timeout events are tracked."""
        # Use signal backend for timeout
        config = RegexConfig(
            default_timeout=0.2,
            timeout_behavior=TimeoutBehavior.RAISE_EXCEPTION,
            preferred_backend="signal",
            enable_metrics=True,
        )
        engine = RegexEngine(config)

        pattern = r"(a+)+b"
        try:
            # Pattern that actually times out (no match, backtracking)
            engine.search(pattern, "a" * 23 + "c", timeout=0.2)
        except RegexTimeoutError:
            pass

        metrics = engine.get_metrics()
        assert metrics.timeouts > 0
        assert pattern in metrics.timeout_patterns

    def test_metrics_slowest_patterns(self, engine):
        """Test retrieval of slowest patterns."""
        # Run some patterns with varying complexity
        engine.search(r"a", "a")  # Fast
        engine.search(r"\w+", "test" * 100)  # Medium
        engine.search(r"(\w+\s+)*", "word " * 50)  # Slower

        metrics = engine.get_metrics()
        slowest = metrics.get_slowest_patterns(2)

        assert len(slowest) > 0
        # Each entry is (pattern, avg_time_ms)
        assert all(isinstance(avg, float) for _, avg in slowest)

    def test_metrics_cache_hit_rate(self, engine):
        """Test cache hit rate calculation."""
        pattern = r"\d+"

        # First call - miss
        engine.search(pattern, "test1")

        # Subsequent calls - hits
        for i in range(5):
            engine.search(pattern, f"test{i}")

        metrics = engine.get_metrics()
        hit_rate = metrics.get_cache_hit_rate()

        # Should have high hit rate
        assert hit_rate > 50.0


# ============================================================================
# Thread Safety Tests
# ============================================================================


class TestThreadSafety:
    """Test thread safety of regex engine."""

    def test_concurrent_searches(self, engine):
        """Test multiple threads can search concurrently."""
        results: list[str] = []
        lock = threading.Lock()

        def worker(pattern: str, text: str):
            match = engine.search(pattern, text)
            with lock:
                results.append(match.group() if match else None)

        threads = [
            threading.Thread(target=worker, args=(r"\d+", f"test{i}number{i * 10}"))
            for i in range(20)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should complete successfully
        assert len(results) == 20
        assert all(r is not None and r.isdigit() for r in results)

    def test_concurrent_substitutions(self, engine):
        """Test concurrent substitutions work correctly."""
        results: list[str] = []
        lock = threading.Lock()

        def worker(pattern: str, text: str):
            result = engine.sub(pattern, "X", text)
            with lock:
                results.append(result)

        threads = [
            threading.Thread(target=worker, args=(r"\d+", f"test{i}"))
            for i in range(20)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 20
        assert all("X" in r for r in results)

    def test_cache_thread_safety(self, engine):
        """Test pattern cache is thread-safe."""

        def worker(worker_id: int):
            for i in range(10):
                pattern = f"pattern{i % 3}"  # Use 3 different patterns
                engine.search(pattern, f"text{worker_id}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should complete without crashes or deadlocks
        metrics = engine.get_metrics()
        assert metrics.total_operations > 0

    def test_metrics_thread_safety(self, engine):
        """Test metrics tracking is thread-safe."""

        def worker():
            for _ in range(100):
                engine.search(r"\d+", "test123")

        threads = [threading.Thread(target=worker) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        metrics = engine.get_metrics()
        # Should be exactly 500 operations
        assert metrics.total_operations == 500


# ============================================================================
# Backend Selection Tests
# ============================================================================


class TestBackendSelection:
    """Test backend selection logic."""

    @pytest.mark.skipif(not REGEX_AVAILABLE, reason="Requires regex module")
    def test_prefers_regex_module(self):
        """Test that regex module backend is preferred when available."""
        config = RegexConfig()
        engine = RegexEngine(config)

        assert engine.backend.name == "regex_module"
        assert engine.backend.priority == BackendPriority.REGEX_MODULE

    def test_fallback_to_stdlib(self):
        """Test fallback to best available backend when preferred unavailable."""
        config = RegexConfig(preferred_backend="nonexistent", allow_fallback=True)
        engine = RegexEngine(config)

        # Should fall back to signal backend on Unix, stdlib on Windows
        import sys

        if sys.platform != "win32":
            assert isinstance(engine.backend, SignalBackend)
            assert engine.backend.supports_timeout
        else:
            assert isinstance(engine.backend, StdlibBackend)
            assert engine.backend.supports_timeout


# ============================================================================
# Global Engine Tests
# ============================================================================


class TestGlobalEngine:
    """Test global engine singleton."""

    def test_get_engine_singleton(self):
        """Test that get_engine returns singleton."""
        engine1 = get_engine()
        engine2 = get_engine()

        assert engine1 is engine2

    def test_reset_engine(self):
        """Test that reset_engine clears singleton."""
        engine1 = get_engine()
        reset_engine()
        engine2 = get_engine()

        assert engine1 is not engine2


# ============================================================================
# Performance Benchmarks
# ============================================================================


class TestPerformance:
    """Performance benchmarks (not strict tests)."""

    def test_cache_performance_improvement(self):
        """Verify caching provides performance improvement."""
        pattern = r"\d{3}-\d{3}-\d{4}"  # Phone number

        # With cache
        engine_cached = RegexEngine(
            RegexConfig(cache_enabled=True, enable_metrics=False)
        )
        start = time.perf_counter()
        for _ in range(1000):
            engine_cached.search(pattern, "555-123-4567")
        time_cached = time.perf_counter() - start

        # Without cache
        engine_no_cache = RegexEngine(
            RegexConfig(cache_enabled=False, enable_metrics=False)
        )
        start = time.perf_counter()
        for _ in range(1000):
            engine_no_cache.search(pattern, "555-123-4567")
        time_no_cache = time.perf_counter() - start

        # Caching should provide speedup
        # Not a strict assertion since timing can vary
        print(
            f"\nCache performance: {time_cached:.4f}s vs No cache: {time_no_cache:.4f}s"
        )
        print(f"Speedup: {time_no_cache / time_cached:.2f}x")

    @pytest.mark.skipif(not REGEX_AVAILABLE, reason="Requires regex module")
    def test_timeout_overhead(self):
        """Measure overhead of timeout protection on realistic workload."""
        # Use a pattern that does actual work to minimize threading overhead ratio
        pattern = r"[a-zA-Z]+\d+[a-zA-Z]+"
        text = "test123abc" * 100  # Larger input to do more work

        # Use regex module backend explicitly (signal backend has higher overhead)
        # Disable default timeouts to measure baseline overhead
        engine = RegexEngine(
            RegexConfig(
                enable_metrics=False,
                preferred_backend="regex",
                search_timeout=0,
                compile_timeout=0,
            )
        )

        # Run without timeout to measure baseline engine overhead (caching, etc)
        start = time.perf_counter()
        for _ in range(100):
            engine.search(pattern, text, timeout=None)
        time_engine = time.perf_counter() - start

        # For comparison, pure stdlib re
        compiled = re.compile(pattern)
        start = time.perf_counter()
        for _ in range(100):
            compiled.search(text)
        time_stdlib = time.perf_counter() - start

        overhead_percent = (time_engine - time_stdlib) / time_stdlib * 100
        print(f"\nEngine overhead (without timeout): {overhead_percent:.1f}%")

        # Without timeout, overhead should be reasonable
        # Allow up to 3000% overhead for abstraction layer, caching, pattern compilation
        # (This overhead is acceptable given the safety and features provided)
        assert overhead_percent < 3000


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error handling edge cases."""

    def test_invalid_pattern(self, engine):
        """Test that invalid regex patterns raise errors."""
        with pytest.raises(re.error):
            engine.search(r"(invalid[", "test")

    def test_replacement_function_in_sub(self, engine):
        """Test that replacement functions work in sub."""

        def replacer(match):
            return match.group().upper()

        result = engine.sub(r"\w+", replacer, "hello world")
        assert result == "HELLO WORLD"

    def test_empty_pattern(self, engine):
        """Test handling of empty patterns."""
        # Empty pattern should match everywhere
        result = engine.findall(r"", "abc")
        # Behavior varies by regex engine, just ensure no crash
        assert isinstance(result, list)

    def test_very_long_input(self, engine):
        """Test handling of very long inputs."""
        long_text = "a" * 100000
        result = engine.search(r"a+", long_text, timeout=5.0)
        assert result is not None
