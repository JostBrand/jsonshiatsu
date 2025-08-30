"""
Unit tests for data type processing utilities.
"""

import unittest

from jsonshiatsu.core.data_type_processor import DataTypeProcessor


class TestDataTypeProcessor(unittest.TestCase):
    """Test data type processing operations."""

    def test_normalize_boolean_null_python_literals(self) -> None:
        """Test normalizing Python boolean and null literals."""
        input_text = '{"active": True, "inactive": False, "empty": None}'
        expected = '{"active": true, "inactive": false, "empty": null}'
        result = DataTypeProcessor.normalize_boolean_null(input_text)
        self.assertEqual(result, expected)

    def test_normalize_boolean_null_yes_no(self) -> None:
        """Test normalizing yes/no values."""
        input_text = '{"confirm": yes, "deny": NO, "maybe": Yes}'
        expected = '{"confirm": true, "deny": false, "maybe": true}'
        result = DataTypeProcessor.normalize_boolean_null(input_text)
        self.assertEqual(result, expected)

    def test_normalize_boolean_null_undefined(self) -> None:
        """Test normalizing undefined values."""
        input_text = '{"value": undefined, "other": UNDEFINED}'
        expected = '{"value": null, "other": null}'
        result = DataTypeProcessor.normalize_boolean_null(input_text)
        self.assertEqual(result, expected)

    def test_normalize_boolean_null_uppercase_null(self) -> None:
        """Test normalizing uppercase NULL."""
        input_text = '{"data": NULL, "info": null}'
        expected = '{"data": null, "info": null}'
        result = DataTypeProcessor.normalize_boolean_null(input_text)
        self.assertEqual(result, expected)

    def test_normalize_boolean_null_word_boundaries(self) -> None:
        """Test that boolean normalization respects word boundaries."""
        input_text = '{"truename": "value", "falsehood": "test"}'
        result = DataTypeProcessor.normalize_boolean_null(input_text)
        self.assertEqual(result, input_text)  # Should remain unchanged

    def test_normalize_special_numbers_nan_infinity(self) -> None:
        """Test normalizing NaN and Infinity values."""
        input_text = '{"nan": NaN, "inf": Infinity, "neg_inf": -Infinity}'
        expected = '{"nan": "NaN", "inf": "Infinity", "neg_inf": "-Infinity"}'
        result = DataTypeProcessor.normalize_special_numbers(input_text)
        self.assertEqual(result, expected)

    def test_normalize_special_numbers_hexadecimal(self) -> None:
        """Test converting hexadecimal numbers."""
        input_text = '{"hex1": 0x1A, "hex2": 0xFF, "hex3": 0x10}'
        expected = '{"hex1": 26, "hex2": 255, "hex3": 16}'
        result = DataTypeProcessor.normalize_special_numbers(input_text)
        self.assertEqual(result, expected)

    def test_normalize_special_numbers_octal(self) -> None:
        """Test converting octal numbers."""
        input_text = '{"octal1": 025, "octal2": 0755, "not_octal": 089}'
        expected = '{"octal1": 21, "octal2": 493, "not_octal": 089}'
        result = DataTypeProcessor.normalize_special_numbers(input_text)
        self.assertEqual(result, expected)

    def test_normalize_special_numbers_invalid_hex(self) -> None:
        """Test that invalid hex values are left unchanged."""
        input_text = '{"invalid": 0xGHI}'
        result = DataTypeProcessor.normalize_special_numbers(input_text)
        self.assertEqual(result, input_text)

    def test_normalize_special_numbers_preserve_valid_decimals(self) -> None:
        """Test that valid decimal numbers starting with 0 are handled carefully."""
        input_text = '{"decimal": 0.25, "integer": 123}'
        result = DataTypeProcessor.normalize_special_numbers(input_text)
        self.assertEqual(result, input_text)  # Should remain unchanged

    def test_normalize_extended_numbers_version_numbers(self) -> None:
        """Test converting version numbers to strings."""
        input_text = '{"version": 1.2.3.4, "build": 2.1.0.5}'
        expected = '{"version": "1.2.3.4", "build": "2.1.0.5"}'
        result = DataTypeProcessor.normalize_extended_numbers(input_text)
        self.assertEqual(result, expected)

    def test_normalize_extended_numbers_trailing_dots(self) -> None:
        """Test removing trailing dots from numbers."""
        input_text = '{"value1": 42., "value2": 123.}'
        expected = '{"value1": 42, "value2": 123}'
        result = DataTypeProcessor.normalize_extended_numbers(input_text)
        self.assertEqual(result, expected)

    def test_normalize_extended_numbers_plus_prefix(self) -> None:
        """Test removing plus prefixes from numbers."""
        input_text = '{"positive": +123, "negative": -456}'
        expected = '{"positive": 123, "negative": -456}'
        result = DataTypeProcessor.normalize_extended_numbers(input_text)
        self.assertEqual(result, expected)

    def test_normalize_extended_numbers_binary(self) -> None:
        """Test converting binary numbers."""
        input_text = '{"bin1": 0b1010, "bin2": 0b1111}'
        expected = '{"bin1": 10, "bin2": 15}'
        result = DataTypeProcessor.normalize_extended_numbers(input_text)
        self.assertEqual(result, expected)

    def test_normalize_extended_numbers_octal_o_prefix(self) -> None:
        """Test converting octal numbers with 0o prefix."""
        input_text = '{"octal1": 0o755, "octal2": 0o644}'
        expected = '{"octal1": 493, "octal2": 420}'
        result = DataTypeProcessor.normalize_extended_numbers(input_text)
        self.assertEqual(result, expected)

    def test_normalize_extended_numbers_incomplete_scientific(self) -> None:
        """Test fixing incomplete scientific notation."""
        input_text = '{"sci1": 1.5e, "sci2": 2.3e}'
        expected = '{"sci1": 1.5e0, "sci2": 2.3e0}'
        result = DataTypeProcessor.normalize_extended_numbers(input_text)
        self.assertEqual(result, expected)

    def test_normalize_extended_numbers_invalid_formats(self) -> None:
        """Test that invalid number formats are handled gracefully."""
        input_text = '{"invalid_bin": 0b123, "invalid_oct": 0o999}'
        result = DataTypeProcessor.normalize_extended_numbers(input_text)
        # Binary 0b123 -> regex matches "1" part, converts to 1, leaves "23": "123"
        # Octal 0o999 -> all digits invalid, stays unchanged
        self.assertIn("123", result)  # 0b1 -> 1, + remaining "23" = "123"
        self.assertIn("0o999", result)  # Invalid octal stays unchanged

    def test_handle_empty_values_object_commas(self) -> None:
        """Test handling empty values after commas in objects."""
        input_text = '{"key1": "value1", "key2": , "key3": "value3"}'
        expected = '{"key1": "value1", "key2": null, "key3": "value3"}'
        result = DataTypeProcessor.handle_empty_values(input_text)
        self.assertEqual(result, expected)

    def test_handle_empty_values_array_commas(self) -> None:
        """Test handling empty values in arrays."""
        input_text = "[1, 2, , 4, , 6]"
        expected = "[1, 2, null, 4, null, 6]"
        result = DataTypeProcessor.handle_empty_values(input_text)
        self.assertEqual(result, expected)

    def test_handle_empty_values_incomplete_structures(self) -> None:
        """Test handling incomplete object and array values."""
        input_text = '{"key": } and [1, 2, ]'
        expected = '{"key": null} and [1, 2, ]'  # Array trailing comma not handled by this regex
        result = DataTypeProcessor.handle_empty_values(input_text)
        self.assertEqual(result, expected)

    def test_handle_empty_values_multiline(self) -> None:
        """Test handling empty values with newlines."""
        input_text = '{"key": \n }'
        expected = '{"key": null}'  # Newline and whitespace are consumed by regex
        result = DataTypeProcessor.handle_empty_values(input_text)
        self.assertEqual(result, expected)

    def test_handle_empty_values_empty_key(self) -> None:
        """Test handling empty key with empty value."""
        input_text = '{"": , "other": "value"}'
        expected = '{"": null, "other": "value"}'
        result = DataTypeProcessor.handle_empty_values(input_text)
        self.assertEqual(result, expected)

    def test_handle_empty_values_no_changes_needed(self) -> None:
        """Test that well-formed JSON is not changed."""
        input_text = '{"key": "value", "array": [1, 2, 3]}'
        result = DataTypeProcessor.handle_empty_values(input_text)
        self.assertEqual(result, input_text)

    def test_integration_all_processors(self) -> None:
        """Test integration of all data type processing methods."""
        input_text = '{"active": True, "version": 1.2.3.4, "count": 0x10, "empty": , "special": NaN}'

        # Apply all processors in sequence
        result = DataTypeProcessor.normalize_boolean_null(input_text)
        result = DataTypeProcessor.normalize_special_numbers(result)
        result = DataTypeProcessor.normalize_extended_numbers(result)
        result = DataTypeProcessor.handle_empty_values(result)

        # Verify all transformations worked
        self.assertIn('"active": true', result)  # Boolean normalized
        self.assertIn('"version": "1.2.3.4"', result)  # Version string
        self.assertIn('"count": 16', result)  # Hex converted
        self.assertIn('"empty": null', result)  # Empty filled
        self.assertIn('"special": "NaN"', result)  # Special number handled

    def test_edge_cases_empty_input(self) -> None:
        """Test handling of empty input."""
        empty_input = ""

        result = DataTypeProcessor.normalize_boolean_null(empty_input)
        self.assertEqual(result, empty_input)

        result = DataTypeProcessor.normalize_special_numbers(empty_input)
        self.assertEqual(result, empty_input)

        result = DataTypeProcessor.normalize_extended_numbers(empty_input)
        self.assertEqual(result, empty_input)

        result = DataTypeProcessor.handle_empty_values(empty_input)
        self.assertEqual(result, empty_input)

    def test_preserve_valid_json(self) -> None:
        """Test that valid JSON is preserved through all processing."""
        valid_json = '{"valid": "json", "number": 123, "boolean": true, "null": null}'

        # Run through all processors
        result = DataTypeProcessor.normalize_boolean_null(valid_json)
        result = DataTypeProcessor.normalize_special_numbers(result)
        result = DataTypeProcessor.normalize_extended_numbers(result)
        result = DataTypeProcessor.handle_empty_values(result)

        # Should remain unchanged
        self.assertEqual(result, valid_json)

    def test_complex_nested_structures(self) -> None:
        """Test processing of complex nested structures."""
        input_text = """
        {
            "config": {
                "enabled": True,
                "timeout": 0x1E,
                "version": 2.1.0.3,
                "features": [
                    "feature1",
                    ,
                    "feature3"
                ],
                "limits": {
                    "max": +1000,
                    "special": NaN,
                    "empty":
                }
            }
        }
        """

        # Apply all processors
        result = DataTypeProcessor.normalize_boolean_null(input_text)
        result = DataTypeProcessor.normalize_special_numbers(result)
        result = DataTypeProcessor.normalize_extended_numbers(result)
        result = DataTypeProcessor.handle_empty_values(result)

        # Verify transformations in nested structure
        self.assertIn('"enabled": true', result)
        self.assertIn('"timeout": 30', result)  # 0x1E = 30
        self.assertIn('"version": "2.1.0.3"', result)
        self.assertIn("null", result)  # Empty values filled
        self.assertIn('"max": 1000', result)  # Plus prefix removed
        self.assertIn('"special": "NaN"', result)  # NaN quoted


if __name__ == "__main__":
    unittest.main()
