# jsonshiatsu

A therapeutic JSON parser for Python that gently massages malformed JSON back into shape. Like the Japanese healing art of shiatsu, this library applies just the right pressure points to transform broken JSON into something beautiful and usable.

Perfect for real-world scenarios where JSON may be improperly formatted, including LLM APIs, legacy systems, and user-generated content that can't be controlled. If you can control the model better use jsonformer. Regex is always an attack surface, be cautious when using this library.

## Features

### Basic Malformed JSON Patterns

- **Unquoted object keys**: `{test: "value"}`
- **Single quotes**: `{'test': 'value'}`
- **Mixed quotes**: `{"test": 'value'}`
- **Trailing commas**: `{"test": "value",}`
- **Unquoted string values**: `{test: value}`

### Advanced Preprocessing

- **Sparse arrays**: `[1,, 3]` → `[1, null, 3]`
- **String concatenation**: `["urgent" "important"]` → `["urgentimportant"]`
- **Assignment operators**: `"id" = 1` → `"id": 1`
- **Markdown code blocks**: Extract JSON from ` ```json ... ``` ` blocks
- **Trailing explanatory text**: `{"result": "success"} This indicates completion`
- **JavaScript-style comments**: `{"key": "value" /* comment */}` and `// line comments`
- **Function call wrappers**: `Date("2025-01-01")`, `ObjectId("...")`, `RegExp("...")`, `UUID("...")`
- **Multiple JSON objects**: Extract the first valid JSON from multiple objects
- **Incomplete structures**: Automatically close missing braces/brackets

### Data Type Handling

- **Non-standard boolean/null**: `True`/`False`, `yes`/`no`, `None`, `undefined`
- **IEEE 754 special numbers**: `Infinity`, `-Infinity`, `NaN`
- **Unicode escape sequences**: `\u4F60\u597D` → proper Unicode characters
- **Complex escape sequences**: All standard JSON escapes plus error recovery

## Installation

```bash
pip install jsonshiatsu
```

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

### Advanced Usage

```python
import jsonshiatsu

# Handle duplicate keys by creating arrays
result = jsonshiatsu.parse('{"key": "value1", "key": "value2"}', duplicate_keys=True)
print(result)  # {'key': ['value1', 'value2']}

# Enable aggressive preprocessing for malformed JSON
result = jsonshiatsu.parse('return {"status": "ok"};', aggressive=True)
print(result)  # {'status': 'ok'}

# Parse with security limits
from jsonshiatsu import ParseConfig, ParseLimits

config = ParseConfig(
    limits=ParseLimits(
        max_input_size=1024*1024,  # 1MB max
        max_nesting_depth=20,
        max_array_items=1000
    )
)
result = jsonshiatsu.parse(large_json, config=config)
```

### Streaming Large Files

```python
import jsonshiatsu

# Stream large JSON files
with open('large_file.json', 'r') as f:
    result = jsonshiatsu.load(f)

# Or parse large strings efficiently  
large_json = "..." # Very large JSON string
result = jsonshiatsu.loads(large_json)  # Automatic streaming if > threshold
```

## Real-World Examples

### LLM API Response (Multiple Issues)

```python
import jsonshiatsu as json

llm_response = """```json
{
    // AI-generated response with mixed issues
    "response": {
        "message": "Hello! I'd say "welcome" to you.",
        'confidence': 0.95,
        "timestamp": Date("2025-08-16T10:30:00Z"),
        "categories": ["greeting", "polite",],  // trailing comma
        metadata: {
            model: gpt-4,           // unquoted values  
            tokens: 150,
            'temperature': 0.7      // mixed quotes
        }
    },
    "status": "success", /* Operation completed */
    debug_info: {
        "processing_time": 1.23e-2,
        "memory_usage": "45MB", 
        errors: [],              // empty trailing comma
        "special_numbers": [Infinity, -Infinity, NaN]
    }
}
```

This response succeeds where standard JSON parsing completely fails.

### Legacy Configuration File

```python
legacy_config = """
{
    // Legacy system config - circa 2010
    database: {
        host: 'localhost',
        port: 5432,
        "username" = "admin",     // assignment operator
        'password': "secret123"
    },
    features: ["auth", "logging", "metrics",],
    debug: True,                  // Python boolean
    "sparse_data": [1,, 3,, 5],  // sparse array
    undefined_setting: undefined
}
"""

result = json.loads(legacy_config)
# Successfully parses complex legacy format
```

### MongoDB Export Format

```python
mongo_export = """
{
    "_id": ObjectId("507f1f77bcf86cd799439011"),
    "name": "John Doe", 
    "created": ISODate("2023-01-01T00:00:00.000Z"),
    "email": RegExp("^[\\w._%+-]+@[\\w.-]+\\.[A-Z]{2,}$"),
    "tags": ["user", "active"]
}
"""

result = json.loads(mongo_export)
# Handles MongoDB function calls correctly
```

### String Concatenation & Sparse Arrays

```python
complex_json = """
{
    "messages": ["urgent" "important"],  // concatenated strings
    "data": [1,, 3,, 5],                // sparse array  
    "unicode": "Hello \\u4F60\\u597D",   // Unicode escapes
    "metadata": {
        "items"= [,, "last"],            // assignment + sparse
        timestamp: Date("2025-01-01")
    }
}
"""

result = json.loads(complex_json)  
# Result: messages=["urgentimportant"], data=[1,None,3,None,5], etc.
```


## Current Limitations

- **Regex-based preprocessing**: Some complex edge cases may need manual handling
- **Security consideration**: Aggressive preprocessing should only be used with trusted inputs
- **Memory usage**: Complex malformed JSON requires additional processing memory
- **Non-standard quotes**: Limited support for some exotic quote types
