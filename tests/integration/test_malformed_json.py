"""
Test cases for handling malformed JSON patterns commonly found in real-world data.
"""

import unittest

from jsonshiatsu import parse
from jsonshiatsu.preprocessing.extractors import MarkdownExtractor
from jsonshiatsu.preprocessing.handlers import CommentHandler, JavaScriptHandler
from jsonshiatsu.preprocessing.repairers import StringRepairer, StructureFixer
from jsonshiatsu.utils.config import PreprocessingConfig


class TestMalformedJSONPatterns(unittest.TestCase):
    def test_markdown_code_blocks(self) -> None:
        """Test extraction of JSON from markdown code blocks."""
        # Fenced code block with json language
        markdown_json = """```json
        {"name": "John", "age": 30}
        ```"""
        result = parse(markdown_json)
        self.assertEqual(result, {"name": "John", "age": 30})

        # Fenced code block without language
        markdown_plain = """```
        {"name": "Jane", "age": 25}
        ```"""
        result = parse(markdown_plain)
        self.assertEqual(result, {"name": "Jane", "age": 25})

        # Inline code block
        inline_code = '`{"status": "success"}`'
        result = parse(inline_code)
        self.assertEqual(result, {"status": "success"})

        # Complex markdown with explanation
        complex_markdown = """Here's the JSON response:
        ```json
        {
            "users": [
                {"name": "Alice", "active": true},
                {"name": "Bob", "active": false}
            ],
            "total": 2
        }
        ```
        This contains user data."""
        result = parse(complex_markdown)
        expected = {
            "users": [
                {"name": "Alice", "active": True},
                {"name": "Bob", "active": False},
            ],
            "total": 2,
        }
        self.assertEqual(result, expected)

    def test_trailing_explanatory_text(self) -> None:
        """Test removal of explanatory text after JSON."""
        # Simple trailing text
        json_with_text = (
            '{"result": "success"} This indicates the operation completed successfully.'
        )
        result = parse(json_with_text)
        self.assertEqual(result, {"result": "success"})

        # Multiple sentences after JSON
        json_with_explanation = """{"data": [1, 2, 3]} Here are the requested numbers.
        They represent the sequence we discussed earlier."""
        result = parse(json_with_explanation)
        self.assertEqual(result, {"data": [1, 2, 3]})

        # Newline separated explanation
        json_with_newline = """{"status": "ok"}

        Explanation: The request was processed successfully."""
        result = parse(json_with_newline)
        self.assertEqual(result, {"status": "ok"})

        # Array with trailing text
        array_with_text = "[1, 2, 3, 4] These are the prime numbers less than 5."
        result = parse(array_with_text)
        self.assertEqual(result, [1, 2, 3, 4])

    def test_javascript_comments(self) -> None:
        """Test removal of JavaScript-style comments."""
        # Single line comments
        json_with_line_comments = """{
            "name": "John", // This is the user's name
            "age": 30 // User's age in years
        }"""
        result = parse(json_with_line_comments)
        self.assertEqual(result, {"name": "John", "age": 30})

        # Block comments
        json_with_block_comments = """{
            "data": /* this contains the main data */ [1, 2, 3],
            "meta": "info" /* additional metadata */
        }"""
        result = parse(json_with_block_comments)
        self.assertEqual(result, {"data": [1, 2, 3], "meta": "info"})

        # Mixed comments
        json_with_mixed_comments = """{
            // User information
            "user": {
                "name": "Alice", /* first name only */
                "verified": true // account is verified
            }
        }"""
        result = parse(json_with_mixed_comments)
        self.assertEqual(result, {"user": {"name": "Alice", "verified": True}})

    def test_multiple_json_objects(self) -> None:
        """Test extraction of first JSON when multiple are present."""
        # Two separate objects
        multiple_objects = '{"first": "object"}\n{"second": "object"}'
        result = parse(multiple_objects)
        self.assertEqual(result, {"first": "object"})

        # Objects with text between
        objects_with_text = '{"a": 1} and here is another one {"b": 2}'
        result = parse(objects_with_text)
        self.assertEqual(result, {"a": 1})

        # Array followed by object
        array_then_object = '[1, 2, 3] {"key": "value"}'
        result = parse(array_then_object)
        self.assertEqual(result, [1, 2, 3])

    def test_function_call_wrappers(self) -> None:
        """Test unwrapping of function calls around JSON."""
        # parse_json function call
        parse_call = 'parse_json({"key": "value"})'
        result = parse(parse_call)
        self.assertEqual(result, {"key": "value"})

        # JSON.parse call
        json_parse_call = 'JSON.parse({"name": "test"})'
        result = parse(json_parse_call)
        self.assertEqual(result, {"name": "test"})

        # return statement
        return_statement = 'return {"status": "complete"};'
        result = parse(return_statement)
        self.assertEqual(result, {"status": "complete"})

        # Variable assignment
        var_assignment = 'const data = {"items": [1, 2, 3]};'
        result = parse(var_assignment)
        self.assertEqual(result, {"items": [1, 2, 3]})

        # let assignment
        let_assignment = 'let response = {"success": true}'
        result = parse(let_assignment)
        self.assertEqual(result, {"success": True})

    def test_non_standard_boolean_null(self) -> None:
        """Test normalization of non-standard boolean and null values."""
        # Python-style booleans
        python_booleans = '{"active": True, "disabled": False, "empty": None}'
        result = parse(python_booleans)
        self.assertEqual(result, {"active": True, "disabled": False, "empty": None})

        # Yes/No values
        yes_no_values = '{"enabled": yes, "disabled": no}'
        result = parse(yes_no_values)
        self.assertEqual(result, {"enabled": True, "disabled": False})

        # Undefined value
        undefined_value = '{"value": undefined, "other": "data"}'
        result = parse(undefined_value)
        self.assertEqual(result, {"value": None, "other": "data"})

        # Mixed case
        mixed_case = '{"a": YES, "b": No, "c": UNDEFINED}'
        result = parse(mixed_case)
        self.assertEqual(result, {"a": True, "b": False, "c": None})

    def test_incomplete_json_structures(self) -> None:
        """Test handling of incomplete JSON with aggressive mode."""
        # Missing closing brace
        incomplete_object = '{"name": "John", "age": 30'
        result = parse(incomplete_object, aggressive=True)
        self.assertEqual(result, {"name": "John", "age": 30})

        # Missing closing bracket
        incomplete_array = "[1, 2, 3"
        result = parse(incomplete_array, aggressive=True)
        self.assertEqual(result, [1, 2, 3])

        # Nested incomplete structure
        nested_incomplete = '{"user": {"name": "Alice", "data": [1, 2'
        result = parse(nested_incomplete, aggressive=True)
        self.assertEqual(result, {"user": {"name": "Alice", "data": [1, 2]}})

        # Incomplete string
        incomplete_string = '{"message": "Hello world'
        result = parse(incomplete_string, aggressive=True)
        self.assertEqual(result, {"message": "Hello world"})

    def test_malformed_strings(self) -> None:
        """Test handling of strings with escaping issues."""
        # Unescaped quotes in strings (basic case)
        # This should be handled by the existing parser's string handling

        # File paths with single backslashes (will be fixed by aggressive preprocessing)
        # Using a case that demonstrates the fix_unescaped_strings function
        # Single backslashes that aren't escape sequences
        file_path = '{"path": "C:\\data\\file"}'
        result = parse(file_path, aggressive=True)
        # The preprocessor should handle this case and parse successfully
        self.assertIsInstance(result, dict)
        self.assertIn("path", result)

    def test_numbers_with_formatting(self) -> None:
        """Test handling of incorrectly formatted numbers."""
        # Note: These cases might not be fully solvable without breaking valid JSON
        # We test what currently works and document limitations

        # Leading zeros (this should work with existing parser)
        leading_zero = '{"id": 007}'
        result = parse(leading_zero)
        self.assertEqual(result, {"id": 7})

        # The following would require more sophisticated preprocessing:
        # Currency symbols, percentage signs, comma separators
        # These are documented as limitations for now

    def test_real_world_complex_cases(self) -> None:
        """Test complex real-world malformed JSON scenarios."""
        # Markdown with comments and trailing text
        complex_case = """```json
        {
            // Configuration data
            "server": {
                "host": "localhost", /* default host */
                "port": 8080,
                "ssl": false
            },
            "features": ["auth", "logging"], // enabled features
            "debug": True
        }
        ```
        This configuration enables the development server."""

        result = parse(complex_case)
        expected = {
            "server": {"host": "localhost", "port": 8080, "ssl": False},
            "features": ["auth", "logging"],
            "debug": True,
        }
        self.assertEqual(result, expected)

        # Function call with comments
        function_with_comments = """return {
            // User data
            "name": "Alice",
            "status": "active", /* currently online */
            "preferences": {
                "theme": "dark",
                "notifications": yes // user enabled notifications
            }
        };"""

        result = parse(function_with_comments)
        expected = {
            "name": "Alice",
            "status": "active",
            "preferences": {"theme": "dark", "notifications": True},
        }
        self.assertEqual(result, expected)


