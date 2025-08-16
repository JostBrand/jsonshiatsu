# jsonshiatsu Test Coverage Analysis

## Current Test Coverage Summary

### ✅ **Well Covered Areas**

1. **Basic JSON Parsing** (`test_engine.py`)
   - Standard JSON compliance
   - Unquoted keys and values
   - Mixed quotes (single/double)
   - Trailing commas
   - Numbers, booleans, null
   - Nested structures
   - Empty structures
   - Whitespace tolerance

2. **Malformed JSON Patterns** (`test_malformed_json.py`)
   - Markdown code blocks
   - JavaScript comments
   - Function call wrappers
   - Trailing explanatory text
   - Multiple JSON objects
   - Non-standard boolean/null values
   - Incomplete JSON structures

3. **Tokenization** (`test_tokenizer.py`)
   - String tokenization (single/double quotes)
   - Number tokenization
   - Structural tokens ({, }, [, ], :, ,)
   - Identifiers and keywords
   - Whitespace and newline handling

4. **Security Features** (`test_limits.py`)
   - Input size limits
   - String length limits
   - Number length limits
   - Nesting depth limits
   - Object key count limits
   - Array item count limits
   - Total item count limits

5. **Streaming** (`test_processor.py`)
   - Basic streaming functionality
   - Large file processing
   - Streaming with preprocessing

6. **Error Recovery** (`test_strategies.py`)
   - Partial parsing
   - Field skipping
   - Error reporting

---

## ❌ **Missing Test Cases - Critical Gaps**

### 1. **Function Call Patterns** (Recently Fixed)
```python
# No tests for the recently fixed function call handling
def test_function_call_patterns(self):
    # Date functions
    assert loads('{"date": Date("2025-08-01")}') == {"date": "2025-08-01"}
    
    # RegExp functions  
    assert loads('{"regex": RegExp("test+")}') == {"regex": "test+"}
    
    # ObjectId functions
    assert loads('{"id": ObjectId("507f...")}') == {"id": "507f..."}
    
    # Unknown function calls should fail gracefully
    with pytest.raises(JSONDecodeError):
        loads('{"unknown": UnknownFunc("value")}')
        
    # Nested function calls
    assert loads('{"data": [Date("2025-01-01"), Date("2025-12-31")]}')
    
    # Empty function calls
    assert loads('{"empty": Date("")}') == {"empty": ""}
```

### 2. **Unicode and Character Encoding** (Partially Fixed)
```python
def test_unicode_edge_cases(self):
    # Unicode normalization conflicts (different representations of same character)
    json_nfc = '{"café": 1}'  # NFC normalization
    json_nfd = '{"café": 2}'  # NFD normalization (visually identical)
    
    # Unicode escape sequences
    assert loads('{"test": "\\u0041"}') == {"test": "A"}
    assert loads('{"chinese": "\\u4F60\\u597D"}') == {"chinese": "你好"}
    
    # Invalid Unicode escapes
    assert loads('{"invalid": "\\u00ZZ"}')  # Should handle gracefully
    assert loads('{"incomplete": "\\u00"}')  # Should handle gracefully
    
    # Mixed Unicode and ASCII
    assert loads('{"mixed": "Hello \\u4F60\\u597D World"}')
    
    # Unicode in keys
    assert loads('{\\u4F60\\u597D: "hello"}') == {"你好": "hello"}
    
    # Surrogate pairs for emojis
    assert loads('{"emoji": "\\uD83D\\uDE00"}') == {"emoji": "😀"}
```

### 3. **IEEE 754 Number Edge Cases** (Partially Fixed)
```python
def test_ieee754_edge_cases(self):
    # Infinity values
    assert loads('{"inf": Infinity}')
    assert loads('{"ninf": -Infinity}')
    
    # NaN values
    assert loads('{"nan": NaN}')
    
    # Very large numbers that overflow to infinity
    assert loads('{"big": 1e309}') == {"big": float('inf')}
    
    # Very small numbers that underflow to zero
    assert loads('{"tiny": 1e-325}') == {"tiny": 0.0}
    
    # Edge of IEEE 754 precision
    assert loads('{"max": 1.7976931348623157e+308}')
    assert loads('{"min": 2.2250738585072014e-308}')
    
    # Numbers with extreme exponents
    assert loads('{"exp_max": 1.23e+308}')
    assert loads('{"exp_min": 1.23e-308}')
```

