"""
Security features demonstration for jsonshiatsu.
"""

import jsonshiatsu
from jsonshiatsu import ParseConfig, ParseLimits, SecurityError


def main():
    print("jsonshiatsu - Security Features Demo")
    print("=" * 40)
    
    # Example 1: Basic security limits
    print("\n1. Input Size Limits")
    config = ParseConfig(limits=ParseLimits(max_input_size=100))
    
    try:
        # This should work
        result = jsonshiatsu.parse('{"test": "value"}', config=config)
        print(f"✓ Small input parsed: {result}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    try:
        # This should fail
        large_input = '{"test": "' + 'x' * 200 + '"}'
        result = jsonshiatsu.parse(large_input, config=config)
        print(f"✗ Large input should have failed: {result}")
    except SecurityError as e:
        print(f"✓ Large input blocked: {type(e).__name__}")
    
    # Example 2: String length limits
    print("\n2. String Length Limits")
    config = ParseConfig(limits=ParseLimits(max_string_length=20))
    
    try:
        result = jsonshiatsu.parse('{"name": "John"}', config=config)
        print(f"✓ Short string parsed: {result}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    try:
        long_string = '{"name": "' + 'x' * 50 + '"}'
        result = jsonshiatsu.parse(long_string, config=config)
        print(f"✗ Long string should have failed: {result}")
    except SecurityError as e:
        print(f"✓ Long string blocked: {type(e).__name__}")
    
    # Example 3: Nesting depth limits
    print("\n3. Nesting Depth Limits")
    config = ParseConfig(limits=ParseLimits(max_nesting_depth=3))
    
    try:
        shallow = '{"a": {"b": {"c": "value"}}}'
        result = jsonshiatsu.parse(shallow, config=config)
        print(f"✓ Shallow nesting parsed: {result}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    try:
        deep = '{"a": {"b": {"c": {"d": {"e": "value"}}}}}'
        result = jsonshiatsu.parse(deep, config=config)
        print(f"✗ Deep nesting should have failed: {result}")
    except SecurityError as e:
        print(f"✓ Deep nesting blocked: {type(e).__name__}")
    
    # Example 4: Object size limits
    print("\n4. Object Size Limits")
    config = ParseConfig(limits=ParseLimits(max_object_keys=3))
    
    try:
        small_obj = '{"a": 1, "b": 2, "c": 3}'
        result = jsonshiatsu.parse(small_obj, config=config)
        print(f"✓ Small object parsed: {result}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    try:
        large_obj = '{' + ', '.join(f'"{i}": {i}' for i in range(10)) + '}'
        result = jsonshiatsu.parse(large_obj, config=config)
        print(f"✗ Large object should have failed")
    except SecurityError as e:
        print(f"✓ Large object blocked: {type(e).__name__}")
    
    # Example 5: Array size limits
    print("\n5. Array Size Limits")
    config = ParseConfig(limits=ParseLimits(max_array_items=5))
    
    try:
        small_array = '[1, 2, 3, 4, 5]'
        result = jsonshiatsu.parse(small_array, config=config)
        print(f"✓ Small array parsed: {result}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    try:
        large_array = '[' + ', '.join(str(i) for i in range(10)) + ']'
        result = jsonshiatsu.parse(large_array, config=config)
        print(f"✗ Large array should have failed")
    except SecurityError as e:
        print(f"✓ Large array blocked: {type(e).__name__}")
    
    # Example 6: Custom limits for production use
    print("\n6. Production Security Configuration")
    production_config = ParseConfig(
        limits=ParseLimits(
            max_input_size=1024 * 1024,      # 1MB max input
            max_string_length=10000,         # 10KB max string
            max_nesting_depth=20,            # Reasonable nesting
            max_object_keys=1000,            # Max 1000 keys per object
            max_array_items=10000,           # Max 10K array items
            max_total_items=100000           # Max 100K total items
        ),
        fallback=False,                      # Don't fall back to unsafe parsing
        aggressive=False                     # Conservative preprocessing
    )
    
    try:
        safe_json = '''
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
        '''
        result = jsonshiatsu.parse(safe_json, config=production_config)
        print(f"✓ Production-safe JSON parsed successfully")
        print(f"  Status: {result['api_response']['status']}")
        print(f"  Data count: {len(result['api_response']['data'])}")
    except Exception as e:
        print(f"✗ Production config error: {e}")


if __name__ == "__main__":
    main()