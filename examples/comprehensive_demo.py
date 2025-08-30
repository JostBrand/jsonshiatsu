#!/usr/bin/env python3
"""
Comprehensive jsonshiatsu Demo

This single demo showcases ALL capabilities of jsonshiatsu, combining examples
from all use cases into one organized demonstration. Perfect for:

- Understanding what jsonshiatsu can do
- Testing the library's capabilities
- Demonstrations and presentations
- Getting started quickly

Features demonstrated:
✅ Basic malformed JSON handling
✅ Advanced preprocessing features
✅ Security and limits
✅ Streaming capabilities
✅ Error handling and recovery
✅ Real-world use cases
"""

import io
import json
import os
import sys
import time
from typing import Any

# Add jsonshiatsu to path if running as script
if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import jsonshiatsu

try:
    from jsonshiatsu import (
        ParseConfig,
        ParseLimits,
        SecurityError,
    )

    # Optional imports - might not be available in all versions
    try:
        from jsonshiatsu import RecoveryLevel, extract_valid_data, parse_partial

        HAS_RECOVERY = True
    except ImportError:
        HAS_RECOVERY = False
except ImportError:
    # Fallback for basic demo
    ParseConfig = None  # type: ignore
    ParseError = Exception
    ParseLimits = None  # type: ignore
    SecurityError = Exception  # type: ignore
    HAS_RECOVERY = False



def print_section(title: str, subtitle: str = "") -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 80}")
    print(f"🔥 {title}")
    if subtitle:
        print(f"   {subtitle}")
    print("=" * 80)


def print_demo(
    title: str,
    input_json: str,
    result: Any = None,
    config: Any = None,
    show_input: bool = True,
) -> None:
    """Print a demo example with formatting."""
    print(f"\n🎯 {title}")
    print("-" * 60)

    if show_input:
        # Truncate very long inputs for readability
        display_input = (
            input_json if len(input_json) < 200 else input_json[:200] + "..."
        )
        print(f"Input:  {repr(display_input)}")

    try:
        if result is None:
            result = (
                jsonshiatsu.loads(input_json)
                if config is None
                else jsonshiatsu.parse(input_json, config=config)
            )
        print(f"✅ Output: {result}")
    except Exception as e:
        error_msg = str(e).split("\n")[0]  # Just first line of error
        print(f"❌ Error: {type(e).__name__}: {error_msg}")


def demo_basic_features() -> None:
    """Demonstrate basic malformed JSON handling."""
    print_section(
        "BASIC MALFORMED JSON HANDLING", "Core features that make jsonshiatsu special"
    )

    examples = [
        ("Unquoted Keys", '{ test: "this is a test"}'),
        ("Single Quotes", "{'name': 'John', 'age': 30}"),
        ("Mixed Quotes", '{"items": [1, 2, 3,], "active": true,}'),
        ("Unquoted Values", "{name: John, age: 30, active: true}"),
        ("Trailing Commas", '{"key": "value", "array": [1, 2, 3,],}'),
        (
            "JavaScript Comments",
            """{
            // Configuration
            "server": "localhost", /* default host */
            "port": 8080
        }""",
        ),
        ("Python Booleans", '{"active": True, "disabled": False, "empty": None}'),
        ("Yes/No Values", '{"enabled": yes, "visible": no}'),
    ]

    for title, example in examples:
        print_demo(title, example)


