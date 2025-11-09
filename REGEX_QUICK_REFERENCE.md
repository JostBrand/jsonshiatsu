# Regex Engine - Quick Reference Card

## 🚀 Quick Start (30 seconds)

```python
# 1. Import
from jsonshiatsu.core.regex_engine import get_engine

# 2. Get engine (singleton)
engine = get_engine()

# 3. Use it!
result = engine.sub(r"\d+", "X", "test123", timeout=1.0)
# → "testX"
```

---

## 📝 Common Operations

### Search
```python
match = engine.search(r"\d+", "test123")
if match:
    print(match.group())  # "123"
```

### Match (start of string)
```python
match = engine.match(r"\d+", "123test")
# Matches: "123"

match = engine.match(r"\d+", "test123")
# None (doesn't match at start)
```

### Substitute
```python
result = engine.sub(r"\d+", "X", "test123abc456")
# → "testXabcX"

# With count limit
result = engine.sub(r"\d+", "X", "test123abc456", count=1)
# → "testXabc456"
```

### Find All
```python
matches = engine.findall(r"\d+", "a1b22c333")
# → ["1", "22", "333"]
```

### With Flags
```python
import re

# Case insensitive
match = engine.search(r"TEST", "test123", flags=re.IGNORECASE)

# DOTALL (. matches newlines)
result = engine.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
```

---

## ⏱️ Timeouts

### Default Timeouts
```python
# Uses configured defaults:
engine.search(pattern, text)  # 0.5s default
engine.sub(pattern, repl, text)  # 2.0s default
engine.findall(pattern, text)  # 3.0s default
```

### Custom Timeouts
```python
# Short timeout for simple patterns
match = engine.search(r"\d+", text, timeout=0.1)

# Long timeout for complex operations
result = engine.sub(
    r"complex(pattern)+",
    replacer,
    large_text,
    timeout=10.0
)
```

### Timeout Recommendations
| Pattern Complexity | Input Size | Timeout |
|-------------------|------------|---------|
| Simple (r"\d+") | <1KB | 0.1s |
| Simple | 1KB-100KB | 0.5s |
| Medium (r"\w+\s+") | <1KB | 0.5s |
| Medium | 1KB-100KB | 1.0s |
| Complex (r"(a\|b)+") | <1KB | 1.0s |
| Complex | 1KB-100KB | 2.0-5.0s |

---

## 🔧 Configuration

### Basic Config
```python
from jsonshiatsu.core.regex_engine import (
    RegexEngine,
    RegexConfig,
    TimeoutBehavior
)

config = RegexConfig(
    default_timeout=1.0,        # Default timeout
    cache_size=128,             # Pattern cache size
    enable_metrics=True,        # Track metrics
)

engine = RegexEngine(config)
```

### Timeout Behaviors
```python
# Option 1: Raise exception (recommended)
config = RegexConfig(
    timeout_behavior=TimeoutBehavior.RAISE_EXCEPTION
)
# Raises RegexTimeoutError on timeout

# Option 2: Return None/empty
config = RegexConfig(
    timeout_behavior=TimeoutBehavior.RETURN_NONE
)
# Returns None for search/match, "" for sub

# Option 3: Return original
config = RegexConfig(
    timeout_behavior=TimeoutBehavior.RETURN_ORIGINAL
)
# Returns input unchanged on timeout

# Option 4: Log and continue
config = RegexConfig(
    timeout_behavior=TimeoutBehavior.LOG_AND_CONTINUE,
    logger=logging.getLogger(__name__)
)
# Logs error and returns None/original
```

---

## 📊 Metrics

### Get Metrics
```python
engine = get_engine()

# Do some operations...
engine.search(r"\d+", "test123")
engine.sub(r"\w+", "X", "hello world")

# Get metrics
metrics = engine.get_metrics()

print(f"Total ops: {metrics.total_operations}")
print(f"Timeouts: {metrics.timeouts}")
print(f"Timeout rate: {metrics.get_timeout_rate():.2f}%")
print(f"Cache hit rate: {metrics.get_cache_hit_rate():.1f}%")
```

### Find Slow Patterns
```python
for pattern, avg_ms in metrics.get_slowest_patterns(5):
    print(f"{pattern}: {avg_ms:.2f}ms")
```

### Monitor Timeouts
```python
# Check if specific pattern is timing out
if "my_pattern" in metrics.timeout_patterns:
    count = metrics.timeout_patterns["my_pattern"]
    print(f"Pattern timed out {count} times")
```

---

## 🛡️ Error Handling

### Handle Timeouts
```python
from jsonshiatsu.core.regex_engine import RegexTimeoutError

try:
    result = engine.sub(pattern, repl, text, timeout=1.0)
except RegexTimeoutError as e:
    print(f"Timeout after {e.timeout}s")
    print(f"Pattern: {e.pattern}")
    print(f"Input length: {e.input_length}")
    # Fallback to original
    result = text
```

### Handle Invalid Patterns
```python
import re

try:
    result = engine.search(r"(invalid[", text)
except re.error as e:
    print(f"Invalid regex: {e}")
```

---

## 🧪 Testing

### Test Setup
```python
import pytest
from jsonshiatsu.core.regex_engine import get_engine, reset_engine

@pytest.fixture(autouse=True)
def reset_global_engine():
    """Reset engine before each test."""
    reset_engine()
    yield
    reset_engine()

def test_my_function():
    engine = get_engine()
    # Your test here...
```

### Test Timeout Protection
```python
def test_timeout():
    engine = get_engine()

    # This should timeout
    with pytest.raises(RegexTimeoutError):
        engine.search(r"(a+)+", "a" * 1000 + "b", timeout=0.1)
```

---

