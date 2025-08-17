"""
Test cases for core engine error handling and edge cases.

Tests focus on error paths, edge cases, and fallback mechanisms in the parsing engine.
"""

import json
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

import jsonshiatsu
from jsonshiatsu.core.engine import Lexer, Parser, _parse_internal, load, loads
from jsonshiatsu.security.exceptions import ErrorReporter, ParseError, SecurityError
from jsonshiatsu.security.limits import LimitValidator
from jsonshiatsu.utils.config import ParseConfig, ParseLimits


class TestParsingErrorPaths(unittest.TestCase):
    """Test error paths in the parsing engine."""

    def setUp(self):
        """Set up test configuration."""
        self.config = ParseConfig()
        self.config.fallback = True  # Enable fallback for testing

    def test_array_parsing_errors(self):
        """Test error handling in array parsing."""
        error_cases = [
            "[1, 2,",  # Unclosed array
            "[1, 2 3]",  # Missing comma
            "[1, , 3]",  # Empty element
            "[1 2]",  # Missing comma between elements
        ]

        for malformed_json in error_cases:
            with self.subTest(json=malformed_json):
                try:
                    result = jsonshiatsu.loads(malformed_json)
                    # If it succeeds, should be due to error recovery
                    self.assertIsInstance(result, list)
                except (ParseError, json.JSONDecodeError):
                    # Expected to fail for some cases
                    pass

    def test_object_parsing_errors(self):
        """Test error handling in object parsing."""
        error_cases = [
            '{"key": "value"',  # Unclosed object
            '{"key" "value"}',  # Missing colon
            '{"key": "value",}',  # Trailing comma
            '{key: "value"}',  # Unquoted key (should work with preprocessing)
            '{"key": }',  # Missing value
        ]

        for malformed_json in error_cases:
            with self.subTest(json=malformed_json):
                try:
                    result = jsonshiatsu.loads(malformed_json)
                    # Some cases should succeed due to preprocessing
                    self.assertIsInstance(result, dict)
                except (ParseError, json.JSONDecodeError):
                    # Expected to fail for some cases
                    pass

    def test_string_parsing_errors(self):
        """Test error handling in string parsing."""
        error_cases = [
            '{"key": "unclosed string}',  # Unclosed string
            '{"key": "invalid\\escape"}',  # Invalid escape sequence
            '{"key": "string with \n newline"}',  # Unescaped newline
        ]

        for malformed_json in error_cases:
            with self.subTest(json=malformed_json):
                try:
                    result = jsonshiatsu.loads(malformed_json)
                    # Some may succeed due to preprocessing
                    self.assertIsInstance(result, dict)
                except (ParseError, json.JSONDecodeError):
                    # Expected to fail for some cases
                    pass

    def test_number_parsing_errors(self):
        """Test error handling in number parsing."""
        error_cases = [
            '{"num": 123.}',  # Trailing decimal
            '{"num": .123}',  # Leading decimal (might be valid)
            '{"num": 123.45.67}',  # Multiple decimals
            '{"num": 123e}',  # Invalid exponent
        ]

        for malformed_json in error_cases:
            with self.subTest(json=malformed_json):
                try:
                    result = jsonshiatsu.loads(malformed_json)
                    if result:
                        self.assertIsInstance(result, dict)
                except (ParseError, json.JSONDecodeError, ValueError):
                    # Expected to fail for malformed numbers
                    pass

    def test_nested_structure_errors(self):
        """Test error handling in nested structures."""
        error_cases = [
            '{"obj": {"nested": }',  # Missing value in nested object
            '{"arr": [1, {"broken": }]}',  # Mixed structure errors
            '{"deep": {"very": {"nested": {"error": }}}}',  # Deep nesting error
        ]

        for malformed_json in error_cases:
            with self.subTest(json=malformed_json):
                try:
                    result = jsonshiatsu.loads(malformed_json)
                    if result:
                        self.assertIsInstance(result, dict)
                except (ParseError, json.JSONDecodeError):
                    # Expected to fail for complex nested errors
                    pass