def demo_advanced_preprocessing() -> None:
    """Demonstrate advanced preprocessing features."""
    print_section(
        "ADVANCED PREPROCESSING FEATURES",
        "Complex malformed patterns that jsonshiatsu can fix",
    )

    # Markdown extraction
    markdown_json = '```json\n{"status": "success", "data": [1, 2, 3]}\n```'
    print_demo("Markdown Code Block Extraction", markdown_json)

    # Function calls
    function_calls = """
    {
        "timestamp": Date("2025-01-01T00:00:00Z"),
        "object_id": ObjectId("507f1f77bcf86cd799439011"),
        "pattern": RegExp("^[a-zA-Z]+$"),
        "uuid": UUID("550e8400-e29b-41d4-a716-446655440000")
    }
    """
    print_demo("Function Call Wrappers", function_calls)

    # Non-standard quotes
    smart_quotes = """
    {
        "smart": "Hello "world" with smart quotes",
        "guillemets": «French style quotes»,
        "cjk": 「Japanese quotes」,
        "backticks": `Backtick string`
    }
    """
    print_demo("Non-Standard Quote Types", smart_quotes)

    # Sparse arrays
    sparse_arrays = """
    {
        "basic": [1,, 3],
        "multiple": [1,,, 4],
        "leading": [,, 3],
        "trailing": [1, 2,],
        "empty": [,,],
        "single": [,]
    }
    """
    print_demo("Sparse Arrays", sparse_arrays)

    # Complex real-world example
    complex_config = """
    {
        server: {
            host: 'localhost',
            port: 8080,
            ssl: false,
        },
        features: ['auth', 'logging', metrics],
        debug: true,
        message: "Server says \\"Hello world!\\"",
        // Database settings
        database: {
            url: postgres://user:pass@localhost/db,
            timeout: 30
        }
    }
    """
    print_demo("Complex Configuration", complex_config)


def demo_ultimate_example() -> None:
    """Demonstrate the ultimate malformed JSON example."""
    print_section(
        "ULTIMATE MALFORMED JSON SHOWCASE",
        "All features combined in one comprehensive example",
    )

    ultimate_json = """Here's some text before...

```json
{
    // All features in one example
    unquoted_key: "no quotes needed",
    'single_quotes': 'work great',
    "mixed": 'quote styles',
    "trailing_comma": "allowed",

    // Function calls
    "timestamp": Date("2025-01-01T00:00:00Z"),
    "object_id": ObjectId("507f1f77bcf86cd799439011"),

    // Booleans and null
    "python_style": {
        "active": True,
        "disabled": False,
        "empty": None
    },
    "yes_no": {"enabled": yes, "disabled": no},
    "undefined_val": undefined,

    // Arrays with issues
    "simple_array": ["item1", "item2", "item3",],
    "sparse": [1,, 3, , 5],

    // Special quotes and escapes
    "smart_quotes": "Hello "world" example",
    "escapes": "Line1\\nLine2\\tTabbed \\u4F60\\u597D",

    // Numbers
    "scientific": 1.23e-10,
    "large_num": 1.7976931348623157e+308
}
```

And some trailing text explaining the response..."""

    print("\n🌟 ULTIMATE SHOWCASE EXAMPLE")
    print("-" * 60)
    print("This example demonstrates ALL jsonshiatsu features:")

    features = [
        "✅ Unquoted keys",
        "✅ Single quotes",
        "✅ Mixed quotes",
        "✅ Trailing commas",
        "✅ JavaScript comments",
        "✅ Function calls",
        "✅ Python booleans",
        "✅ Yes/No values",
        "✅ Undefined values",
        "✅ Sparse arrays",
        "✅ Smart quotes",
        "✅ Escape sequences",
        "✅ Unicode escapes",
        "✅ Scientific notation",
        "✅ Markdown blocks",
        "✅ Trailing text",
        "✅ Multiple malformation types",
    ]

    for i, feature in enumerate(features, 1):
        print(f"{i:2d}. {feature}")

    print(f"\nInput length: {len(ultimate_json)} characters")
    print("Standard json.loads() would completely fail on this!")
    print("\nParsing with jsonshiatsu...")

    try:
        result = jsonshiatsu.loads(ultimate_json)
        print("✅ SUCCESS! Parsed into clean Python data:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ Error: {e}")


