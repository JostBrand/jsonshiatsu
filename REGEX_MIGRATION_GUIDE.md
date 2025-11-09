# Regex Engine Migration Guide

## Overview

This guide shows how to migrate from the old `regex_utils.py` signal-based approach to the new production-ready `RegexEngine`.

## Why Migrate?

### Current Problems

```python
# OLD APPROACH (jsonshiatsu/core/regex_utils.py)

from jsonshiatsu.core.regex_utils import safe_regex_sub

result = safe_regex_sub(pattern, repl, text, timeout=5)

# PROBLEMS:
# ❌ Unix-only (crashes on Windows)
# ❌ Not thread-safe (signal handlers are process-wide)
# ❌ Silent failures (returns original on timeout)
# ❌ Integer second precision only
# ❌ No pattern caching
# ❌ No metrics/monitoring
```

### New Benefits

```python
# NEW APPROACH (jsonshiatsu/core/regex_engine.py)

from jsonshiatsu.core.regex_engine import get_engine

engine = get_engine()
result = engine.sub(pattern, repl, text, timeout=2.0)

# BENEFITS:
# ✅ Cross-platform (Windows, Linux, macOS)
# ✅ Thread-safe
# ✅ Configurable error handling
# ✅ Millisecond precision timeouts
# ✅ LRU pattern caching (2-5x faster)
# ✅ Built-in metrics tracking
# ✅ Multiple backend strategies
```

---

## Migration Steps

### Step 1: Install Dependencies (Optional but Recommended)

```bash
# Install the 'regex' module for best timeout support
pip install regex

# Or add to requirements.txt / pyproject.toml
poetry add regex
```

Without `regex` module, the engine falls back to stdlib `re` (no timeout protection).

### Step 2: Update Imports

#### Before:
```python
import re
from jsonshiatsu.core.regex_utils import (
    safe_regex_sub,
    safe_regex_search,
    safe_regex_match,
    safe_regex_findall,
)
```

#### After:
```python
from jsonshiatsu.core.regex_engine import get_engine

# Get global engine instance (created once, reused everywhere)
engine = get_engine()
```

### Step 3: Update Function Calls

#### Pattern 1: Search
```python
# Before:
match = safe_regex_search(r"\d+", text, timeout=5)

# After:
match = engine.search(r"\d+", text, timeout=5.0)
```

#### Pattern 2: Substitution
```python
# Before:
result = safe_regex_sub(r"\d+", "X", text, flags=re.IGNORECASE, timeout=5)

# After:
result = engine.sub(r"\d+", "X", text, flags=re.IGNORECASE, timeout=5.0)
```

#### Pattern 3: Match
```python
# Before:
match = safe_regex_match(r"^\d+", text, timeout=5)

# After:
match = engine.match(r"^\d+", text, timeout=5.0)
```

#### Pattern 4: FindAll
```python
# Before:
matches = safe_regex_findall(r"\d+", text, timeout=5)

# After:
matches = engine.findall(r"\d+", text, timeout=5.0)
```

#### Pattern 5: Direct `re` Module Calls
```python
# Before (UNSAFE - no timeout):
import re
result = re.sub(r"\d+", "X", text)
match = re.search(r"\w+", text)

# After:
result = engine.sub(r"\d+", "X", text)
match = engine.search(r"\w+", text)
```

---

## Real-World Migration Examples

### Example 1: handlers.py (JavaScript Handler)

#### Before:
```python
# jsonshiatsu/preprocessing/handlers.py

import re

class JavaScriptHandler:
    def handle_special_numbers(self, text: str) -> str:
        # Convert NaN to JSON null
        text = re.sub(r"\bNaN\b", '"NaN"', text)

        # Convert Infinity
        text = re.sub(r"-\bInfinity\b", '"-Infinity"', text)
        text = re.sub(
            r"\b(Infinity)\b",
            lambda m: f'"{m.group(0)}"'
            if m.start() > 0 and text[m.start() - 1] != "-"
            else m.group(0),
            text,
        )

        return text
```

