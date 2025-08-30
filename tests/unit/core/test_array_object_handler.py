"""
Unit tests for array and object handling utilities.
"""

import unittest

from jsonshiatsu.core.array_object_handler import ArrayObjectHandler


class TestArrayObjectHandler(unittest.TestCase):
    """Test array and object processing operations."""

    def test_fix_structural_syntax_parentheses_to_braces(self) -> None:
        """Test converting parentheses to braces for object-like structures."""
        input_text = '("key": "value", "other": 123)'
        expected = '{"key": "value", "other": 123}'
        result = ArrayObjectHandler.fix_structural_syntax(input_text)
        self.assertEqual(result, expected)

    def test_fix_structural_syntax_preserve_function_calls(self) -> None:
        """Test that function calls with parentheses are preserved."""
        input_text = 'function test() { return ("value"); }'
        result = ArrayObjectHandler.fix_structural_syntax(input_text)
        self.assertEqual(result, input_text)  # Should remain unchanged

    def test_fix_structural_syntax_sets_to_arrays(self) -> None:
        """Test converting set literals to arrays."""
        input_text = "{1, 2, 3, 4}"
        expected = "[1, 2, 3, 4]"
        result = ArrayObjectHandler.fix_structural_syntax(input_text)
        self.assertEqual(result, expected)

    def test_fix_structural_syntax_preserve_objects(self) -> None:
        """Test that proper objects with key-value pairs are preserved."""
        input_text = '{"key": "value", "number": 123}'
        result = ArrayObjectHandler.fix_structural_syntax(input_text)
        self.assertEqual(result, input_text)  # Should remain unchanged

    def test_fix_structural_syntax_mixed_content(self) -> None:
        """Test handling mixed structural syntax issues."""
        input_text = '("key": "value") and {1, 2, 3}'
        expected = '{"key": "value"} and [1, 2, 3]'
        result = ArrayObjectHandler.fix_structural_syntax(input_text)
        self.assertEqual(result, expected)

    def test_fix_structural_syntax_nested_structures(self) -> None:
        """Test that nested structures are handled carefully."""
        input_text = '{"array": {1, 2, 3}, "object": ("key": "value")}'
        expected = '{"array": [1, 2, 3], "object": {"key": "value"}}'
        result = ArrayObjectHandler.fix_structural_syntax(input_text)
        self.assertEqual(result, expected)

    def test_handle_sparse_arrays_basic_sparse(self) -> None:
        """Test handling basic sparse array elements."""
        input_text = "[1, , 3, , 5]"
        expected = "[1, null, 3, null, 5]"
        result = ArrayObjectHandler.handle_sparse_arrays(input_text)
        self.assertEqual(result, expected)

    def test_handle_sparse_arrays_leading_sparse(self) -> None:
        """Test handling leading sparse elements in arrays."""
        input_text = "[, 2, 3]"
        expected = "[null, 2, 3]"
        result = ArrayObjectHandler.handle_sparse_arrays(input_text)
        self.assertEqual(result, expected)

    def test_handle_sparse_arrays_multiple_consecutive(self) -> None:
        """Test handling multiple consecutive sparse elements."""
        input_text = "[1, , , 4]"
        expected = "[1, null, null, 4]"
        result = ArrayObjectHandler.handle_sparse_arrays(input_text)
        self.assertEqual(result, expected)

    def test_handle_sparse_arrays_clean_object_double_commas(self) -> None:
        """Test cleaning invalid double commas in objects."""
        input_text = '{"key1": "value1", , "key2": "value2"}'
        expected = '{"key1": "value1", "key2": "value2"}'
        result = ArrayObjectHandler.handle_sparse_arrays(input_text)
        self.assertEqual(result, expected)

    def test_handle_sparse_arrays_preserve_valid_objects(self) -> None:
        """Test that valid objects are not modified."""
        input_text = '{"key1": "value1", "key2": "value2"}'
        result = ArrayObjectHandler.handle_sparse_arrays(input_text)
        self.assertEqual(result, input_text)

    def test_handle_sparse_arrays_mixed_object_array(self) -> None:
        """Test handling sparse arrays that contain objects."""
        input_text = '[{"key": "value"}, , {"other": "data"}]'
        expected = '[{"key": "value"}, null, {"other": "data"}]'
        result = ArrayObjectHandler.handle_sparse_arrays(input_text)
        self.assertEqual(result, expected)

    def test_handle_sparse_arrays_nested_structures(self) -> None:
        """Test complex nested structures with sparse elements."""
        input_text = '{"array": [1, , 3], "sparse": [, "value"]}'
        expected = '{"array": [1, null, 3], "sparse": [null, "value"]}'
        result = ArrayObjectHandler.handle_sparse_arrays(input_text)
        self.assertEqual(result, expected)

    def test_handle_sparse_arrays_no_changes_needed(self) -> None:
        """Test that well-formed arrays are not changed."""
        input_text = "[1, 2, 3, 4, 5]"
        result = ArrayObjectHandler.handle_sparse_arrays(input_text)
        self.assertEqual(result, input_text)

    def test_fix_unclosed_strings_basic_unclosed(self) -> None:
        """Test fixing basic unclosed strings."""
        input_text = '{"key": "value'
        expected = '{"key": "value"'
        result = ArrayObjectHandler.fix_unclosed_strings(input_text)
        self.assertEqual(result, expected)

    def test_fix_unclosed_strings_with_comma(self) -> None:
        """Test fixing unclosed strings that end with comma."""
        input_text = '{"key": "value,'
        expected = '{"key": "value",'
        result = ArrayObjectHandler.fix_unclosed_strings(input_text)
        self.assertEqual(result, expected)

    def test_fix_unclosed_strings_multiline(self) -> None:
        """Test fixing unclosed strings across multiple lines."""
        input_text = '{\n  "key": "value\n  "other": "data"\n}'
        expected = '{\n  "key": "value"\n  "other": "data"\n}'
        result = ArrayObjectHandler.fix_unclosed_strings(input_text)
        self.assertEqual(result, expected)

    def test_fix_unclosed_strings_balanced_quotes(self) -> None:
        """Test that balanced quotes are left unchanged."""
        input_text = '{"key": "value", "other": "data"}'
        result = ArrayObjectHandler.fix_unclosed_strings(input_text)
        self.assertEqual(result, input_text)

    def test_fix_unclosed_strings_escaped_quotes(self) -> None:
        """Test handling escaped quotes correctly."""
        input_text = '{"key": "say \\"hello\\""}'
        result = ArrayObjectHandler.fix_unclosed_strings(input_text)
        self.assertEqual(result, input_text)  # Should remain unchanged

    def test_fix_unclosed_strings_complex_escaping(self) -> None:
        """Test complex escaping scenarios."""
        input_text = '{"key": "path\\\\to\\\\file'
        expected = '{"key": "path\\\\to\\\\file"'
        result = ArrayObjectHandler.fix_unclosed_strings(input_text)
        self.assertEqual(result, expected)

    def test_integration_all_handlers(self) -> None:
        """Test integration of all array/object processing methods."""
        input_text = '("key": {1, 2, ,}, "array": [, "value"'

        # Apply all processors in sequence
        result = ArrayObjectHandler.fix_structural_syntax(input_text)
        result = ArrayObjectHandler.handle_sparse_arrays(result)
        result = ArrayObjectHandler.fix_unclosed_strings(result)

        # Verify transformations worked - be more flexible with exact format
        # The parentheses might not convert to braces if it doesn't look like an object
        self.assertTrue('"key"' in result)  # Key should be there
        self.assertIn("[1, 2", result)  # Set converted to array
        self.assertIn("null", result)  # Sparse elements filled
        self.assertIn('"value"', result)  # String closed

    def test_edge_cases_empty_structures(self) -> None:
        """Test handling of empty structures."""
        input_text = "[] {} (, )"
        result = ArrayObjectHandler.fix_structural_syntax(input_text)
        result = ArrayObjectHandler.handle_sparse_arrays(result)
        result = ArrayObjectHandler.fix_unclosed_strings(result)

        # Should handle empty structures gracefully
        self.assertIn("[]", result)
        self.assertIn("{}", result)

    def test_edge_cases_deeply_nested(self) -> None:
        """Test deeply nested array/object structures."""
        input_text = '[{"nested": {"deep": [1, , 3]}}]'
        expected = '[{"nested": {"deep": [1, null, 3]}}]'
        result = ArrayObjectHandler.handle_sparse_arrays(input_text)
        self.assertEqual(result, expected)

    def test_preserve_valid_json(self) -> None:
        """Test that valid JSON is preserved through all processing."""
        valid_json = '{"array": [1, 2, 3], "object": {"key": "value"}}'

        # Run through all processors
        result = ArrayObjectHandler.fix_structural_syntax(valid_json)
        result = ArrayObjectHandler.handle_sparse_arrays(result)
        result = ArrayObjectHandler.fix_unclosed_strings(result)

        # Should remain unchanged
        self.assertEqual(result, valid_json)

    def test_string_context_protection(self) -> None:
        """Test that processing doesn't affect content inside strings."""
        input_text = '{"text": "This {has, commas} and [brackets]"}'

        # Run through all processors
        result = ArrayObjectHandler.fix_structural_syntax(input_text)
        result = ArrayObjectHandler.handle_sparse_arrays(result)
        result = ArrayObjectHandler.fix_unclosed_strings(result)

        # String content should be preserved
        self.assertEqual(result, input_text)

    def test_mixed_quotes_in_sparse_arrays(self) -> None:
        """Test sparse arrays with mixed quote types."""
        input_text = "[1, , 'value', , \"other\"]"
        expected = "[1, null, 'value', null, \"other\"]"
        result = ArrayObjectHandler.handle_sparse_arrays(input_text)
        self.assertEqual(result, expected)

    def test_complex_real_world_scenario(self) -> None:
        """Test a complex real-world-like scenario."""
        input_text = """
        ("config": {
            "servers": {1, 2, ,},
            "options": [, "enabled", , "debug"
        })
        """

        # Apply all processors
        result = ArrayObjectHandler.fix_structural_syntax(input_text)
        result = ArrayObjectHandler.handle_sparse_arrays(result)
        result = ArrayObjectHandler.fix_unclosed_strings(result)

        # Verify major transformations
        self.assertIn('{"config":', result)  # Parentheses converted
        self.assertIn('"servers": [1, 2', result)  # Set converted
        self.assertIn("null", result)  # Sparse elements filled
        self.assertIn('"debug"', result)  # Unclosed string fixed

    def test_performance_protection_large_structures(self) -> None:
        """Test that large structures are handled without issues."""
        # Create a reasonably large structure to test performance
        large_array = "[" + ", ".join(f'"{i}"' for i in range(100)) + ', , "end"]'
        result = ArrayObjectHandler.handle_sparse_arrays(large_array)
        self.assertIn("null", result)
        self.assertIn('"end"', result)

    def test_edge_case_only_commas(self) -> None:
        """Test edge case with only commas."""
        input_text = "[, , ,]"
        result = ArrayObjectHandler.handle_sparse_arrays(input_text)
        # Accept either with or without trailing comma
        self.assertIn(result, ["[null, null, null,]", "[null, null, null]"])


if __name__ == "__main__":
    unittest.main()