def demo_error_handling() -> None:
    """Demonstrate error handling and partial recovery."""
    print_section(
        "ERROR HANDLING & PARTIAL RECOVERY", "Extract valid data even from broken JSON"
    )

    if not HAS_RECOVERY:
        print("\n⚠️ Recovery features not available in this version")
        print("Showing basic error handling only...")

    # Enhanced error reporting
    print("\n🔍 BASIC ERROR HANDLING:")
    malformed = '{"key": }'  # Missing value

    try:
        result = jsonshiatsu.loads(malformed)
        print(f"❌ Should have failed: {result}")
    except Exception as e:
        error_msg = str(e).split("\n")[0]
        print(f"✅ Error caught: {type(e).__name__}: {error_msg}")

    if HAS_RECOVERY:
        # Partial recovery
        print("\n🛠️ PARTIAL DATA RECOVERY:")
        mixed_data = """
        {
            "valid_id": 12345,
            "valid_name": "Alice",
            "broken_email": invalid_syntax_here,
            "valid_phone": "555-1234",
            "valid_tags": ["user", "active"]
        }
        """

        try:
            result = parse_partial(mixed_data, RecoveryLevel.SKIP_FIELDS)
            print("Input had mixed valid/invalid fields")
            print(f"✅ Extracted valid data: {result.data}")
            print(f"📊 Success rate: {result.success_rate:.1f}%")
            print(f"❌ Skipped {len(result.errors)} broken fields")
        except Exception as e:
            print(f"❌ Recovery demo error: {e}")

        # Quick extraction
        print("\n⚡ QUICK DATA EXTRACTION:")
        quick_data = '{"good": "data", broken: syntax, "more": "good"}'
        try:
            extracted = extract_valid_data(quick_data)
            print(f"Quick extract: {extracted}")
        except Exception as e:
            print(f"❌ Quick extraction error: {e}")
    else:
        print("\n🎯 BASIC GRACEFUL HANDLING:")
        simple_cases = [
            ('{"valid": "data", "number": 42}', "Valid JSON"),
            ('{valid: "data", number: 42}', "Unquoted key"),
            ('{"valid": "data", "broken": }', "Missing value"),
        ]

        for case, desc in simple_cases:
            try:
                result = jsonshiatsu.loads(case)
                print(f"✅ {desc}: {result}")
            except Exception as e:
                error_msg = str(e).split("\n")[0]
                print(f"❌ {desc}: {type(e).__name__}: {error_msg}")


def demo_security_features() -> None:
    """Demonstrate security features and limits."""
    print_section(
        "SECURITY FEATURES & LIMITS", "Protect against malicious or oversized JSON"
    )

    if ParseLimits is None:
        print("\n⚠️ Security features not available in this version")
        print("Showing basic parsing only...")
        basic_examples = [
            ('{"small": "data"}', "Small JSON"),
            ('{"large": "' + "x" * 100 + '"}', "Large JSON"),
        ]
        for example, desc in basic_examples:
            print_demo(desc, example)
        return

    examples = [
        (
            "Input Size Limit",
            ParseLimits(max_input_size=50),
            '{"test": "' + "x" * 100 + '"}',
        ),
        (
            "String Length Limit",
            ParseLimits(max_string_length=10),
            '{"name": "this_string_is_too_long_to_pass"}',
        ),
        (
            "Nesting Depth Limit",
            ParseLimits(max_nesting_depth=2),
            '{"a": {"b": {"c": {"d": "too_deep"}}}}',
        ),
        (
            "Object Keys Limit",
            ParseLimits(max_object_keys=2),
            '{"a": 1, "b": 2, "c": 3, "d": 4}',
        ),
        (
            "Array Items Limit",
            ParseLimits(max_array_items=3),
            "[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]",
        ),
    ]

    for title, limits, test_json in examples:
        print(f"\n🛡️ {title}")
        config = ParseConfig(limits=limits, fallback=False)
        try:
            result = jsonshiatsu.parse(test_json, config=config)
            print(f"❌ Should have been blocked: {result}")
        except SecurityError as e:
            print(f"✅ Correctly blocked: {type(e).__name__}")
        except Exception as e:
            print(f"⚠️ Unexpected error: {e}")

    # Production security config
    print("\n🏭 PRODUCTION SECURITY CONFIGURATION:")
    prod_config = ParseConfig(
        limits=ParseLimits(
            max_input_size=1024 * 1024,  # 1MB
            max_string_length=10000,  # 10KB
            max_nesting_depth=20,  # Reasonable nesting
            max_object_keys=1000,  # 1K keys per object
            max_array_items=10000,  # 10K array items
        ),
        fallback=False,
        aggressive=False,
    )

    safe_json = """
    {
        "api_response": {
            "status": "success",
            "data": [1, 2, 3, 4, 5],
            "metadata": {
                "count": 5,
                "timestamp": "2023-01-01T00:00:00Z"
            }
        }
    }
    """

    try:
        result = jsonshiatsu.parse(safe_json, config=prod_config)
        print("✅ Production-safe JSON parsed successfully")
        print(f"   Status: {result['api_response']['status']}")
    except Exception as e:
        print(f"❌ Production config error: {e}")