## 🔄 Migration Patterns

### Pattern 1: Direct `re` → `engine`
```python
# Before
import re
result = re.sub(r"\d+", "X", text)

# After
from jsonshiatsu.core.regex_engine import get_engine
engine = get_engine()
result = engine.sub(r"\d+", "X", text, timeout=1.0)
```

### Pattern 2: In Class Methods
```python
# Before
class MyClass:
    def process(self, text):
        return re.sub(r"\d+", "X", text)

# After
from jsonshiatsu.core.regex_engine import get_engine

class MyClass:
    def __init__(self):
        self.engine = get_engine()

    def process(self, text):
        return self.engine.sub(r"\d+", "X", text, timeout=1.0)
```

### Pattern 3: Static Methods
```python
# Before
class Utils:
    @staticmethod
    def clean(text):
        return re.sub(r"\d+", "", text)

# After
class Utils:
    _engine = None

    @classmethod
    def _get_engine(cls):
        if cls._engine is None:
            cls._engine = get_engine()
        return cls._engine

    @staticmethod
    def clean(text):
        engine = Utils._get_engine()
        return engine.sub(r"\d+", "", text, timeout=1.0)
```

---

## ⚡ Performance Tips

### 1. Pattern Caching (Automatic)
```python
# Pattern compiled once, cached forever
for item in items:
    engine.search(r"\d+", item)  # Uses cached pattern
```

### 2. Disable Metrics in Hot Paths
```python
config = RegexConfig(enable_metrics=False)
fast_engine = RegexEngine(config)

# Max performance, no overhead
for _ in range(1_000_000):
    fast_engine.search(r"\d+", text)
```

### 3. Increase Cache Size
```python
config = RegexConfig(cache_size=512)  # Default: 128
engine = RegexEngine(config)
```

### 4. Appropriate Timeouts
```python
# Short timeout for simple operations
engine.search(r"\d", short_text, timeout=0.1)

# Longer timeout for complex operations
engine.sub(r"complex+", repl, long_text, timeout=5.0)
```

---

## 🚨 Anti-Patterns (Don't Do This!)

### ❌ Creating New Engine Every Call
```python
# BAD - Creates new engine each time
def process(text):
    engine = RegexEngine()  # DON'T DO THIS
    return engine.sub(r"\d+", "X", text)

# GOOD - Reuse singleton
engine = get_engine()

def process(text):
    return engine.sub(r"\d+", "X", text)
```

### ❌ Overly Long Timeouts
```python
# BAD - Wastes time
result = engine.search(r"\d", text, timeout=60.0)

# GOOD - Reasonable timeout
result = engine.search(r"\d", text, timeout=0.5)
```

### ❌ No Timeout on Complex Patterns
```python
# BAD - Vulnerable to ReDoS
result = engine.sub(r"(a+)+", "X", text)  # Uses default

# GOOD - Explicit short timeout
result = engine.sub(r"(a+)+", "X", text, timeout=0.1)
```

---

## 📖 API Reference

### RegexEngine Methods

| Method | Signature | Returns | Timeout Default |
|--------|-----------|---------|----------------|
| `search()` | `search(pattern, string, flags=0, timeout=None)` | `Match \| None` | 0.5s |
| `match()` | `match(pattern, string, flags=0, timeout=None)` | `Match \| None` | 0.5s |
| `sub()` | `sub(pattern, repl, string, count=0, flags=0, timeout=None)` | `str` | 2.0s |
| `findall()` | `findall(pattern, string, flags=0, timeout=None)` | `list[str]` | 3.0s |

### RegexConfig Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `default_timeout` | `float` | 1.0 | Default timeout in seconds |
| `timeout_behavior` | `TimeoutBehavior` | RAISE_EXCEPTION | What to do on timeout |
| `cache_size` | `int` | 128 | Pattern cache size (0=disabled) |
| `enable_metrics` | `bool` | True | Track metrics |
| `log_slow_patterns` | `bool` | False | Log patterns >threshold |
| `slow_threshold_ms` | `float` | 100.0 | Threshold for slow logs |

---

## 🔗 Links

- **Design Doc**: `REGEX_TIMEOUT_DESIGN.md` - Architecture deep dive
- **Migration Guide**: `REGEX_MIGRATION_GUIDE.md` - Step-by-step migration
- **Example**: `EXAMPLE_MIGRATION.md` - Real-world before/after
- **Summary**: `REGEX_TIMEOUT_SUMMARY.md` - Executive overview
- **Tests**: `tests/unit/core/test_regex_engine.py` - 34 comprehensive tests

---

## 💡 Remember

✅ **Always set timeouts** - especially for complex patterns
✅ **Use the singleton** - `get_engine()` not `RegexEngine()`
✅ **Monitor metrics** - track timeouts and slow patterns
✅ **Test edge cases** - especially timeout behavior
✅ **Install `regex` module** - for best protection: `pip install regex`

---

## 🆘 Troubleshooting

### "regex module not available"
```bash
pip install regex
```

### Timeouts too aggressive
```python
# Increase timeout
engine.sub(pattern, repl, text, timeout=10.0)

# Or globally
config = RegexConfig(default_timeout=5.0)
```

### Low cache hit rate
```python
# Increase cache size
config = RegexConfig(cache_size=512)

# Check current rate
metrics = engine.get_metrics()
print(f"Hit rate: {metrics.get_cache_hit_rate():.1f}%")
```

### Performance regression
```python
# Disable metrics for max speed
config = RegexConfig(enable_metrics=False)

# Or just in hot path
fast_engine = RegexEngine(config)
```

---

**Quick help**: `python -c "from jsonshiatsu.core.regex_engine import get_engine; help(get_engine())"`