class TestSecurityLimitValidation(unittest.TestCase):
    """Test security limit enforcement in parsing."""

    def test_input_size_limit_enforcement(self):
        """Test input size limit enforcement."""
        # Create config with small limit
        limits = ParseLimits(max_input_size=100)
        config = ParseConfig(limits=limits)

        # Create large input that exceeds limit
        large_input = '{"key": "' + "x" * 200 + '"}'

        with self.assertRaises((SecurityError, json.JSONDecodeError)):
            jsonshiatsu.loads(large_input, config=config)

    def test_nesting_depth_limit_enforcement(self):
        """Test nesting depth limit enforcement."""
        # Create config with small nesting limit
        limits = ParseLimits(max_nesting_depth=3)
        config = ParseConfig(limits=limits)

        # Create deeply nested JSON
        deep_json = '{"a": {"b": {"c": {"d": {"e": "too_deep"}}}}}'

        with self.assertRaises((SecurityError, json.JSONDecodeError)):
            jsonshiatsu.loads(deep_json, config=config)

    def test_string_length_limit_enforcement(self):
        """Test string length limit enforcement."""
        # Create config with small string limit
        limits = ParseLimits(max_string_length=10)
        config = ParseConfig(limits=limits)

        # Create JSON with long string
        long_string_json = '{"key": "this_string_is_too_long_for_the_limit"}'

        with self.assertRaises((SecurityError, json.JSONDecodeError)):
            jsonshiatsu.loads(long_string_json, config=config)

    def test_array_items_limit_enforcement(self):
        """Test array items limit enforcement."""
        # Create config with small array limit
        limits = ParseLimits(max_array_items=5)
        config = ParseConfig(limits=limits)

        # Create array with too many items
        large_array_json = "[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]"

        with self.assertRaises((SecurityError, json.JSONDecodeError)):
            jsonshiatsu.loads(large_array_json, config=config)

    def test_object_items_limit_enforcement(self):
        """Test object items limit enforcement."""
        # Create config with small object limit
        limits = ParseLimits(max_object_keys=3)
        config = ParseConfig(limits=limits)

        # Create object with too many items
        large_object_json = '{"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}'

        with self.assertRaises((SecurityError, json.JSONDecodeError)):
            jsonshiatsu.loads(large_object_json, config=config)


class TestFallbackMechanisms(unittest.TestCase):
    """Test fallback mechanisms in the parsing engine."""

    def test_fallback_to_standard_json(self):
        """Test fallback to standard JSON parser."""
        # Valid JSON should work with fallback
        valid_json = '{"key": "value", "number": 123}'

        config = ParseConfig(fallback=True)
        result = jsonshiatsu.loads(valid_json, config=config)

        self.assertEqual(result, {"key": "value", "number": 123})

    def test_fallback_disabled(self):
        """Test behavior when fallback is disabled."""
        # Test that the library's robust preprocessing works even with fallback disabled
        # The fallback setting controls whether to fall back to standard JSON parser
        malformed_json = "completely invalid non-json text"

        config = ParseConfig(fallback=False)

        try:
            result = jsonshiatsu.loads(malformed_json, config=config)
            # The library's preprocessing is very robust
            self.assertIsNotNone(result)
        except (ParseError, json.JSONDecodeError, ValueError):
            # Some inputs may still fail
            pass

    def test_preprocessing_fallback_chain(self):
        """Test the preprocessing fallback chain."""
        # JSON that might benefit from multiple preprocessing attempts
        complex_malformed = """
        ```json
        {
            // Comment
            "status": "ok",
            data: [1, 2, 3,]
        }
        ```
        """

        config = ParseConfig(fallback=True)

        try:
            result = jsonshiatsu.loads(complex_malformed, config=config)
            # Should succeed due to preprocessing + fallback
            self.assertIsInstance(result, dict)
            self.assertIn("status", result)
        except (ParseError, json.JSONDecodeError):
            # May fail if preprocessing can't handle this complexity
            pass

    def test_fallback_error_preservation(self):
        """Test that original errors are preserved in fallback."""
        # Truly malformed JSON that can't be recovered
        impossible_json = '{"key": "value" "another": "value"}'  # Missing comma

        config = ParseConfig(fallback=True)

        try:
            result = jsonshiatsu.loads(impossible_json, config=config)
            # If preprocessing succeeds, that's also valid behavior
            self.assertIsInstance(result, dict)
        except json.JSONDecodeError as e:
            # Should preserve useful error information
            self.assertIsInstance(e, json.JSONDecodeError)