def demo_streaming() -> None:
    """Demonstrate streaming capabilities."""
    print_section("STREAMING CAPABILITIES", "Handle large JSON efficiently")

    # Basic streaming
    print("\n💧 BASIC STREAMING:")
    json_data = '{"message": "Hello from stream", "data": [1, 2, 3, 4, 5]}'
    stream = io.StringIO(json_data)
    result = jsonshiatsu.parse(stream)
    print(f"✅ Streamed result: {result}")

    # Large data streaming
    print("\n📊 LARGE DATA STREAMING:")
    large_data = {"items": list(range(1000))}
    json_string = json.dumps(large_data)
    size_kb = len(json_string) / 1024
    print(f"JSON size: {size_kb:.1f} KB")

    # Compare streaming vs regular
    start = time.time()
    result1 = jsonshiatsu.loads(json_string)
    regular_time = time.time() - start

    stream = io.StringIO(json_string)
    start = time.time()
    result2 = jsonshiatsu.parse(stream)
    streaming_time = time.time() - start

    print(f"Regular parsing: {regular_time:.4f}s")
    print(f"Streaming parsing: {streaming_time:.4f}s")
    print(f"Results identical: {result1 == result2}")

    # Streaming with preprocessing
    print("\n⚡ STREAMING + PREPROCESSING:")
    dirty_stream = """```json
    {
        // Config file
        host: "localhost",
        port: 8080,
        features: ["auth", "logging",]
    }
    ```"""

    stream = io.StringIO(dirty_stream)
    result = jsonshiatsu.parse(stream)
    print(f"✅ Preprocessed stream: {result}")


def demo_real_world_use_cases() -> None:
    """Demonstrate real-world use cases."""
    print_section("REAL-WORLD USE CASES", "Practical applications of jsonshiatsu")

    # LLM API responses
    print("\n🤖 LLM API RESPONSE:")
    llm_response = """```json
{"response": "Here is the analysis", "sentiment": "positive", "confidence": 0.95}
```"""

    print_demo("LLM API Response", llm_response, show_input=False)

    # Configuration files
    print("\n⚙️ LEGACY CONFIGURATION FILE:")
    config_file = """
    {
        // Legacy app config
        database: {
            host: "localhost",
            port: 5432,
            'username': "admin",
            "password": "secret123"
        },
        features: ["auth", "logging", "metrics",],
        debug: true
    }
    """

    result = jsonshiatsu.loads(config_file)
    print(f"✅ Config loaded: {list(result.keys())}")

    # Log file processing
    print("\n📄 LOG FILE PROCESSING:")
    log_entries = [
        '{"timestamp": "2023-12-01T10:00:00", "level": "info", "message": "Started"}',
        '{"timestamp": "2023-12-01T10:01:00", "level": "error", message: "Missing quotes"}',
        '{"timestamp": "2023-12-01T10:02:00", "level": "info", "message": "Complete"}',
    ]

    valid_logs = []
    for entry in log_entries:
        data = extract_valid_data(entry)
        if data:
            valid_logs.append(data)

    print(f"✅ Processed {len(valid_logs)}/{len(log_entries)} log entries")
    print(f"   Valid logs: {[log['level'] for log in valid_logs]}")

    # MongoDB exports
    print("\n🍃 MONGODB EXPORT FORMAT:")
    mongo_export = """
    {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "name": "John Doe",
        "created": ISODate("2023-01-01T00:00:00.000Z"),
        "tags": ["user", "active"]
    }
    """

    result = jsonshiatsu.loads(mongo_export)
    print(f"✅ MongoDB export parsed: {result}")