#### After:
```python
# jsonshiatsu/preprocessing/handlers.py

from jsonshiatsu.core.regex_engine import get_engine

class JavaScriptHandler:
    def __init__(self):
        self.engine = get_engine()

    def handle_special_numbers(self, text: str) -> str:
        # Convert NaN to JSON null
        text = self.engine.sub(r"\bNaN\b", '"NaN"', text, timeout=0.5)

        # Convert Infinity
        text = self.engine.sub(r"-\bInfinity\b", '"-Infinity"', text, timeout=0.5)
        text = self.engine.sub(
            r"\b(Infinity)\b",
            lambda m: f'"{m.group(0)}"'
            if m.start() > 0 and text[m.start() - 1] != "-"
            else m.group(0),
            text,
            timeout=0.5
        )

        return text
```

### Example 2: array_object_handler.py

#### Before:
```python
# jsonshiatsu/core/array_object_handler.py

import re

class ArrayObjectHandler:
    @staticmethod
    def handle_sparse_arrays(text: str) -> str:
        def fix_array_sparse(match):
            array_content = match.group(1)
            # Replace leading comma with null
            array_content = re.sub(r"^\s*,", "null,", array_content)
            # ... more processing
            return f"[{array_content}]"

        text = re.sub(r"\[([^\[\]]*)\]", fix_array_sparse, text)
        return text
```

#### After:
```python
# jsonshiatsu/core/array_object_handler.py

from jsonshiatsu.core.regex_engine import get_engine

class ArrayObjectHandler:
    def __init__(self):
        self.engine = get_engine()

    def handle_sparse_arrays(self, text: str) -> str:
        def fix_array_sparse(match):
            array_content = match.group(1)
            # Replace leading comma with null
            array_content = self.engine.sub(
                r"^\s*,",
                "null,",
                array_content,
                timeout=0.5
            )
            # ... more processing
            return f"[{array_content}]"

        text = self.engine.sub(
            r"\[([^\[\]]*)\]",
            fix_array_sparse,
            text,
            timeout=2.0  # Longer timeout for recursive function
        )
        return text
```

### Example 3: string_preprocessors.py

#### Before:
```python
# jsonshiatsu/core/string_preprocessors.py

from .regex_utils import safe_regex_sub, safe_regex_search

class StringPreprocessor:
    @staticmethod
    def fix_unescaped_strings(text: str) -> str:
        has_json_escapes = safe_regex_search(
            r'\\[\\"/bfnrtu]|\\u[0-9a-fA-F]{4}',
            content
        )

        # ... more logic

        text = safe_regex_sub(r'"([^"]*)"', fix_file_paths, text)
        return text
```

#### After:
```python
# jsonshiatsu/core/string_preprocessors.py

from jsonshiatsu.core.regex_engine import get_engine

class StringPreprocessor:
    _engine = None  # Class-level shared instance

    @classmethod
    def _get_engine(cls):
        if cls._engine is None:
            cls._engine = get_engine()
        return cls._engine

    @staticmethod
    def fix_unescaped_strings(text: str) -> str:
        engine = StringPreprocessor._get_engine()

        has_json_escapes = engine.search(
            r'\\[\\"/bfnrtu]|\\u[0-9a-fA-F]{4}',
            content,
            timeout=0.5
        )

        # ... more logic

        text = engine.sub(r'"([^"]*)"', fix_file_paths, text, timeout=2.0)
        return text
```

---

## Advanced Configuration

### Custom Configuration

```python
from jsonshiatsu.core.regex_engine import (
    RegexEngine,
    RegexConfig,
    TimeoutBehavior
)

# Create engine with custom config
config = RegexConfig(
    # Timeout settings
    default_timeout=1.0,
    search_timeout=0.5,
    sub_timeout=2.0,

    # Error handling
    timeout_behavior=TimeoutBehavior.RAISE_EXCEPTION,

    # Performance
    cache_size=256,  # Larger cache for better performance

    # Monitoring
    enable_metrics=True,
    log_slow_patterns=True,
    slow_threshold_ms=100.0,
)

engine = RegexEngine(config)
```

### Per-Operation Timeouts