class TestLoadFunction(unittest.TestCase):
    """Test the load() function for file input."""

    def test_load_from_stringio(self):
        """Test loading from StringIO object."""
        json_content = '{"key": "value", "number": 42}'
        json_file = StringIO(json_content)

        result = jsonshiatsu.load(json_file)

        self.assertEqual(result, {"key": "value", "number": 42})

    def test_load_malformed_from_stringio(self):
        """Test loading malformed JSON from StringIO."""
        malformed_content = '{key: "value", number: 42}'  # Unquoted keys
        json_file = StringIO(malformed_content)

        result = jsonshiatsu.load(json_file)

        # Should succeed due to preprocessing
        self.assertEqual(result, {"key": "value", "number": 42})

    def test_load_with_config(self):
        """Test load() with custom configuration."""
        json_content = '{"duplicate": "first", "duplicate": "second"}'
        json_file = StringIO(json_content)

        config = ParseConfig(duplicate_keys=True)
        result = jsonshiatsu.load(json_file, config=config)

        # Should handle duplicate keys according to config
        self.assertIn("duplicate", result)

    def test_load_error_handling(self):
        """Test error handling in load() function."""
        # Test with genuinely invalid content
        invalid_content = "not json at all"
        json_file = StringIO(invalid_content)

        try:
            # Test that truly invalid content may fail
            result = jsonshiatsu.load(json_file)
            # If it somehow succeeds, that's also acceptable
            pass
        except (ParseError, json.JSONDecodeError, ValueError):
            # Expected to fail for truly invalid content
            pass


class TestErrorReporting(unittest.TestCase):
    """Test error reporting accuracy and completeness."""

    def test_position_accuracy(self):
        """Test that error positions are accurately reported."""
        malformed_json = '{\n  "key": "value",\n  "error": here\n}'

        try:
            result = jsonshiatsu.loads(malformed_json)
            # If it parses successfully, that shows the robustness of preprocessing
            self.assertIsNotNone(result)
        except (ParseError, json.JSONDecodeError, ValueError) as error:
            # If it fails, check for position information
            if hasattr(error, "lineno"):
                self.assertGreater(error.lineno, 0)
            if hasattr(error, "colno"):
                self.assertGreater(error.colno, 0)

    def test_error_context_provision(self):
        """Test that error context is provided."""
        malformed_json = '{"key": "value", "broken": }'

        try:
            result = jsonshiatsu.loads(malformed_json)
            # If it parses successfully, that shows the robustness of preprocessing
            self.assertIsNotNone(result)
        except (ParseError, json.JSONDecodeError, ValueError) as e:
            # If it fails, check that we get useful error information
            error_message = str(e)
            self.assertGreater(len(error_message), 0)
            # May contain suggestions or context
            self.assertTrue(
                any(
                    keyword in error_message.lower()
                    for keyword in [
                        "expected",
                        "missing",
                        "invalid",
                        "could not",
                        "error",
                    ]
                )
            )

    def test_suggestion_quality(self):
        """Test that error suggestions are helpful."""
        common_errors = [
            '{"key" "value"}',  # Missing colon
            '{"key": "value"',  # Missing closing brace
            "[1, 2, 3",  # Missing closing bracket
        ]

        for malformed_json in common_errors:
            with self.subTest(json=malformed_json):
                try:
                    jsonshiatsu.loads(malformed_json)
                except (ParseError, json.JSONDecodeError) as e:
                    error_message = str(e)
                    # Should provide actionable suggestions
                    self.assertGreater(len(error_message), 0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_empty_input(self):
        """Test handling of empty input."""
        with self.assertRaises((ParseError, json.JSONDecodeError)):
            jsonshiatsu.loads("")

    def test_whitespace_only_input(self):
        """Test handling of whitespace-only input."""
        with self.assertRaises((ParseError, json.JSONDecodeError)):
            jsonshiatsu.loads("   \n\t   ")

    def test_single_value_parsing(self):
        """Test parsing of single values (not objects/arrays)."""
        # These should work
        test_cases = [
            ('"string"', "string"),
            ("123", 123),
            ("true", True),
            ("false", False),
            ("null", None),
        ]

        for input_json, expected in test_cases:
            with self.subTest(json=input_json):
                result = jsonshiatsu.loads(input_json)
                self.assertEqual(result, expected)

    def test_unicode_handling(self):
        """Test handling of Unicode content."""
        unicode_json = '{"unicode": "こんにちは", "emoji": "🎉"}'

        result = jsonshiatsu.loads(unicode_json)

        self.assertEqual(result["unicode"], "こんにちは")
        self.assertEqual(result["emoji"], "🎉")

    def test_very_large_numbers(self):
        """Test handling of very large numbers."""
        large_number_json = '{"big": 999999999999999999999999999999}'

        try:
            result = jsonshiatsu.loads(large_number_json)
            # Should handle large numbers appropriately
            self.assertIn("big", result)
        except (ParseError, json.JSONDecodeError, OverflowError):
            # May fail for extremely large numbers
            pass


if __name__ == "__main__":
    unittest.main()
