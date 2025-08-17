"""
jsonshiatsu demonstration script.
"""

import jsonshiatsu


def main():
    print("jsonshiatsu - Permissive JSON Parser Demo")
    print("=" * 40)

    examples = [
        # Basic unquoted keys
        ('{ test: "this is a test"}', "Unquoted keys"),
        # Single quotes
        ("{'name': 'John', 'age': 30}", "Single quotes"),
        # Mixed quotes and trailing commas
        ('{"items": [1, 2, 3,], "active": true,}', "Mixed quotes and trailing commas"),
        # Unquoted values
        ("{name: John, age: 30, active: true}", "Unquoted values"),
        # Complex real-world example
        (
            """
        {
            server: {
                host: 'localhost',
                port: 8080,
                ssl: false,
            },
            features: ['auth', 'logging', metrics],
            debug: true,
            message: "Server says \\"Hello world!\\"",
        }
        """,
            "Complex configuration",
        ),
        # Duplicate keys
        ('{"test": "value1", "test": "value2"}', "Duplicate keys (default behavior)"),
    ]

    for i, (json_str, description) in enumerate(examples, 1):
        print(f"\n{i}. {description}")
        print(f"Input:  {json_str.strip()}")

        try:
            result = jsonshiatsu.parse(json_str)
            print(f"Output: {result}")
        except Exception as e:
            print(f"Error:  {e}")

    # Demonstrate duplicate keys handling
    print(f"\n{len(examples) + 1}. Duplicate keys (array mode)")
    duplicate_example = '{"test": "value1", "test": "value2"}'
    print(f"Input:  {duplicate_example}")
    try:
        result = jsonshiatsu.parse(duplicate_example, duplicate_keys=True)
        print(f"Output: {result}")
    except Exception as e:
        print(f"Error:  {e}")


if __name__ == "__main__":
    main()