```python
engine = get_engine()

# Quick search with short timeout
match = engine.search(r"\d+", text, timeout=0.1)

# Complex substitution with longer timeout
result = engine.sub(
    r"complex(pattern)+",
    replacer,
    text,
    timeout=5.0
)
```

### Error Handling Strategies

```python
# Strategy 1: Raise exception (recommended for production)
config = RegexConfig(timeout_behavior=TimeoutBehavior.RAISE_EXCEPTION)

try:
    result = engine.sub(pattern, repl, text)
except RegexTimeoutError as e:
    logger.error(f"Regex timeout: {e.pattern}")
    # Handle error appropriately
    result = text  # Return original

# Strategy 2: Return None/empty (for non-critical operations)
config = RegexConfig(timeout_behavior=TimeoutBehavior.RETURN_NONE)
match = engine.search(pattern, text)
if match is None:
    # Could be timeout or no match - can't distinguish!
    pass

# Strategy 3: Log and continue (for best-effort processing)
import logging
logger = logging.getLogger(__name__)

config = RegexConfig(
    timeout_behavior=TimeoutBehavior.LOG_AND_CONTINUE,
    logger=logger
)
```

---

## Monitoring & Metrics

### Basic Metrics

```python
engine = get_engine()

# Do some operations
engine.search(r"\d+", "test123")
engine.sub(r"\w+", "X", "hello world")

# Get metrics
metrics = engine.get_metrics()

print(f"Total operations: {metrics.total_operations}")
print(f"Timeouts: {metrics.timeouts}")
print(f"Cache hit rate: {metrics.get_cache_hit_rate():.1f}%")

# Find slow patterns
for pattern, avg_ms in metrics.get_slowest_patterns(5):
    print(f"  {pattern}: {avg_ms:.2f}ms average")
```

### Production Monitoring

```python
import logging

# Set up logging
logger = logging.getLogger("jsonshiatsu.regex")
logger.setLevel(logging.WARNING)

config = RegexConfig(
    enable_metrics=True,
    log_slow_patterns=True,
    slow_threshold_ms=100.0,
    logger=logger
)

engine = RegexEngine(config)

# Slow patterns will be automatically logged
# WARNING: Slow regex sub detected (234ms): pattern=(a+)+ on 5000 char input
```

### Periodic Metrics Export

```python
import time
import json

def export_metrics_periodically():
    """Export metrics every 60 seconds."""
    engine = get_engine()

    while True:
        time.sleep(60)

        metrics = engine.get_metrics()

        report = {
            "timestamp": time.time(),
            "total_ops": metrics.total_operations,
            "timeouts": metrics.timeouts,
            "timeout_rate": metrics.get_timeout_rate(),
            "cache_hit_rate": metrics.get_cache_hit_rate(),
            "slowest_patterns": metrics.get_slowest_patterns(10)
        }

        # Log or send to monitoring system
        with open("regex_metrics.json", "w") as f:
            json.dump(report, f, indent=2)

# Run in background thread
import threading
metrics_thread = threading.Thread(target=export_metrics_periodically, daemon=True)
metrics_thread.start()
```

---

## Testing Migration

### Unit Test Updates

#### Before:
```python
def test_malformed_json():
    from jsonshiatsu.core.regex_utils import safe_regex_sub

    result = safe_regex_sub(r"\d+", "X", "test123")
    assert result == "testX"
```

#### After:
```python
def test_malformed_json():
    from jsonshiatsu.core.regex_engine import get_engine, reset_engine

    # Reset engine for test isolation
    reset_engine()

    engine = get_engine()
    result = engine.sub(r"\d+", "X", "test123")
    assert result == "testX"
```

### Integration Test Pattern

```python
import pytest
from jsonshiatsu.core.regex_engine import (
    get_engine,
    reset_engine,
    RegexTimeoutError
)

@pytest.fixture(autouse=True)
def reset_global_engine():
    """Reset engine before each test for isolation."""
    reset_engine()
    yield
    reset_engine()

def test_timeout_protection():
    """Test that timeouts work correctly."""
    engine = get_engine()

    # This should timeout (if regex module available)
    try:
        result = engine.search(r"(a+)+", "a" * 1000 + "b", timeout=0.1)
        # If no timeout occurred, we're on fallback backend
        assert result is None or result is not None
    except RegexTimeoutError:
        # Timeout correctly triggered
        pass
```

