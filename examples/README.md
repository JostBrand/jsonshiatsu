# jsonshiatsu Examples

This directory contains a comprehensive demonstration of jsonshiatsu's capabilities.

## 🌟 Comprehensive Demo

**File:** `comprehensive_demo.py`

The **complete showcase** of all jsonshiatsu features in one organized demonstration. Perfect for:

- **Learning** what jsonshiatsu can do
- **Testing** all library capabilities  
- **Presentations** and demonstrations
- **Getting started** quickly

### 🚀 Run the Demo

```bash
# Run the complete demonstration
python examples/comprehensive_demo.py

# Or run from project root
python -m examples.comprehensive_demo
```

### 📋 What's Included

The demo covers **ALL** jsonshiatsu capabilities:

#### **Basic Malformed JSON Handling**
- Unquoted keys: `{test: "value"}`
- Single quotes: `{'key': 'value'}`
- Mixed quotes: `{"key": 'value'}`
- Trailing commas: `{"key": "value",}`
- Unquoted values: `{key: value}`
- JavaScript comments: `// and /* */`
- Python booleans: `True/False/None`

#### **Advanced Preprocessing**
- Markdown code blocks: Extract JSON from ````json ... ``` blocks
- Function call wrappers: `Date()`, `ObjectId()`, `RegExp()`, etc.
- Non-standard quotes: Smart quotes (`""`), guillemets (`«»`), CJK (`「」`)
- Sparse arrays: `[1,, 3]`, `[,,]`, `[,]` patterns
- Complex configurations with mixed malformation types

#### **Error Handling & Recovery**
- Enhanced error reporting with position and context
- Partial data recovery from broken JSON
- Skip invalid fields while preserving valid data
- Multiple recovery levels and strategies

#### **Security & Limits**
- Input size limits for DoS protection
- String length and nesting depth controls
- Object keys and array items limits
- Production-ready security configurations

#### **Streaming Capabilities**
- Large JSON efficient processing
- Stream from files, StringIO, or other sources
- Performance comparisons vs regular parsing
- Streaming with preprocessing enabled

#### **Real-World Use Cases**
- LLM API responses (often malformed)
- Legacy configuration files
- Log file processing with mixed formats
- MongoDB exports with function calls
- Web scraping "almost JSON" data

#### **Performance Analysis**
- Comparison with standard `json` library
- Overhead analysis for valid JSON
- Advantage demonstration for malformed JSON

### 🎯 Key Benefits Demonstrated

1. **Robustness**: Handles JSON that breaks everything else
2. **Flexibility**: Multiple parsing modes and configurations
3. **Security**: Built-in protections against malicious input
4. **Performance**: Efficient processing even for large data
5. **Recovery**: Extract valid data from partially broken JSON
6. **Production-Ready**: Comprehensive error handling and limits

### 💡 Perfect for Showcasing

- **LLM API responses** (often contain mixed formatting)
- **Legacy configuration files** (loose syntax rules)  
- **Real-world messy JSON** (copy-pasted from various sources)
- **JavaScript object literals** (used in web development)
- **MongoDB exports** (ObjectId, ISODate functions)

## 🌟 Ultimate Malformed Example

The demo includes the **Ultimate Malformed JSON Example** that demonstrates ALL 18 promised features in a single JSON structure. This proves that jsonshiatsu truly is the most robust JSON parser for handling real-world malformed data!

While Python's standard `json.loads()` would **completely fail** on these examples, jsonshiatsu gracefully parses them into clean, valid Python data structures.

**That's the power of jsonshiatsu! 🔥**

## 🚀 Quick Start

```python
import jsonshiatsu

# The kind of JSON that breaks standard parsers
malformed = """
{
    name: "Alice",           // Unquoted key
    'age': 30,              // Single quotes  
    "city": 'New York',     // Mixed quotes
    "tags": ["user", "active",],  // Trailing comma
    active: true,           // Unquoted boolean
}
"""

# jsonshiatsu handles it effortlessly
result = jsonshiatsu.loads(malformed)
print(result)  # Clean Python dictionary!
```

Run the comprehensive demo to see hundreds more examples like this! 🎉