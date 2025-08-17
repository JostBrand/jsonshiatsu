"""
Demonstration of jsonshiatsu's handling of malformed JSON patterns.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import jsonshiatsu


def main():
    print("jsonshiatsu - Malformed JSON Handling Demo")
    print("=" * 50)

    examples = [
        # Markdown code blocks
        (
            """```json
        {"name": "Alice", "status": "active"}
        ```""",
            "JSON in markdown code block",
        ),
        # Trailing explanatory text
        (
            '{"result": "success"} This indicates the operation completed.',
            "JSON with trailing explanation",
        ),
        # JavaScript comments
        (
            """{
            // User configuration
            "theme": "dark", /* preferred theme */
            "auto_save": true
        }""",
            "JSON with JavaScript-style comments",
        ),
        # Function call wrapper
        ('return {"data": [1, 2, 3]};', "JSON wrapped in return statement"),
        # Multiple JSON objects
        ('{"first": "object"} {"second": "object"}', "Multiple JSON objects"),
        # Non-standard boolean values
        (
            '{"active": True, "disabled": False, "empty": None}',
            "Python-style boolean/null values",
        ),
        # Yes/No values
        ('{"enabled": yes, "visible": no}', "Yes/No as boolean values"),
        # Incomplete JSON (aggressive mode)
        ('{"user": {"name": "Bob", "data": [1, 2', "Incomplete JSON structure"),
    ]

    for i, (json_str, description) in enumerate(examples, 1):
        print(f"\n{i}. {description}")
        print(f"Input:  {repr(json_str)}")

        try:
            # Use aggressive mode for the incomplete JSON example
            aggressive = "Incomplete" in description
            result = jsonshiatsu.parse(json_str, aggressive=aggressive)
            print(f"Output: {result}")
        except Exception as e:
            print(f"Error:  {e}")

    print("\n" + "=" * 50)
    print("Complex example combining multiple malformed patterns:")

    complex_example = """```json
    {
        // API response
        "status": "success", /* operation completed */
        "user": {
            "active": True,
            "preferences": {
                "notifications": yes,
                "theme": "dark"
            }
        },
        "data": [1, 2, 3] // numeric data
    }
    ``` This response includes user preferences and numeric data."""

    print(f"Input: {repr(complex_example)}")
    try:
        result = jsonshiatsu.parse(complex_example)
        print(f"Output: {result}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
