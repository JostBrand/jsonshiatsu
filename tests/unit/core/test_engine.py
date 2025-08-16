"""
Test cases for the jsonshiatsu parser.
"""

import unittest
from jsonshiatsu import parse
from jsonshiatsu.security.exceptions import ParseError


class TestParser(unittest.TestCase):

    def test_standard_json(self):
        # Test that standard JSON still works
        result = parse('{"test": "value"}')
        self.assertEqual(result, {"test": "value"})

        result = parse("[1, 2, 3]")
        self.assertEqual(result, [1, 2, 3])

    def test_unquoted_keys(self):
        # Unquoted object keys should work
        result = parse('{test: "value"}')
        self.assertEqual(result, {"test": "value"})

        result = parse('{key1: "value1", key2: "value2"}')
        self.assertEqual(result, {"key1": "value1", "key2": "value2"})

    def test_single_quotes(self):
        # Single quoted strings should work
        result = parse("{'test': 'value'}")
        self.assertEqual(result, {"test": "value"})

        result = parse("{test: 'value'}")
        self.assertEqual(result, {"test": "value"})

    def test_mixed_quotes(self):
        # Mix of single and double quotes
        result = parse("{\"test\": 'value'}")
        self.assertEqual(result, {"test": "value"})

        result = parse("{'test': \"value\"}")
        self.assertEqual(result, {"test": "value"})

    def test_unquoted_values(self):
        # Unquoted string values (treated as identifiers)
        result = parse("{test: value}")
        self.assertEqual(result, {"test": "value"})

    def test_trailing_commas(self):
        # Trailing commas should be handled
        result = parse('{"test": "value",}')
        self.assertEqual(result, {"test": "value"})

        result = parse("[1, 2, 3,]")
        self.assertEqual(result, [1, 2, 3, None])

    def test_numbers(self):
        # Various number formats
        result = parse('{"int": 123}')
        self.assertEqual(result, {"int": 123})

        result = parse('{"float": 123.45}')
        self.assertEqual(result, {"float": 123.45})

        result = parse('{"negative": -123}')
        self.assertEqual(result, {"negative": -123})

        result = parse('{"scientific": 1.23e-4}')
        self.assertEqual(result, {"scientific": 1.23e-4})

    def test_boolean_and_null(self):
        result = parse('{"bool_true": true, "bool_false": false, "null_val": null}')
        expected = {"bool_true": True, "bool_false": False, "null_val": None}
        self.assertEqual(result, expected)

    def test_nested_structures(self):
        # Nested objects and arrays
        result = parse('{obj: {nested: "value"}, arr: [1, 2, {inner: "test"}]}')
        expected = {"obj": {"nested": "value"}, "arr": [1, 2, {"inner": "test"}]}
        self.assertEqual(result, expected)

    def test_strings_with_embedded_quotes(self):
        # Strings with escaped quotes
        result = parse('{"test": "He said \\"Hello\\""}')
        self.assertEqual(result, {"test": 'He said "Hello"'})

        result = parse("{'test': 'She said \\'Hi\\''}")
        self.assertEqual(result, {"test": "She said 'Hi'"})

    def test_strings_with_newlines(self):
        # Strings with escape sequences
        result = parse('{"test": "line1\\nline2"}')
        self.assertEqual(result, {"test": "line1\nline2"})

    def test_empty_structures(self):
        # Empty objects and arrays
        result = parse("{}")
        self.assertEqual(result, {})

        result = parse("[]")
        self.assertEqual(result, [])

        result = parse("{empty_obj: {}, empty_arr: []}")
        self.assertEqual(result, {"empty_obj": {}, "empty_arr": []})

    def test_whitespace_tolerance(self):
        # Various whitespace scenarios
        result = parse('  {  test  :  "value"  }  ')
        self.assertEqual(result, {"test": "value"})

        result = parse('{\n  test: "value"\n}')
        self.assertEqual(result, {"test": "value"})

    def test_duplicate_keys_default(self):
        # By default, duplicate keys should overwrite
        result = parse('{"test": "value1", "test": "value2"}')
        self.assertEqual(result, {"test": "value2"})

    def test_duplicate_keys_array_mode(self):
        # With duplicate_keys=True, should create arrays
        result = parse('{"test": "value1", "test": "value2"}', duplicate_keys=True)
        self.assertEqual(result, {"test": ["value1", "value2"]})

    def test_real_world_examples(self):
        # Real-world malformed JSON examples
        result = parse('{ test: "this is a test"}')
        self.assertEqual(result, {"test": "this is a test"})

        # More complex real-world example
        malformed_json = """{
            name: 'John Doe',
            age: 30,
            city: "New York",
            hobbies: ['reading', "swimming", coding],
            active: true,
            score: null,
        }"""

        expected = {
            "name": "John Doe",
            "age": 30,
            "city": "New York",
            "hobbies": ["reading", "swimming", "coding"],
            "active": True,
            "score": None,
        }

        result = parse(malformed_json)
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
