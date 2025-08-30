"""
Unit tests for JavaScript-specific preprocessing utilities.
"""

import unittest

from jsonshiatsu.core.javascript_handler import JavaScriptHandler


class TestJavaScriptHandler(unittest.TestCase):
    """Test JavaScript-specific preprocessing operations."""

    def test_remove_comments_line_comments(self) -> None:
        """Test removing JavaScript line comments."""
        input_text = '{"key": "value"} // this is a comment'
        expected = '{"key": "value"} '
        result = JavaScriptHandler.remove_comments(input_text)
        self.assertEqual(result, expected)

    def test_remove_comments_block_comments(self) -> None:
        """Test removing JavaScript block comments."""
        input_text = '{"key": /* comment */ "value"}'
        expected = '{"key":  "value"}'
        result = JavaScriptHandler.remove_comments(input_text)
        self.assertEqual(result, expected)

    def test_remove_comments_preserve_urls(self) -> None:
        """Test that URLs are preserved when removing comments."""
        input_text = '{"url": "https://example.com"}'
        result = JavaScriptHandler.remove_comments(input_text)
        self.assertEqual(result, input_text)  # Should remain unchanged

    def test_remove_comments_multiline_block(self) -> None:
        """Test removing multiline block comments."""
        input_text = (
            '{"key": "value", /* this is a\n multiline comment */ "key2": "value2"}'
        )
        expected = '{"key": "value",  "key2": "value2"}'
        result = JavaScriptHandler.remove_comments(input_text)
        self.assertEqual(result, expected)

    def test_unwrap_function_calls_simple_function(self) -> None:
        """Test unwrapping simple function calls."""
        input_text = 'parseJSON({"key": "value"})'
        expected = '{"key": "value"}'
        result = JavaScriptHandler.unwrap_function_calls(input_text)
        self.assertEqual(result, expected)

    def test_unwrap_function_calls_return_statement(self) -> None:
        """Test unwrapping return statements."""
        input_text = 'return {"key": "value"};'
        expected = '{"key": "value"}'
        result = JavaScriptHandler.unwrap_function_calls(input_text)
        self.assertEqual(result, expected)

    def test_unwrap_function_calls_variable_declaration(self) -> None:
        """Test unwrapping variable declarations."""
        input_text = 'const data = {"key": "value"};'
        expected = '{"key": "value"}'
        result = JavaScriptHandler.unwrap_function_calls(input_text)
        self.assertEqual(result, expected)

    def test_unwrap_function_calls_let_declaration(self) -> None:
        """Test unwrapping let variable declarations."""
        input_text = "let result = [1, 2, 3];"
        expected = "[1, 2, 3]"
        result = JavaScriptHandler.unwrap_function_calls(input_text)
        self.assertEqual(result, expected)

    def test_unwrap_function_calls_var_declaration(self) -> None:
        """Test unwrapping var variable declarations."""
        input_text = 'var info = {"name": "test"};'
        expected = '{"name": "test"}'
        result = JavaScriptHandler.unwrap_function_calls(input_text)
        self.assertEqual(result, expected)

    def test_unwrap_function_calls_no_match(self) -> None:
        """Test that non-matching text is unchanged."""
        input_text = '{"key": "value"}'
        result = JavaScriptHandler.unwrap_function_calls(input_text)
        self.assertEqual(result, input_text)

    def test_unwrap_inline_function_calls_json_parse(self) -> None:
        """Test unwrapping inline function calls like JSON.parse."""
        input_text = '{"data": JSON.parse("{\\"nested\\": \\"value\\"}")}'
        expected = '{"data": {\\"nested\\": \\"value\\"}}'  # Original behavior preserves escaping
        result = JavaScriptHandler.unwrap_inline_function_calls(input_text)
        self.assertEqual(result, expected)

    def test_unwrap_inline_function_calls_simple(self) -> None:
        """Test unwrapping simple inline function calls."""
        # parseInt is not handled by this method - it focuses on MongoDB-style functions
        input_text = "parseInt(123)"
        expected = "parseInt(123)"  # Should remain unchanged
        result = JavaScriptHandler.unwrap_inline_function_calls(input_text)
        self.assertEqual(result, expected)

    def test_evaluate_javascript_expressions_division(self) -> None:
        """Test evaluating division expressions."""
        input_text = '{"result": 22/7}'
        expected = '{"result": 3.142857142857143}'
        result = JavaScriptHandler.evaluate_javascript_expressions(input_text)
        self.assertEqual(result, expected)

    def test_evaluate_javascript_expressions_modulo(self) -> None:
        """Test evaluating modulo expressions."""
        input_text = '{"result": 10%3}'
        expected = '{"result": 1}'
        result = JavaScriptHandler.evaluate_javascript_expressions(input_text)
        self.assertEqual(result, expected)

    def test_evaluate_javascript_expressions_comparison_greater(self) -> None:
        """Test evaluating greater than comparisons."""
        input_text = '{"result": 5>3}'
        expected = '{"result": true}'
        result = JavaScriptHandler.evaluate_javascript_expressions(input_text)
        self.assertEqual(result, expected)

    def test_evaluate_javascript_expressions_comparison_less(self) -> None:
        """Test evaluating less than comparisons."""
        input_text = '{"result": 2<5}'
        expected = '{"result": true}'
        result = JavaScriptHandler.evaluate_javascript_expressions(input_text)
        self.assertEqual(result, expected)

    def test_evaluate_javascript_expressions_boolean_and_true(self) -> None:
        """Test evaluating boolean AND expressions."""
        input_text = '{"result": true && true}'
        expected = '{"result": true}'
        result = JavaScriptHandler.evaluate_javascript_expressions(input_text)
        self.assertEqual(result, expected)

    def test_evaluate_javascript_expressions_boolean_and_false(self) -> None:
        """Test evaluating boolean AND expressions with false."""
        input_text = '{"result": true && false}'
        expected = '{"result": false}'
        result = JavaScriptHandler.evaluate_javascript_expressions(input_text)
        self.assertEqual(result, expected)

    def test_evaluate_javascript_expressions_boolean_or(self) -> None:
        """Test evaluating boolean OR expressions."""
        input_text = '{"result": false || true}'
        expected = '{"result": true}'
        result = JavaScriptHandler.evaluate_javascript_expressions(input_text)
        self.assertEqual(result, expected)

    def test_evaluate_javascript_expressions_unsafe_increment(self) -> None:
        """Test that unsafe increment expressions are converted to null."""
        input_text = '{"counter": counter++}'
        expected = '{"counter": null}'
        result = JavaScriptHandler.evaluate_javascript_expressions(input_text)
        self.assertEqual(result, expected)

    def test_evaluate_javascript_expressions_unsafe_decrement(self) -> None:
        """Test that unsafe decrement expressions are converted to null."""
        input_text = '{"value": --counter}'
        expected = '{"value": null}'
        result = JavaScriptHandler.evaluate_javascript_expressions(input_text)
        self.assertEqual(result, expected)

    def test_handle_javascript_constructs_function_removal(self) -> None:
        """Test removing JavaScript function definitions."""
        input_text = 'function test() { return "hello"; } {"key": "value"}'
        expected = 'null {"key": "value"}'
        result = JavaScriptHandler.handle_javascript_constructs(input_text)
        self.assertEqual(result, expected)

    def test_handle_javascript_constructs_regex_literals(self) -> None:
        """Test converting regex literals to strings."""
        input_text = '{"pattern": /test[a-z]+/gi}'
        expected = '{"pattern": "test[a-z]+"}'
        result = JavaScriptHandler.handle_javascript_constructs(input_text)
        self.assertEqual(result, expected)

    def test_handle_javascript_constructs_template_literals(self) -> None:
        """Test converting template literals to strings."""
        input_text = '{"message": `Hello world`}'
        expected = '{"message": "Hello world"}'
        result = JavaScriptHandler.handle_javascript_constructs(input_text)
        self.assertEqual(result, expected)

    def test_handle_javascript_constructs_new_expressions(self) -> None:
        """Test converting new expressions to null."""
        input_text = '{"date": new Date()}'
        expected = '{"date": null}'
        result = JavaScriptHandler.handle_javascript_constructs(input_text)
        self.assertEqual(result, expected)

    def test_handle_javascript_constructs_arithmetic_addition(self) -> None:
        """Test handling arithmetic addition."""
        input_text = '{"result": 10 + 5}'
        expected = '{"result": 15}'
        result = JavaScriptHandler.handle_javascript_constructs(input_text)
        self.assertEqual(result, expected)

    def test_handle_javascript_constructs_arithmetic_subtraction(self) -> None:
        """Test handling arithmetic subtraction."""
        input_text = '{"result": 20 - 8}'
        expected = '{"result": 12}'
        result = JavaScriptHandler.handle_javascript_constructs(input_text)
        self.assertEqual(result, expected)

    def test_handle_javascript_constructs_complex_function(self) -> None:
        """Test removing complex nested function definitions."""
        input_text = 'function outer() { function inner() { return 1; } return 2; } {"data": "value"}'
        expected = 'null {"data": "value"}'
        result = JavaScriptHandler.handle_javascript_constructs(input_text)
        self.assertEqual(result, expected)

    def test_integration_multiple_javascript_features(self) -> None:
        """Test integration of multiple JavaScript preprocessing features."""
        # Complex case with comments, function calls, and expressions
        input_text = """
        // This is a comment
        return {
            "result": 10 + 5,
            "comparison": 3 > 1,
            "pattern": /test/g,
            "template": `hello world`
        };
        """

        # Apply all JavaScript preprocessing
        result = JavaScriptHandler.remove_comments(input_text)
        result = JavaScriptHandler.unwrap_function_calls(result)
        result = JavaScriptHandler.evaluate_javascript_expressions(result)
        result = JavaScriptHandler.handle_javascript_constructs(result)

        # Should have processed all JavaScript constructs
        self.assertIn('"result": 15', result)  # Arithmetic processed
        self.assertIn('"comparison": true', result)  # Comparison processed
        self.assertIn('"pattern": "test"', result)  # Regex converted
        self.assertIn('"template": "hello world"', result)  # Template literal converted
        self.assertNotIn("//", result)  # Comments removed
        self.assertNotIn("return", result)  # Function wrapper removed

    def test_edge_cases_empty_input(self) -> None:
        """Test handling of empty input."""
        input_text = ""
        result = JavaScriptHandler.remove_comments(input_text)
        self.assertEqual(result, input_text)

        result = JavaScriptHandler.unwrap_function_calls(input_text)
        self.assertEqual(result, input_text)

    def test_edge_cases_malformed_expressions(self) -> None:
        """Test handling of malformed JavaScript expressions."""
        # Division by zero should be handled gracefully
        input_text = '{"result": 5/0}'
        result = JavaScriptHandler.evaluate_javascript_expressions(input_text)
        self.assertIn('"result": 0', result)  # Should fallback to 0

    def test_regex_literals_with_quotes(self) -> None:
        """Test regex literals containing quotes are properly escaped."""
        input_text = '{"pattern": /test"quote/g}'
        expected = '{"pattern": "test\\"quote"}'
        result = JavaScriptHandler.handle_javascript_constructs(input_text)
        self.assertEqual(result, expected)

    def test_preserve_valid_json(self) -> None:
        """Test that valid JSON is preserved through all processing."""
        input_text = '{"valid": "json", "number": 123, "boolean": true}'

        # Run through all JavaScript processing
        result = JavaScriptHandler.remove_comments(input_text)
        result = JavaScriptHandler.unwrap_function_calls(result)
        result = JavaScriptHandler.evaluate_javascript_expressions(result)
        result = JavaScriptHandler.handle_javascript_constructs(result)

        # Should remain unchanged
        self.assertEqual(result, input_text)


if __name__ == "__main__":
    unittest.main()