### 4. **Non-Standard Quote Characters** (Missing)
```python
def test_non_standard_quotes(self):
    # Smart quotes
    assert loads('{"test": "value"}') == {"test": "value"}  # U+201C/U+201D
    
    # Guillemets (French quotes)
    assert loads('{"test": «value»}') == {"test": "value"}
    
    # CJK quotes
    assert loads('{"test": 「value」}') == {"test": "value"}
    
    # Backticks as quotes
    assert loads('{test: `value`}') == {"test": "value"}
    
    # Mixed non-standard quotes
    assert loads('{"a": "b", 'c': "d"}')
```

### 5. **Sparse Array Edge Cases** (Partially Tested)
```python
def test_sparse_arrays_comprehensive(self):
    # Double commas
    assert loads('[1,, 3]') == [1, None, 3]
    
    # Triple commas
    assert loads('[1,,, 4]') == [1, None, None, 4]
    
    # Leading sparse elements
    assert loads('[,, 3]') == [None, None, 3]
    
    # Trailing sparse elements  
    assert loads('[1,,]') == [1, None]
    
    # Only sparse elements
    assert loads('[,,]') == [None, None]
    
    # Nested sparse arrays
    assert loads('[1, [,, 3], 4]') == [1, [None, None, 3], 4]
    
    # Sparse in objects
    assert loads('{"arr": [1,, 3]}') == {"arr": [1, None, 3]}
```

### 6. **Error Recovery and Partial Parsing** (Needs Expansion)
```python
def test_comprehensive_error_recovery(self):
    # Mixed valid and invalid fields
    malformed = '''{
        "valid1": "ok",
        "broken": {unclosed: "quote},
        "valid2": "also ok",
        invalid_number: 123.45.67,
        "valid3": [1, 2, 3]
    }'''
    
    result = loads_partial(malformed)
    assert "valid1" in result.data
    assert "valid2" in result.data  
    assert "valid3" in result.data
    assert "broken" not in result.data
    assert len(result.errors) > 0
    
    # Array with mixed valid/invalid elements
    mixed_array = '[1, {broken: }, 3, "valid", invalid_syntax]'
    result = loads_partial(mixed_array)
    assert 1 in result.data
    assert 3 in result.data
    assert "valid" in result.data
```

### 7. **Configuration and Preprocessing** (Missing)
```python
def test_preprocessing_config(self):
    from jsonshiatsu.utils.config import PreprocessingConfig
    
    # Conservative config
    conservative = PreprocessingConfig.conservative()
    
    # Aggressive config
    aggressive = PreprocessingConfig.aggressive()
    
    # Custom config
    custom = PreprocessingConfig(
        extract_from_markdown=True,
        remove_comments=False,
        fix_unescaped_strings=True
    )
    
    # Test with different configs
    markdown_json = '```json\n{"test": "value"}\n```'
    assert loads(markdown_json, config=conservative) != loads(markdown_json, config=aggressive)
```

### 8. **Escape Sequence Handling** (Needs Comprehensive Testing)
```python
def test_escape_sequences_comprehensive(self):
    # Standard JSON escapes
    assert loads('{"test": "\\n\\t\\r\\b\\f\\\\\\/\\""}')
    
    # Unicode escapes
    assert loads('{"test": "\\u0041\\u0042\\u0043"}') == {"test": "ABC"}
    
    # Invalid escapes that should be preserved literally
    assert loads('{"path": "C:\\\\data\\\\file"}')  # File paths
    
    # Mixed valid and invalid escapes
    assert loads('{"mixed": "Valid\\nand\\xinvalid"}')
    
    # Escape sequences in keys
    assert loads('{"\\u0041": "value"}') == {"A": "value"}
    
    # Nested escape sequences
    assert loads('{"test": "\\u0022value\\u0022"}') == {"test": '"value"'}
```

### 9. **Performance and Memory Tests** (Missing)
```python
def test_performance_characteristics(self):
    # Large nested structures
    deep_json = '{"level": ' * 1000 + '"value"' + '}' * 1000
    
    # Large arrays
    big_array = '[' + ','.join(str(i) for i in range(10000)) + ']'
    
    # Large strings
    big_string = '{"data": "' + 'x' * 1000000 + '"}'
    
    # Measure parsing time and memory usage
    import time, psutil, os
    
    process = psutil.Process(os.getpid())
    start_memory = process.memory_info().rss
    start_time = time.time()
    
    result = loads(big_string)
    
    end_time = time.time()
    end_memory = process.memory_info().rss
    
    assert end_time - start_time < 5.0  # Should parse in < 5 seconds
    assert end_memory - start_memory < 100 * 1024 * 1024  # < 100MB additional memory
```

