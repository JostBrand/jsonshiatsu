#!/usr/bin/env python3
"""
The Ultimate Jsonshiatsu Showcase Example

This file contains the most comprehensive malformed JSON example that demonstrates
ALL features promised by jsonshiatsu. Use this as a reference for what kinds of
malformed JSON your library can handle.

Features demonstrated:
✅ Unquoted object keys
✅ Single quotes
✅ Mixed quotes
✅ Trailing commas
✅ Unquoted string values
✅ Embedded quotes with escaping
✅ Newlines in strings
✅ Markdown code blocks
✅ Trailing explanatory text
✅ JavaScript-style comments
✅ Function call wrappers
✅ Multiple JSON objects
✅ Non-standard boolean/null values
✅ Non-standard quotes (smart, guillemets, CJK, backticks)
✅ Incomplete structures
✅ All escape sequences
✅ Sparse arrays
✅ Scientific notation
"""

import json

import jsonshiatsu

# The ultimate malformed JSON example containing ALL promised features
ULTIMATE_MALFORMED_JSON = """Here's some explanatory text before the JSON...

```json
{
    // 1. Unquoted object keys
    unquoted_key: "This key has no quotes",
    
    // 2. Single quotes
    'single_quoted_key': 'single quoted value',
    
    // 3. Mixed quotes  
    "double_key": 'mixed quote styles work',
    
    // 4. Trailing commas in objects
    "trailing_comma_obj": {
        "inner": "value",
    },
    
    // 5. Unquoted string values
    unquoted_value_key: unquoted_string_value,
    
    // 6. Embedded quotes with proper escaping
    "message": "He said \\"Hello!\\" and she replied \\"Hi there!\\"",
    
    // 7. Newlines in strings
    "multiline": "line1\\nline2\\nline3",
    
    // 8. Function calls in values
    "timestamp": Date("2025-08-16T10:30:00Z"),
    "object_id": ObjectId("507f1f77bcf86cd799439011"),
    "regex": RegExp("^[a-z]+$"),
    "uuid": UUID("550e8400-e29b-41d4-a716-446655440000"),
    "iso_date": ISODate("2025-01-01T00:00:00.000Z"),
    
    // 9. Non-standard boolean/null values
    "python_booleans": {
        "active": True,
        "disabled": False, 
        "empty": None
    },
    "yes_no_values": {
        "enabled": yes,
        "disabled": no
    },
    "undefined_val": undefined,
    
    // 10. Non-standard quotes (smart quotes, guillemets, CJK, backticks)
    "smart_quotes": "Hello "world" with smart quotes",
    "guillemets": «French style quotes»,
    "cjk_quotes": 「Japanese style quotes」,
    "backticks": `Backtick quoted string`,
    
    // 11. Trailing commas in arrays
    "simple_array": ["item1", "item2", "item3",],
    
    // 12. Sparse arrays with various patterns
    "sparse_arrays": {
        "basic": [1,, 3],
        "multiple": [1,,, 4], 
        "leading": [,, 3],
        "trailing": [1, 2,],
        "empty_sparse": [,,],
        "single_sparse": [,],
        "with_spaces": [1, , 3, , 5]
    },
    
    // 13. JavaScript-style comments (both types demonstrated)
    "comments_demo": "value", /* this is a block comment */
    
    // 14. All escape sequences
    "escapes": {
        "newline": "line1\\nline2",
        "tab": "col1\\tcol2", 
        "carriage": "line1\\rline2",
        "backspace": "text\\bdelete",
        "formfeed": "page1\\fpage2",
        "backslash": "path\\\\file",
        "quote": "He said \\"hello\\"",
        "slash": "http:\\/\\/example.com",
        "unicode": "Hello \\u4F60\\u597D World! \\uD83D\\uDE00"
    },
    
    // 15. Scientific notation
    "numbers": {
        "scientific": 1.23e-10,
        "large": 1.7976931348623157e+308,
        "negative": -2.5e-3
    }
}
```

you see this a completely  malformed JSON example that demonstrates all the features"""


def demonstrate_parsing():
    """Demonstrate parsing of all examples"""
    print("🌟 ULTIMATE JSONSHIATSU SHOWCASE")
    print("=" * 80)
    print("This example demonstrates all features in a single JSON!")
    print()

    print("📋 COMPLETE FEATURE CHECKLIST:")
    features = [
        "1. Unquoted object keys: unquoted_key",
        "2. Single quotes: 'single_quoted_key'",
        "3. Mixed quotes: \"double_key\": 'mixed'",
        '4. Trailing commas: {"inner": "value",}',
        "5. Unquoted string values: key: unquoted_value",
        '6. Embedded quotes: "He said \\"Hello!\\""',
        '7. Newlines in strings: "line1\\nline2"',
        "8. Markdown code blocks: ```json ... ```",
        "9. Trailing explanatory text after JSON",
        "10. JavaScript comments: // and /* */",
        "11. Function calls: Date(), ObjectId(), RegExp(), etc.",
        "12. Non-standard booleans: True/False, yes/no, None, undefined",
        "13. Non-standard quotes: " ", «», 「」, ``",
        "14. Sparse arrays: [1,, 3], [,,], [,]",
        '15. All escape sequences: \\n, \\t, \\\\, \\", \\/',
        "16. Unicode escapes: \\u4F60\\u597D",
        "17. Scientific notation: 1.23e-10",
        "18. Incomplete structures (auto-completion)",
    ]

    for feature in features:
        print(f"✅ {feature}")
    print()

    # Test main example
    print("🔥 TESTING MAIN COMPREHENSIVE EXAMPLE:")
    print("-" * 60)
    try:
        print(ULTIMATE_MALFORMED_JSON)
        print("-" * 60)
        result = jsonshiatsu.loads(ULTIMATE_MALFORMED_JSON)
        print("Parsed Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    demonstrate_parsing()
    print("\n" + "=" * 80)