def demo_performance_comparison() -> None:
    """Show performance comparison with standard JSON."""
    print_section("PERFORMANCE COMPARISON", "jsonshiatsu vs standard library")

    # Valid JSON (both should work)
    valid_json = '{"name": "test", "values": [1, 2, 3, 4, 5]}'

    print("\n⚡ VALID JSON COMPARISON:")

    # Standard library
    start = time.time()
    for _ in range(1000):
        json.loads(valid_json)
    std_time = time.time() - start

    # jsonshiatsu
    start = time.time()
    for _ in range(1000):
        jsonshiatsu.loads(valid_json)
    js_time = time.time() - start

    print(f"Standard json.loads(): {std_time:.4f}s (1000 iterations)")
    print(f"jsonshiatsu.loads(): {js_time:.4f}s (1000 iterations)")
    print(f"Overhead: {((js_time - std_time) / std_time * 100):+.1f}%")

    # Malformed JSON (only jsonshiatsu works)
    print("\n🔧 MALFORMED JSON (jsonshiatsu advantage):")
    malformed_json = "{name: 'test', values: [1, 2, 3,]}"

    # Standard library fails
    try:
        json.loads(malformed_json)
        print("❌ Standard library should have failed!")
    except json.JSONDecodeError:
        print("✅ Standard library correctly failed on malformed JSON")

    # jsonshiatsu succeeds
    try:
        result = jsonshiatsu.loads(malformed_json)
        print(f"✅ jsonshiatsu parsed malformed JSON: {result}")
    except Exception as e:
        print(f"❌ jsonshiatsu failed: {e}")


def main() -> None:
    """Run the comprehensive demo."""
    print("🌟 JSONSHIATSU COMPREHENSIVE DEMO")
    print("The ultimate showcase of jsonshiatsu's capabilities")

    # Run all demo sections
    demo_basic_features()
    demo_advanced_preprocessing()
    demo_ultimate_example()
    demo_error_handling()
    demo_security_features()
    demo_streaming()
    demo_real_world_use_cases()
    demo_performance_comparison()

    # Final summary
    print_section(
        "DEMO COMPLETE! 🎉", "jsonshiatsu handles JSON that breaks everything else"
    )

    print(
        """
✅ COMPREHENSIVE FEATURE COVERAGE:
   • Unquoted keys and values     • Single and mixed quotes
   • Trailing commas              • JavaScript comments
   • Function call wrappers       • Python-style booleans
   • Smart quotes and Unicode     • Sparse arrays
   • Markdown code blocks         • Trailing explanatory text
   • Enhanced error reporting     • Partial data recovery
   • Security limits and controls • Streaming for large data
   • Real-world use case support  • Production-ready reliability

🚀 PERFECT FOR:
   • LLM API responses            • Legacy configuration files
   • MongoDB exports              • Log file processing
   • Web scraping data            • JavaScript object literals
   • Copy-pasted JSON snippets    • Any "almost JSON" format

💪 WHY CHOOSE JSONSHIATSU:
   • Handles JSON that breaks standard parsers
   • Graceful error recovery with detailed reporting
   • Security controls for production use
   • Streaming support for large datasets
   • Zero-configuration ease of use
   • Comprehensive malformation support

Ready to handle any JSON thrown at you? That's the power of jsonshiatsu! 🔥
"""
    )


if __name__ == "__main__":
    main()
