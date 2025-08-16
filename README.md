# jsonshiatsu 🤲

A *therapeutic* JSON parser for Python that gently massages malformed JSON back into shape. Like the Japanese healing art of shiatsu, this library applies just the right pressure points to transform broken JSON into something beautiful and usable.

Perfect for real-world scenarios where JSON may be improperly formatted, including LLM APIs, legacy systems, and user-generated content that can't be controlled.

## Features

jsonshiatsu can heal JSON-like strings that would normally cause standard JSON parsing to fail, including:

- **Unquoted object keys**: `{test: "value"}`
- **Single quotes**: `{'test': 'value'}`
- **Mixed quotes**: `{"test": 'value'}`
- **Trailing commas**: `{"test": "value",}`
- **Unquoted string values**: `{test: value}`
- **Embedded quotes with proper escaping**
- **Newlines in strings**

### Advanced Therapeutic Techniques

With deep tissue massage mode, jsonshiatsu can also heal:

- **Markdown code blocks**: Extract JSON from ` ```json ... ``` ` blocks
- **Trailing explanatory text**: `{"result": "success"} This indicates completion`
- **JavaScript-style comments**: `{"key": "value" /* comment */}` and `// line comments`
- **Function call wrappers**: `return {"data": [1, 2, 3]};` or `parse_json(...)`
- **Multiple JSON objects**: Extract the first valid JSON from multiple objects
- **Non-standard boolean/null**: `True`/`False`, `yes`/`no`, `None`, `undefined`
- **Non-standard quotes**: Smart quotes (`""`), guillemets (`«»`), CJK quotes (`「」`), backticks
- **Incomplete structures**: Automatically close missing braces/brackets

### Security & Performance Features

jsonshiatsu now includes enterprise-ready features for secure and efficient parsing:

- **Input sanitization**: Configurable limits on input size, string length, nesting depth, and structure sizes
- **Enhanced error reporting**: Detailed error messages with position tracking, context, and helpful suggestions
- **Streaming support**: Parse large JSON files without loading entire content into memory
- **Security limits**: Prevent DoS attacks and resource exhaustion with configurable validation

## Installation

Not yet submitted to pip.

```bash
pip install jsonshiatsu
```

## Migration from `json`

jsonshiatsu is designed to be a **seamless drop-in replacement**:

```python
# Before
import json
data = json.loads(json_string)
with open('file.json') as f:
    data = json.load(f)

# After - just change the import!
import jsonshiatsu as json
data = json.loads(json_string)     # Now handles malformed JSON too!
with open('file.json') as f:
    data = json.load(f)           # Now handles malformed JSON too!
```

**100% Compatibility**: All existing code using `json.loads()` and `json.load()` will work without any changes.

## Usage

### Drop-in Replacement for `json`

The easiest way to use jsonshiatsu is as a direct replacement for Python's `json` module:

```python
# Instead of: import json
import jsonshiatsu as json

# All standard json functionality works exactly the same
data = json.loads('{"name": "Alice", "age": 30}')

# But now malformed JSON also works!
data = json.loads('{ test: "this is a test"}')  # Unquoted keys
data = json.loads("{'name': 'John', age: 30}")  # Single quotes  
data = json.loads('{"items": [1, 2, 3,]}')      # Trailing commas

# File loading
with open('config.json') as f:
    config = json.load(f)

# All json.loads parameters supported
from decimal import Decimal
data = json.loads('{"price": 123.45}', parse_float=Decimal)
```

### Advanced jsonshiatsu Features

