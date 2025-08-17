"""
Test cases for the jsonshiatsu core engine functionality.

Tests focus on parsing logic, not preprocessing (which is covered in transformer tests).
"""

import unittest

import jsonshiatsu
from jsonshiatsu.core.engine import Lexer, Parser
from jsonshiatsu.security.exceptions import ErrorReporter, ParseError
from jsonshiatsu.utils.config import ParseConfig


class TestParserCore(unittest.TestCase):
    """Test core parser functionality with minimal preprocessing."""

    def setUp(self):
        """Set up with minimal preprocessing config for pure parsing tests."""
        self.config = ParseConfig()
        self.config.preprocessing_config = None  # Disable preprocessing for unit tests

    def _parse_tokens(self, json_str):
        """Helper to parse tokens directly for parser testing."""
        lexer = Lexer(json_str)
        tokens = lexer.get_all_tokens()
        error_reporter = ErrorReporter(json_str)  # ErrorReporter needs text
        parser = Parser(tokens, self.config, error_reporter)
        return parser.parse()

    def test_basic_object_parsing(self):
        """Test parsing of basic objects."""
        result = self._parse_tokens('{"key": "value"}')
        self.assertEqual(result, {"key": "value"})

        result = self._parse_tokens('{"a": 1, "b": 2}')
        self.assertEqual(result, {"a": 1, "b": 2})

    def test_basic_array_parsing(self):
        """Test parsing of basic arrays."""
        result = self._parse_tokens("[1, 2, 3]")
        self.assertEqual(result, [1, 2, 3])

        result = self._parse_tokens('["a", "b", "c"]')
        self.assertEqual(result, ["a", "b", "c"])

    def test_number_parsing(self):
        """Test number parsing accuracy."""
        result = self._parse_tokens('{"int": 123, "float": 45.67, "neg": -89}')
        self.assertEqual(result["int"], 123)
        self.assertEqual(result["float"], 45.67)
        self.assertEqual(result["neg"], -89)

    def test_boolean_null_parsing(self):
        """Test boolean and null value parsing."""
        result = self._parse_tokens('{"t": true, "f": false, "n": null}')
        self.assertEqual(result, {"t": True, "f": False, "n": None})

    def test_nested_structure_parsing(self):
        """Test parsing of nested structures."""
        json_str = '{"obj": {"nested": "value"}, "arr": [1, {"inner": 2}]}'
        result = self._parse_tokens(json_str)
        expected = {"obj": {"nested": "value"}, "arr": [1, {"inner": 2}]}
        self.assertEqual(result, expected)

    def test_string_escape_handling(self):
        """Test proper handling of escaped strings."""
        result = self._parse_tokens('{"escaped": "line1\\nline2"}')
        self.assertEqual(result["escaped"], "line1\nline2")

    def test_error_reporting(self):
        """Test that parser provides useful error messages."""
        with self.assertRaises(ParseError) as cm:
            self._parse_tokens('{"key" "value"}')  # Missing colon

        error = cm.exception
        self.assertIn("Expected ':'", str(error))
        self.assertTrue(hasattr(error, "position"))


class TestEngineIntegration(unittest.TestCase):
    """Test the full engine with preprocessing integration."""

    def test_malformed_to_valid_conversion(self):
        """Test that malformed JSON gets converted to valid structures."""
        # Unquoted keys
        result = jsonshiatsu.loads('{test: "value"}')
        self.assertEqual(result, {"test": "value"})

        # Single quotes
        result = jsonshiatsu.loads("{'key': 'value'}")
        self.assertEqual(result, {"key": "value"})

        # Trailing commas
        result = jsonshiatsu.loads('{"key": "value",}')
        self.assertEqual(result, {"key": "value"})

    def test_duplicate_key_handling(self):
        """Test duplicate key handling strategies."""
        # Default behavior - last value wins
        result = jsonshiatsu.loads('{"key": "first", "key": "second"}')
        self.assertEqual(result, {"key": "second"})

    def test_error_recovery(self):
        """Test error recovery mechanisms."""
        # This should either succeed with recovery or fail gracefully
        try:
            result = jsonshiatsu.loads('{"valid": "data", "broken": }')
            # If it succeeds, should have some valid data
            self.assertIn("valid", result)
        except Exception as e:
            # If it fails, should be a proper JSONDecodeError
            self.assertIn("JSON", str(type(e)))

    def test_compatibility_with_standard_json(self):
        """Test that valid JSON still works perfectly."""
        valid_json = (
            '{"standard": "json", "array": [1, 2, 3], "nested": {"works": true}}'
        )
        result = jsonshiatsu.loads(valid_json)
        expected = {"standard": "json", "array": [1, 2, 3], "nested": {"works": True}}
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
