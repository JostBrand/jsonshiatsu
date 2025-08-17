# Jsonshiatsu Examples

This directory contains comprehensive examples demonstrating the full capabilities of jsonshiatsu.

## 🌟 Ultimate Malformed Example

**File:** `ultimate_malformed_example.py`

This is the most comprehensive example that demonstrates **ALL** features promised by jsonshiatsu in a single malformed JSON. It includes:

### ✅ Complete Feature Coverage (18 features):

1. **Unquoted object keys**: `{test: "value"}`
2. **Single quotes**: `{'test': 'value'}`  
3. **Mixed quotes**: `{"test": 'value'}`
4. **Trailing commas**: `{"test": "value",}`
5. **Unquoted string values**: `{test: value}`
6. **Embedded quotes**: Proper escaping of quotes in strings
7. **Newlines in strings**: `\n`, `\t`, etc.
8. **Markdown code blocks**: Extract JSON from ````json ... ``` blocks
9. **Trailing explanatory text**: `{"result": "success"} This indicates completion`
10. **JavaScript-style comments**: `// line` and `/* block */` comments
11. **Function call wrappers**: `Date()`, `ObjectId()`, `RegExp()`, etc.
12. **Multiple JSON objects**: Extract first valid JSON from multiple objects
13. **Non-standard boolean/null**: `True`/`False`, `yes`/`no`, `None`, `undefined`
14. **Non-standard quotes**: Smart quotes (`""`), guillemets (`«»`), CJK (`「」`), backticks
15. **Incomplete structures**: Auto-complete missing braces/brackets
16. **All escape sequences**: `\n`, `\t`, `\\`, `\"`, `\/`, Unicode escapes
17. **Sparse arrays**: `[1,, 3]`, `[,,]`, `[,]` patterns
18. **Scientific notation**: `1.23e-10`

### 🚀 Usage:

```python
# Run the complete demonstration
python examples/ultimate_malformed_example.py

# Or import and use in your code
from examples.ultimate_malformed_example import ULTIMATE_MALFORMED_JSON, get_parsed_result
import jsonshiatsu

result = jsonshiatsu.loads(ULTIMATE_MALFORMED_JSON)
print(result)
```

### 💡 Perfect for showcasing:

- **LLM API responses** (often contain mixed formatting)
- **Legacy configuration files** (loose syntax rules)  
- **Real-world messy JSON** (copy-pasted from various sources)
- **JavaScript object literals** (used in web development)
- **MongoDB exports** (ObjectId, ISODate functions)

This example proves that jsonshiatsu truly is the most robust JSON parser for handling real-world malformed data!

## 🎯 Key Takeaway

While Python's standard `json.loads()` would **completely fail** on this malformed JSON nightmare, jsonshiatsu gracefully parses it into clean, valid Python data structures with all malformations resolved.

**That's the power of jsonshiatsu! 🔥**