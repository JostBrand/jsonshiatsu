# jsonshiatsu Performance Analysis & Optimization

## Current Performance Issues

Based on benchmarking analysis, jsonshiatsu shows **significant performance overhead** compared to standard JSON:

- **Small objects**: 3,914% overhead
- **Medium arrays**: 12,213% overhead  
- **Large objects**: 12,975% overhead
- **Mixed content**: 8,147% overhead

## Root Cause Analysis

### 1. 🔴 **Critical: String Concatenation in Lexer (HIGH IMPACT)**

**Problem**: Heavy use of `result += char` in tight loops
```python
# lexer.py - INEFFICIENT
result = ""
while condition:
    result += self.advance()  # O(n) string copy each iteration
```

**Impact**: O(n²) complexity for string/number parsing
**Solution**: Use `list` and `''.join()` or `io.StringIO`

### 2. 🔴 **Critical: Repeated `len(self.text)` Calls (HIGH IMPACT)**

**Problem**: `len()` called in every loop iteration
```python
# lexer.py - INEFFICIENT  
while self.pos < len(self.text):  # len() called every iteration
```

**Impact**: Unnecessary function calls in tight loops
**Solution**: Cache `text_length = len(self.text)`

### 3. 🟡 **Major: Inefficient Character Access Patterns**

**Problem**: Multiple `self.peek()` calls and bounds checking
```python
# lexer.py - INEFFICIENT
char = self.peek()
if char == something and self.peek(1).isdigit():
```

**Impact**: Redundant bounds checking and character access
**Solution**: Batch character reads, optimize peek operations

### 4. 🟡 **Major: Excessive Object Creation**

**Problem**: Creating `Position` objects for every token
```python
# lexer.py - MEMORY INTENSIVE
pos = self.current_position()  # Creates new Position object
yield Token(TokenType.STRING, string_value, pos)
```

**Impact**: Memory allocation overhead
**Solution**: Lazy position calculation, object pooling

### 5. 🟡 **Major: Streaming Buffer Management**

**Problem**: Inefficient string slicing in streaming
```python
# streaming.py - INEFFICIENT
self.buffer = self.buffer[1:]  # O(n) string copy
```

**Impact**: O(n²) complexity for buffer operations
**Solution**: Use `collections.deque` or index tracking

### 6. 🟠 **Minor: Preprocessor Regex Overhead**

**Problem**: Multiple regex compilations and executions
```python
# preprocessor.py - INEFFICIENT
re.search(pattern, text, flags)  # Pattern compiled each time
```

**Impact**: Regex compilation overhead
**Solution**: Pre-compile patterns, optimize regex usage

## Optimization Strategy

### Phase 1: Critical Performance Fixes (Expected 80% improvement)

1. **String Building Optimization**
2. **Loop Optimization** 
3. **Character Access Optimization**

### Phase 2: Major Optimizations (Expected 50% additional improvement)

4. **Object Creation Reduction**
5. **Streaming Buffer Optimization**
6. **Memory Pool Implementation**

### Phase 3: Fine-tuning (Expected 20% additional improvement)

7. **Regex Optimization**
8. **Validation Optimization**
9. **Error Path Optimization**

## Detailed Optimization Plans

### 1. String Building Optimization

**Current Code:**
```python
result = ""
while condition:
    result += self.advance()  # O(n²)
```

**Optimized Code:**
```python
chars = []
while condition:
    chars.append(self.advance())  # O(1)
result = ''.join(chars)  # O(n)
```

### 2. Loop Optimization

**Current Code:**
```python
while self.pos < len(self.text):
    # loop body
```

**Optimized Code:**
```python
text_length = len(self.text)
while self.pos < text_length:
    # loop body
```

### 3. Character Access Optimization

**Current Code:**
```python
def peek(self, offset: int = 0) -> str:
    pos = self.pos + offset
    if pos >= len(self.text):
        return ""
    return self.text[pos]
```

**Optimized Code:**
```python
def peek(self, offset: int = 0) -> str:
    pos = self.pos + offset
    if pos >= self.text_length:
        return ""
    return self.text[pos]

# Batch operations
def peek_ahead(self, count: int) -> str:
    end_pos = min(self.pos + count, self.text_length)
    return self.text[self.pos:end_pos]
```

### 4. Object Creation Reduction

**Current Code:**
```python
def current_position(self) -> Position:
    return Position(self.line, self.column)
```

**Optimized Code:**
```python
# Lazy position calculation
def current_position(self) -> Position:
    if not hasattr(self, '_cached_position'):
        self._cached_position = Position(self.line, self.column)
    return self._cached_position

def invalidate_position_cache(self):
    if hasattr(self, '_cached_position'):
        delattr(self, '_cached_position')
```

### 5. Streaming Buffer Optimization

**Current Code:**
```python
char = self.buffer[0]
self.buffer = self.buffer[1:]  # O(n) copy
```

**Optimized Code:**
```python
from collections import deque

class StreamingLexer:
    def __init__(self, stream: TextIO, buffer_size: int = 8192):
        self.buffer = deque()
        self.buffer_offset = 0
        
    def advance(self) -> str:
        if not self.buffer:
            self._fill_buffer()
        return self.buffer.popleft()  # O(1)
```

## Implementation Priority

### High Priority (Immediate 60-80% improvement)
- [ ] String concatenation optimization in lexer
- [ ] Loop optimization with cached lengths
- [ ] Streaming buffer optimization

### Medium Priority (Additional 30-50% improvement)  
- [ ] Character access pattern optimization
- [ ] Object creation reduction
- [ ] Preprocessor regex compilation

### Low Priority (Additional 10-20% improvement)
- [ ] Memory pooling for frequently created objects
- [ ] Validation overhead reduction
- [ ] Error reporting optimization

## Expected Results

After implementing all optimizations:

| Test Case | Current Overhead | Expected Overhead | Improvement |
|-----------|------------------|-------------------|-------------|
| Small objects | 3,914% | ~200% | 95% reduction |
| Medium arrays | 12,213% | ~300% | 97.5% reduction |
| Large objects | 12,975% | ~250% | 98% reduction |
| Mixed content | 8,147% | ~150% | 98% reduction |

## Performance Monitoring

Post-optimization, implement:

1. **Regression Testing**: Automated performance benchmarks
2. **Memory Profiling**: Track memory usage patterns
3. **Hotspot Analysis**: Identify remaining bottlenecks
4. **Comparative Benchmarks**: Against other JSON parsers

## Implementation Notes

- Maintain backward compatibility
- Preserve all security features
- Add performance configuration options
- Include performance regression tests