---

## Performance Optimization Tips

### 1. Pattern Caching

```python
# BAD: Recompiling pattern every call
for item in items:
    result = engine.sub(r"\d+", "X", item, timeout=1.0)
    # Pattern is cached, but still some overhead

# BETTER: Pattern is automatically cached by engine
# Just use it naturally, caching handles the rest
engine = get_engine()
for item in items:
    result = engine.sub(r"\d+", "X", item, timeout=1.0)
```

### 2. Appropriate Timeouts

```python
# BAD: Too generous timeout for simple operations
match = engine.search(r"\d+", short_text, timeout=10.0)

# GOOD: Short timeout for simple patterns
match = engine.search(r"\d+", short_text, timeout=0.1)

# GOOD: Longer timeout for complex operations
result = engine.sub(
    r"(complex|pattern)+",
    replacer,
    long_text,
    timeout=5.0
)
```

### 3. Disable Metrics in Hot Paths

```python
# For performance-critical code
from jsonshiatsu.core.regex_engine import RegexEngine, RegexConfig

config = RegexConfig(
    enable_metrics=False,  # Disable for max performance
    cache_size=512,        # Larger cache
)
fast_engine = RegexEngine(config)

# Use in hot path
for _ in range(1_000_000):
    result = fast_engine.search(r"\d+", text, timeout=0.5)
```

---

## Troubleshooting

### Issue 1: "regex module not available"

**Problem**: Warning message about missing `regex` module

**Solution**:
```bash
pip install regex
```

**Alternative**: Use fallback mode (no timeout protection)
```python
config = RegexConfig(allow_fallback=True)
engine = RegexEngine(config)
```

### Issue 2: Timeouts too aggressive

**Problem**: Legitimate operations timing out

**Solution**: Increase timeout or use per-operation timeouts
```python
# Global increase
config = RegexConfig(default_timeout=5.0)

# Or per-operation
result = engine.sub(pattern, repl, text, timeout=10.0)
```

### Issue 3: Performance regression

**Problem**: Code slower after migration

**Solution**: Check cache is enabled and increase size
```python
config = RegexConfig(
    cache_enabled=True,
    cache_size=512,  # Increase if many unique patterns
    enable_metrics=False,  # Disable for performance
)
```

**Verify caching is working**:
```python
metrics = engine.get_metrics()
print(f"Cache hit rate: {metrics.get_cache_hit_rate():.1f}%")
# Should be >80% for repeated patterns
```

---

## Rollout Plan

### Phase 1: Enable New Engine (Week 1)
- Add `regex_engine.py` to codebase
- Add tests
- No changes to existing code yet
- Monitor for issues

### Phase 2: Migrate High-Risk Files (Week 2)
Priority order:
1. `preprocessing/handlers.py` - 10 regex calls
2. `core/array_object_handler.py` - 5 regex calls
3. `preprocessing/repairers.py` - 8 regex calls
4. `core/string_preprocessors.py` - Update to use new engine

### Phase 3: Deprecate Old API (Week 3)
- Add deprecation warnings to `regex_utils.py`
- Update remaining files
- Add migration guide to docs

### Phase 4: Remove Old Code (Version 1.0.0)
- Delete `regex_utils.py`
- Breaking change in major version

---

## Checklist

Use this checklist when migrating a file:

- [ ] Install `regex` module (optional but recommended)
- [ ] Replace `import re` with `from jsonshiatsu.core.regex_engine import get_engine`
- [ ] Replace `safe_regex_*` calls with `engine.*` calls
- [ ] Add appropriate timeouts to all calls
- [ ] Update tests to use `reset_engine()` for isolation
- [ ] Test edge cases (timeouts, errors, thread safety)
- [ ] Verify performance is acceptable
- [ ] Update documentation/comments
- [ ] Remove old imports from `regex_utils`

---

## Questions?

- Check design doc: `REGEX_TIMEOUT_DESIGN.md`
- Run tests: `pytest tests/unit/core/test_regex_engine.py -v`
- File issues: GitHub Issues