### 10. **Edge Cases in Preprocessing** (Missing)
```python
def test_preprocessing_edge_cases(self):
    # Multiple markdown blocks
    multi_markdown = '''
    First block:
    ```json
    {"first": "value"}
    ```
    
    Second block:
    ```json
    {"second": "value"}
    ```
    '''
    
    # Comments in strings (should not be removed)
    comments_in_strings = '{"message": "This // is not a comment"}'
    
    # Nested function calls
    nested_functions = 'outer(inner({"data": "value"}))'
    
    # Malformed markdown blocks
    broken_markdown = '```json\n{"broken": "no closing fence'
    
    # Empty markdown blocks
    empty_markdown = '```json\n\n```'
```

### 11. **Drop-in Replacement API** (Needs Testing)
```python
def test_json_compatibility(self):
    # Test loads() function with json.loads() parameters
    assert loads('{"test": "value"}', strict=False)
    
    # Test with object_hook
    def hook(obj):
        return {k + "_modified": v for k, v in obj.items()}
    
    result = loads('{"test": "value"}', object_hook=hook)
    assert result == {"test_modified": "value"}
    
    # Test with parse_float
    result = loads('{"num": 3.14}', parse_float=str)
    assert result == {"num": "3.14"}
    
    # Test with parse_int
    result = loads('{"num": 42}', parse_int=str)
    assert result == {"num": "42"}
    
    # Test load() function with file input
    import tempfile, json
    data = {"test": "file_value"}
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        temp_path = f.name
    
    with open(temp_path, 'r') as f:
        result = load(f)
        assert result == data
```

### 12. **Error Messages and Debugging** (Missing)
```python
def test_error_messages_quality(self):
    # Test helpful error messages
    try:
        loads('{"test": }')
    except JSONDecodeError as e:
        assert "expected value" in str(e).lower()
        assert "line 1" in str(e)
        assert "column" in str(e)
    
    # Test error context
    try:
        loads('{\n  "valid": "ok",\n  "broken":,\n  "more": "data"\n}')
    except JSONDecodeError as e:
        assert "line 3" in str(e)  # Should point to broken line
        assert "broken" in str(e)  # Should show context
    
    # Test suggestions
    try:
        loads('{"test" "value"}')  # Missing colon
    except JSONDecodeError as e:
        assert "missing colon" in str(e).lower() or "expected ':'" in str(e).lower()
```

---

## 🔧 **Recommended Test Suite Additions**

### High Priority (Critical Gaps)
1. **Function call pattern tests** (Date, RegExp, ObjectId, etc.)
2. **Unicode handling comprehensive tests**
3. **IEEE 754 edge case tests**
4. **Drop-in replacement API compatibility tests**

### Medium Priority (Important Coverage)
5. **Non-standard quote character tests**
6. **Comprehensive escape sequence tests**
7. **Error message quality tests**
8. **Preprocessing configuration tests**

### Low Priority (Nice to Have)
9. **Performance and memory usage tests**
10. **Complex edge case combinations**
11. **Streaming with malformed JSON tests**
12. **Recovery strategy comprehensive tests**

---

## 📊 **Test File Structure Recommendations**

```
tests/
├── integration/
│   ├── test_malformed_json.py ✅ (existing)
│   ├── test_function_calls.py ❌ (missing)
│   ├── test_unicode_comprehensive.py ❌ (missing)
│   └── test_json_compatibility.py ❌ (missing)
├── unit/
│   ├── core/
│   │   ├── test_engine.py ✅ (existing)
│   │   ├── test_tokenizer.py ✅ (existing)
│   │   └── test_transformer.py ❌ (missing)
│   ├── preprocessing/
│   │   ├── test_config.py ❌ (missing)
│   │   └── test_edge_cases.py ❌ (missing)
│   └── performance/
│       ├── test_memory_usage.py ❌ (missing)
│       └── test_parsing_speed.py ❌ (missing)
```

This analysis shows that while jsonshiatsu has good basic coverage, there are significant gaps in testing the more advanced features and edge cases that make it unique.