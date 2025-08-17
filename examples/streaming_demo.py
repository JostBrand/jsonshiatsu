"""
Streaming functionality demonstration for jsonshiatsu.
"""

import io
import json
import os
import tempfile

import jsonshiatsu
from jsonshiatsu import ParseConfig


def main():
    print("jsonshiatsu - Streaming Features Demo")
    print("=" * 40)

    # Example 1: Basic streaming from string
    print("\n1. Basic Streaming from StringIO")
    json_data = '{"message": "Hello from stream", "data": [1, 2, 3, 4, 5]}'
    stream = io.StringIO(json_data)

    result = jsonshiatsu.parse(stream)
    print(f"✓ Streamed result: {result}")

    # Example 2: Large data automatic streaming
    print("\n2. Automatic Streaming for Large Data")
    # Create data larger than default streaming threshold
    large_data = {"items": list(range(100000))}  # Large list
    json_string = json.dumps(large_data)
    print(f"  JSON size: {len(json_string):,} characters")

    # This will automatically use streaming
    config = ParseConfig(streaming_threshold=50000)  # 50KB threshold
    result = jsonshiatsu.parse(json_string, config=config)
    print(f"✓ Large data parsed, item count: {len(result['items'])}")

    # Example 3: Streaming with preprocessing
    print("\n3. Streaming with Preprocessing")
    dirty_stream_data = """```json
    {
        // Configuration file
        "server": {
            "host": "localhost",
            "port": 8080,
            "ssl": false
        },
        "features": ["auth", "logging"],
        "debug": true,
    }
    ```"""

    stream = io.StringIO(dirty_stream_data)
    config = ParseConfig(aggressive=True)
    result = jsonshiatsu.parse(stream, config=config)
    print(f"✓ Preprocessed stream result: {result}")

    # Example 4: Streaming from file
    print("\n4. Streaming from File")
    test_data = {
        "users": [
            {"id": i, "name": f"User{i}", "active": i % 2 == 0} for i in range(1000)
        ],
        "metadata": {"total": 1000, "generated": "2023-01-01T00:00:00Z"},
    }

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(test_data, f, indent=2)
        temp_file = f.name

    try:
        print(f"  Reading from file: {temp_file}")
        with open(temp_file, "r") as f:
            result = jsonshiatsu.parse(f)
            print(f"✓ File streaming result: {len(result['users'])} users loaded")
            print(f"  First user: {result['users'][0]}")
            print(f"  Last user: {result['users'][-1]}")
    finally:
        os.unlink(temp_file)

    # Example 5: Streaming with security limits
    print("\n5. Streaming with Security Limits")
    from jsonshiatsu import ParseLimits, SecurityError

    # Create data that will exceed limits
    risky_data = {"huge_string": "x" * 10000}
    json_string = json.dumps(risky_data)

    config = ParseConfig(
        limits=ParseLimits(max_string_length=5000),
        streaming_threshold=1000,  # Force streaming
    )

    try:
        result = jsonshiatsu.parse(json_string, config=config)
        print(f"✗ Should have failed: {result}")
    except SecurityError as e:
        print(f"✓ Security limit enforced in streaming: {type(e).__name__}")

    # Example 6: Streaming nested structures
    print("\n6. Streaming Complex Nested Structures")
    complex_data = {
        "company": {
            "name": "TechCorp",
            "departments": [
                {
                    "name": "Engineering",
                    "employees": [
                        {
                            "id": i,
                            "name": f"Engineer{i}",
                            "projects": [f"Project{j}" for j in range(3)],
                        }
                        for i in range(100)
                    ],
                },
                {
                    "name": "Sales",
                    "employees": [
                        {"id": i + 100, "name": f"Sales{i}", "quota": i * 1000}
                        for i in range(50)
                    ],
                },
            ],
        }
    }

    json_string = json.dumps(complex_data)
    stream = io.StringIO(json_string)

    result = jsonshiatsu.parse(stream)
    eng_dept = result["company"]["departments"][0]
    sales_dept = result["company"]["departments"][1]

    print("✓ Complex structure parsed:")
    print(f"  Company: {result['company']['name']}")
    print(f"  Engineering employees: {len(eng_dept['employees'])}")
    print(f"  Sales employees: {len(sales_dept['employees'])}")

    # Example 7: Streaming with malformed JSON
    print("\n7. Streaming Malformed JSON")
    malformed_data = """
    {
        name: "Unquoted key",
        'single_quotes': 'are fine',
        "trailing_comma": "allowed",
        numbers: [1, 2, 3,],
        "mixed": true,
    }
    """

    stream = io.StringIO(malformed_data)
    result = jsonshiatsu.parse(stream)
    print(f"✓ Malformed JSON streamed: {result}")

    # Example 8: Performance comparison (conceptual)
    print("\n8. Streaming vs Regular Parsing")

    # Create moderately large data
    medium_data = {
        "records": [
            {"id": i, "data": f"data_{i}", "value": i * 1.5} for i in range(5000)
        ]
    }
    json_string = json.dumps(medium_data)

    import time

    # Regular parsing
    start = time.time()
    result1 = jsonshiatsu.parse(json_string)
    regular_time = time.time() - start

    # Streaming parsing
    stream = io.StringIO(json_string)
    start = time.time()
    result2 = jsonshiatsu.parse(stream)
    streaming_time = time.time() - start

    print(f"  Regular parsing time: {regular_time:.4f}s")
    print(f"  Streaming parsing time: {streaming_time:.4f}s")
    print(f"  Results identical: {result1 == result2}")

    print("\n" + "=" * 40)
    print("Streaming demo completed!")


if __name__ == "__main__":
    main()
