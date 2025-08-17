# jsonshiatsu 🤲

A *therapeutic* JSON parser for Python that gently massages malformed JSON back into shape. Like the Japanese healing art of shiatsu, this library applies just the right pressure points to transform broken JSON into something beautiful and usable.

Perfect for real-world scenarios where JSON may be improperly formatted, including LLM APIs, legacy systems, and user-generated content that can't be controlled. If you can control the model better use jsonformer. Regex is always an attack surface, be cautious when using this library.

## Features

jsonshiatsu can heal JSON-like strings that would normally cause standard JSON parsing to fail, including:

- **Unquoted object keys**: `{test: "value"}`
- **Single quotes**: `{'test': 'value'}`
- **Mixed quotes**: `{"test": 'value'}`
- **Trailing commas**: `{"test": "value",}`
- **Unquoted string values**: `{test: value}`
- **Embedded quotes with proper escaping**
- **Newlines in strings**
- **Markdown code blocks**: Extract JSON from ` ```json ... ``` ` blocks
- **Trailing explanatory text**: `{"result": "success"} This indicates completion`
- **JavaScript-style comments**: `{"key": "value" /* comment */}` and `// line comments`
- **Function call wrappers**: `return {"data": [1, 2, 3]};` or `parse_json(...)`
- **Multiple JSON objects**: Extract the first valid JSON from multiple objects
- **Non-standard boolean/null**: `True`/`False`, `yes`/`no`, `None`, `undefined`
- **Non-standard quotes**: Smart quotes (`""`), guillemets (`«»`), CJK quotes (`「」`), backticks
- **Incomplete structures**: Automatically close missing braces/brackets

## Installation

Not yet submitted to pip.

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

### Options

```python
# Handle duplicate keys by creating arrays
result = jsonshiatsu.parse('{"key": "value1", "key": "value2"}', duplicate_keys=True)
print(result)  # {'key': ['value1', 'value2']}

# Enable aggressive preprocessing for malformed JSON
result = jsonshiatsu.parse('return {"status": "ok"};', aggressive=True)
print(result)  # {'status': 'ok'}
```

### `ParseLimits` Class

You can limit the lenght, depth and count of the data.

**Parameters:**
- `max_input_size` (int): Maximum input size in bytes (default: 10MB)
- `max_string_length` (int): Maximum string length (default: 1MB)
- `max_number_length` (int): Maximum number string length (default: 100)
- `max_nesting_depth` (int): Maximum nesting depth (default: 100)
- `max_object_keys` (int): Maximum keys per object (default: 10,000)
- `max_array_items` (int): Maximum items per array (default: 100,000)
- `max_total_items` (int): Maximum total parsed items (default: 1,000,000)

## Examples

### Real-world nightmares

```python
        llm_response = """```json
        {
            // Generated response
            "response": {
                "message": "Hello! I'd say "welcome" to you.",
                'confidence': 0.95,
                "timestamp": Date("2025-08-16T10:30:00Z"),
                "metadata": {
                    model: gpt-4,
                    tokens: 150,
                    "categories": ["greeting", "polite",],
                    settings: {
                        temperature: 0.7,
                        'max_tokens': 1000
                    }
                }
            },
            "status": "success", // Operation completed
            debug_info: {
                "processing_time": 1.23e-2,
                "memory_usage": "45MB",
                errors: [],
            }
        }

```

### Limitations

- Some complex edge cases may not be handled perfectly
- Aggressive preprocessing mode should only be used with trusted inputs
- Performance can be much slower than regular json parsing. Use it only on malformed input.