```python
import jsonshiatsu

# Strict mode for conservative parsing
result = jsonshiatsu.loads(malformed_json, strict=True)

# Handle very malformed JSON
malformed = '''```json
{
    // Configuration
    "active": True,
    "path": "C:\\data\\file",
    "items": [1, 2, 3
}
``` This is incomplete but jsonshiatsu can handle it.'''

result = jsonshiatsu.loads(malformed)  # Auto-completes missing bracket
print(result)  # {'active': True, 'path': 'C:\\data\\file', 'items': [1, 2, 3]}

# Legacy API still available
result = jsonshiatsu.parse(malformed, aggressive=True)
```

### Options

```python
# Handle duplicate keys by creating arrays
result = jsonshiatsu.parse('{"key": "value1", "key": "value2"}', duplicate_keys=True)
print(result)  # {'key': ['value1', 'value2']}

# Enable aggressive preprocessing for malformed JSON
result = jsonshiatsu.parse('return {"status": "ok"};', aggressive=True)
print(result)  # {'status': 'ok'}
```

### Advanced Configuration

For production use with security requirements:

```python
from jsonshiatsu import parse, ParseConfig, ParseLimits

# Configure security limits
config = ParseConfig(
    limits=ParseLimits(
        max_input_size=1024 * 1024,      # 1MB max input
        max_string_length=10000,         # 10KB max string
        max_nesting_depth=20,            # Max 20 levels deep
        max_object_keys=1000,            # Max 1000 keys per object
        max_array_items=10000,           # Max 10K array items
        max_total_items=100000           # Max 100K total parsed items
    ),
    include_position=True,               # Enhanced error reporting
    include_context=True,                # Show error context
    fallback=False                       # Don't fall back to unsafe parsing
)

# Parse with security limits
try:
    result = parse(untrusted_json, config=config)
except SecurityError as e:
    print(f"Security limit exceeded: {e}")
except ParseError as e:
    print(f"Parse error with context: {e}")
```

### Streaming Large Files

```python
# Parse large files without loading into memory
with open('large_data.json', 'r') as f:
    result = parse(f)  # Automatically uses streaming

# Or explicitly configure streaming threshold
config = ParseConfig(streaming_threshold=1024 * 1024)  # 1MB
result = parse(large_json_string, config=config)
```

## API Reference

### `jsonshiatsu.loads(s, *, strict=False, config=None, **json_kwargs)`

**Drop-in replacement for `json.loads()`** - supports all standard parameters plus jsonshiatsu features.

**Standard json.loads parameters:**
- `s` (str, bytes, bytearray): JSON string to parse
- `cls`: Custom JSONDecoder class (ignored) 
- `object_hook`: Function called for each decoded object
- `parse_float`: Function to parse JSON floats
- `parse_int`: Function to parse JSON integers
- `parse_constant`: Function to parse constants (Infinity, NaN)
- `object_pairs_hook`: Function called with ordered pairs for each object

**jsonshiatsu-specific parameters:**
- `strict` (bool): If True, use conservative preprocessing only (default: False)
- `config` (ParseConfig): Advanced configuration object

**Returns:** Parsed Python data structure

**Raises:** `json.JSONDecodeError` (for compatibility with standard json)

### `jsonshiatsu.load(fp, *, strict=False, config=None, **json_kwargs)`

**Drop-in replacement for `json.load()`** - same as `loads()` but reads from a file.

### `jsonshiatsu.parse(text, fallback=True, duplicate_keys=False, aggressive=False, config=None)`

**Legacy jsonshiatsu API** - use `loads()`/`load()` for new code.

**Parameters:**
- `text` (str or file-like): JSON string or file object
- `fallback` (bool): Enable fallback to standard JSON (default: True)
- `duplicate_keys` (bool): Handle duplicate keys as arrays (default: False)
- `aggressive` (bool): Enable aggressive preprocessing (default: False) 
- `config` (ParseConfig): Advanced configuration

**Returns:** Parsed Python data structure

**Raises:** `ParseError`, `SecurityError`, or `json.JSONDecodeError`

### `ParseConfig` Class

Configuration options for parsing behavior and security.

**Parameters:**
- `limits` (ParseLimits): Security limits for safe parsing
- `fallback` (bool): Enable fallback to standard JSON parser
- `duplicate_keys` (bool): Handle duplicate keys by creating arrays
- `aggressive` (bool): Enable aggressive preprocessing (deprecated, use `preprocessing_config`)
- `preprocessing_config` (PreprocessingConfig): Granular control over preprocessing steps
- `include_position` (bool): Include position information in errors
- `include_context` (bool): Include context around errors
- `max_error_context` (int): Maximum characters of error context to show
- `streaming_threshold` (int): File size threshold for automatic streaming

### `PreprocessingConfig` Class

Granular control over individual preprocessing steps.

**Features:**
- `extract_from_markdown` (bool): Extract JSON from markdown code blocks
- `remove_comments` (bool): Remove JavaScript-style comments
- `unwrap_function_calls` (bool): Remove function call wrappers
- `extract_first_json` (bool): Extract first JSON from multiple objects
- `remove_trailing_text` (bool): Remove text after JSON
- `normalize_quotes` (bool): Convert smart quotes to standard quotes
- `normalize_boolean_null` (bool): Convert Python-style True/False/None
- `fix_unescaped_strings` (bool): Fix backslash escaping in file paths
- `handle_incomplete_json` (bool): Auto-complete missing braces/brackets

**Presets:**
- `PreprocessingConfig.conservative()`: Only safe transformations
- `PreprocessingConfig.aggressive()`: All transformations enabled
- `PreprocessingConfig.from_features(set)`: Enable specific features

**Example:**
```python
from jsonshiatsu import parse, ParseConfig, PreprocessingConfig

# Only fix string escaping issues
config = ParseConfig(
    preprocessing_config=PreprocessingConfig.from_features({'fix_unescaped_strings'})
)
result = parse('{"path": "C:\\data\\file"}', config=config)

# Conservative preset - safe transformations only
conservative = ParseConfig(preprocessing_config=PreprocessingConfig.conservative())
```

### `ParseLimits` Class

Security limits to prevent resource exhaustion attacks.

**Parameters:**
- `max_input_size` (int): Maximum input size in bytes (default: 10MB)
- `max_string_length` (int): Maximum string length (default: 1MB)
- `max_number_length` (int): Maximum number string length (default: 100)
- `max_nesting_depth` (int): Maximum nesting depth (default: 100)
- `max_object_keys` (int): Maximum keys per object (default: 10,000)
- `max_array_items` (int): Maximum items per array (default: 100,000)
- `max_total_items` (int): Maximum total parsed items (default: 1,000,000)

## Examples

### Real-world scenarios

```python
import jsonshiatsu

# Configuration files with relaxed syntax
config = jsonshiatsu.parse('''
{
    server: {
        host: 'localhost',
        port: 8080,
        ssl: false,
    },
    features: ['auth', 'logging', 'metrics'],
    debug: true
}
''')

# API responses with non-standard formatting
api_response = jsonshiatsu.parse('''
{
    users: [
        {name: 'Alice', age: 25},
        {name: 'Bob', age: 30},
    ],
    total: 2,
    success: true
}
''')

# Handling embedded quotes
text_with_quotes = jsonshiatsu.parse('''
{
    message: "He said \\"Hello world!\\"",
    html: '<div class="container">Content</div>'
}
''')
```

## Security Considerations

⚠️ **Important**: This library is designed for situations where you need to parse non-standard JSON from external sources. It should not be used as a replacement for proper JSON formatting in your own applications.

### Production Use

jsonshiatsu now includes security features that make it suitable for production use:

- ✅ **Configurable security limits** prevent resource exhaustion attacks
- ✅ **Input validation** blocks oversized or malicious inputs  
- ✅ **Streaming support** handles large files efficiently
- ✅ **Enhanced error reporting** aids in debugging and monitoring
- ✅ **No fallback mode** ensures predictable parsing behavior

### Limitations

- Some complex edge cases may not be handled perfectly
- Performance on very small inputs may be slower than standard JSON due to additional validation
- Aggressive preprocessing mode should only be used with trusted inputs
- Regular expressions in preprocessing may have performance implications with very large inputs

### Recommendations

- **For untrusted input**: Use `ParseConfig` with strict limits and `fallback=False`
- **For large files**: Enable streaming with appropriate thresholds
- **For debugging**: Enable position tracking and error context
- **For production**: Set up monitoring for `SecurityError` exceptions

## Development

### Running tests

```bash
# Run all tests
python -m unittest discover tests/ -v

# Run specific test categories
python -m unittest tests.test_parser -v      # Original functionality
python -m unittest tests.test_security -v    # Security features
python -m unittest tests.test_errors -v      # Error reporting
python -m unittest tests.test_streaming -v   # Streaming functionality
```

### Running examples

```bash
# Basic functionality demo
PYTHONPATH=. python examples/demo.py

# Security features demo
PYTHONPATH=. python examples/security_demo.py

# Error reporting demo  
PYTHONPATH=. python examples/error_demo.py

# Streaming functionality demo
PYTHONPATH=. python examples/streaming_demo.py
```

### Running with coverage

```bash
python -m pytest tests/ --cov=jsonshiatsu --cov-report=html
```

## License

This project is licensed under the MIT License with Attribution - see the LICENSE file for details.

**Usage Rights:**
- ✅ Commercial use
- ✅ Private use  
- ✅ Modification
- ✅ Distribution
- ✅ Forking and derivative works

**Requirements:**
- Attribution must be provided (see LICENSE for details)
- License and copyright notice must be included with copies

Simple attribution examples:
- "Powered by jsonshiatsu" in your app's About section
- "Uses jsonshiatsu library" in documentation  
- Link to this repository when technically feasible

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

jsonshiatsu was designed from the ground up to provide robust, secure JSON parsing for production environments. Special thanks to the open-source community for contributions and feedback.