class TestJSONPreprocessor(unittest.TestCase):
    """Test the JSONPreprocessor class methods individually."""

    def test_extract_from_markdown(self) -> None:
        """Test markdown extraction method."""
        # JSON code block
        markdown = '```json\n{"test": "value"}\n```'
        result = MarkdownExtractor().process(markdown, PreprocessingConfig())
        self.assertEqual(result, '{"test": "value"}')

        # Plain code block
        plain = '```\n{"test": "value"}\n```'
        result = MarkdownExtractor().process(plain, PreprocessingConfig())
        self.assertEqual(result, '{"test": "value"}')

        # Inline code
        inline = 'Text `{"test": "value"}` more text'
        result = MarkdownExtractor().process(inline, PreprocessingConfig())
        self.assertEqual(result, '{"test": "value"}')

        # No markdown
        no_markdown = '{"test": "value"}'
        result = MarkdownExtractor().process(no_markdown, PreprocessingConfig())
        self.assertEqual(result, '{"test": "value"}')

    def test_remove_comments(self) -> None:
        """Test comment removal method."""
        # Line comments
        with_line_comments = '{"key": "value"} // comment'
        result = CommentHandler().process(with_line_comments, PreprocessingConfig())
        self.assertEqual(result.strip(), '{"key": "value"}')

        # Block comments
        with_block_comments = '{"key": /* comment */ "value"}'
        result = CommentHandler().process(with_block_comments, PreprocessingConfig())
        self.assertEqual(result.strip(), '{"key":  "value"}')

    def test_unwrap_function_calls(self) -> None:
        """Test function call unwrapping method."""
        # Function call
        func_call = 'parse({"key": "value"})'
        result = JavaScriptHandler().process(func_call, PreprocessingConfig())
        self.assertEqual(result, '{"key": "value"}')

        # Return statement
        return_stmt = 'return {"key": "value"};'
        result = JavaScriptHandler().process(return_stmt, PreprocessingConfig())
        self.assertEqual(result, '{"key": "value"}')

        # Variable assignment
        var_assign = 'const data = {"key": "value"};'
        result = JavaScriptHandler().process(var_assign, PreprocessingConfig())
        self.assertEqual(result, '{"key": "value"}')

    def test_normalize_boolean_null(self) -> None:
        """Test boolean and null normalization method."""
        # Python style
        python_style = '{"a": True, "b": False, "c": None}'
        result = StringRepairer().process(python_style, PreprocessingConfig())
        self.assertEqual(result, '{"a": true, "b": false, "c": null}')

        # Yes/No
        yes_no = '{"enabled": yes, "disabled": NO}'
        result = StringRepairer().process(yes_no, PreprocessingConfig())
        self.assertEqual(result, '{"enabled": true, "disabled": false}')

        # Undefined
        undefined = '{"value": undefined}'
        result = StringRepairer().process(undefined, PreprocessingConfig())
        self.assertEqual(result, '{"value": null}')

    def test_handle_incomplete_json(self) -> None:
        """Test incomplete JSON completion method."""
        # Missing closing brace
        incomplete = '{"key": "value"'
        result = StructureFixer().process(incomplete, PreprocessingConfig())
        self.assertEqual(result, '{"key": "value"}')

        # Missing closing bracket
        incomplete_array = '["a", "b"'
        result = StructureFixer().process(incomplete_array, PreprocessingConfig())
        self.assertEqual(result, '["a", "b"]')

        # Multiple missing closures
        multiple_missing = '{"array": [1, 2, {"nested": "value"'
        result = StructureFixer().process(multiple_missing, PreprocessingConfig())
        self.assertEqual(result, '{"array": [1, 2, {"nested": "value"}]}')


if __name__ == "__main__":
    unittest.main()
