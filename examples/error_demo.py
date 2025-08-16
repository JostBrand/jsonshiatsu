"""
Enhanced error reporting demonstration for jsonshiatsu.
"""

import jsonshiatsu
from jsonshiatsu import ParseConfig, ParseError


def main():
    print("jsonshiatsu - Enhanced Error Reporting Demo")
    print("=" * 45)
    
    # Example 1: Basic error with position
    print("\n1. Error with Position Information")
    config = ParseConfig(include_position=True, fallback=False)
    
    try:
        # Missing value after colon
        jsonshiatsu.parse('{"key": }', config=config)
    except ParseError as e:
        print("Error caught:")
        print(str(e))
    
    # Example 2: Error with context
    print("\n2. Error with Context")
    config = ParseConfig(include_context=True, fallback=False)
    
    try:
        # Missing colon
        jsonshiatsu.parse('{"key" "value"}', config=config)
    except ParseError as e:
        print("Error caught:")
        print(str(e))
    
    # Example 3: Error with suggestions
    print("\n3. Error with Helpful Suggestions")
    config = ParseConfig(include_position=True, include_context=True, fallback=False)
    
    try:
        # Unclosed object
        jsonshiatsu.parse('{"key": "value"', config=config)
    except ParseError as e:
        print("Error caught:")
        print(str(e))
    
    # Example 4: Multiline JSON error
    print("\n4. Multiline JSON Error")
    multiline_json = '''
    {
        "name": "John Doe",
        "age": 30,
        "city": "New York",
        "invalid": 
    }
    '''
    
    try:
        jsonshiatsu.parse(multiline_json, config=config)
    except ParseError as e:
        print("Error caught:")
        print(str(e))
    
    # Example 5: Error in nested structure
    print("\n5. Error in Nested Structure")
    nested_json = '''
    {
        "user": {
            "profile": {
                "name": "Alice",
                "settings": {
                    "theme": dark,
                    "notifications": true
                }
            }
        }
    }
    '''
    
    try:
        jsonshiatsu.parse(nested_json, config=config)
    except ParseError as e:
        print("Error caught:")
        print(str(e))
    
    # Example 6: Array syntax error
    print("\n6. Array Syntax Error")
    array_json = '["item1", "item2", "item3",, "item4"]'  # Extra comma
    
    try:
        jsonshiatsu.parse(array_json, config=config)
    except ParseError as e:
        print("Error caught:")
        print(str(e))
    
    # Example 7: Demonstrating different error contexts
    print("\n7. Different Error Context Sizes")
    
    # Large context
    config_large = ParseConfig(
        include_context=True, 
        max_error_context=100, 
        fallback=False
    )
    
    # Small context
    config_small = ParseConfig(
        include_context=True, 
        max_error_context=10, 
        fallback=False
    )
    
    error_json = 'This is a very long prefix that contains lots of text before the actual JSON starts {"key": invalid_value} and then some suffix text'
    
    print("\nLarge context (100 chars):")
    try:
        jsonshiatsu.parse(error_json, config=config_large)
    except ParseError as e:
        # Show just the surrounding text part
        error_str = str(e)
        if "Surrounding text:" in error_str:
            context_part = error_str.split("Surrounding text:")[1].split("\n")[1]
            print(f"Context: {context_part}")
    
    print("\nSmall context (10 chars):")
    try:
        jsonshiatsu.parse(error_json, config=config_small)
    except ParseError as e:
        # Show just the surrounding text part
        error_str = str(e)
        if "Surrounding text:" in error_str:
            context_part = error_str.split("Surrounding text:")[1].split("\n")[1]
            print(f"Context: {context_part}")
    
    # Example 8: Disabled error reporting
    print("\n8. Minimal Error Reporting")
    config_minimal = ParseConfig(
        include_position=False,
        include_context=False,
        fallback=False
    )
    
    try:
        jsonshiatsu.parse('{"broken": }', config=config_minimal)
    except ParseError as e:
        print("Minimal error:")
        print(str(e))
    
    print("\n" + "=" * 45)
    print("Error reporting demo completed!")


if __name__ == "__main__":
    main()