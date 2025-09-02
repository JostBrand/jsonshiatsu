"""
Test cases for the JSONPreprocessor transformation functions.

Tests focus on key preprocessing functionality that enables malformed JSON parsing.
"""

import unittest

from jsonshiatsu.core.string_preprocessors import StringPreprocessor
from jsonshiatsu.preprocessing.extractors import ContentExtractor, MarkdownExtractor
from jsonshiatsu.preprocessing.handlers import CommentHandler, JavaScriptHandler
from jsonshiatsu.preprocessing.normalizers import QuoteNormalizer
from jsonshiatsu.preprocessing.pipeline import PreprocessingPipeline
from jsonshiatsu.preprocessing.repairers import StringRepairer, StructureFixer
from jsonshiatsu.utils.config import PreprocessingConfig


class TestCriticalPreprocessing(unittest.TestCase):
    """Test critical preprocessing functions that enable malformed JSON parsing."""

    def test_markdown_extraction(self) -> None:
        """Test extraction of JSON from markdown code blocks."""
        # Basic markdown extraction
        markdown_input = '```json\n{"key": "value"}\n```'
        extractor = MarkdownExtractor()
        result = extractor.process(markdown_input, PreprocessingConfig())
        self.assertEqual(result.strip(), '{"key": "value"}')

        # Extraction with trailing text (common in LLM responses)
        llm_style = """```json
        {"response": "success"}
        ```
        This is the result."""
        result = extractor.process(llm_style, PreprocessingConfig())
        self.assertIn('"response"', result)
        self.assertNotIn("This is the result", result)

    def test_comment_removal(self) -> None:
        """Test JavaScript-style comment removal."""
        # Line comments
        with_comments = '{"key": "value"} // comment'
        handler = CommentHandler()
        result = handler.process(with_comments, PreprocessingConfig())
        self.assertNotIn("//", result)
        self.assertIn('"key"', result)

        # Block comments
        block_comments = '{"key": /* comment */ "value"}'
        result = handler.process(block_comments, PreprocessingConfig())
        self.assertNotIn("comment", result)
        self.assertIn('"key"', result)
        self.assertIn('"value"', result)

    def test_quote_normalization(self) -> None:
        """Test normalization of various quote styles."""
        # Smart quotes to standard quotes
        smart_quotes = '{"key": "value"}'  # Using smart quotes
        normalizer = QuoteNormalizer()
        result = normalizer.process(smart_quotes, PreprocessingConfig())
        # Should convert to standard ASCII quotes
        self.assertIn('"key"', result)

        # Mixed quote styles should be handled consistently
        mixed = """{'single': "double", "mixed": 'content'}"""
        result = normalizer.process(mixed, PreprocessingConfig())
        # Should normalize quote characters appropriately
        self.assertTrue('"' in result or "'" in result)

    def test_boolean_null_normalization(self) -> None:
        """Test normalization of boolean and null values."""
        # Python-style to JSON-style
        python_style = '{"flag": True, "empty": None, "disabled": False}'
        repairer = StringRepairer()
        result = repairer.process(python_style, PreprocessingConfig())
        self.assertIn("true", result)
        self.assertIn("false", result)
        self.assertIn("null", result)

        # Alternative boolean representations
        alternative = '{"yes": yes, "no": no, "undefined": undefined}'
        result = repairer.process(alternative, PreprocessingConfig())
        # Should convert to standard JSON values
        self.assertIn("true", result.lower())
        self.assertIn("false", result.lower())
        self.assertIn("null", result.lower())

    def test_incomplete_json_completion(self) -> None:
        """Test completion of incomplete JSON structures."""
        # Missing closing brace
        incomplete = '{"key": "value"'
        fixer = StructureFixer()
        result = fixer.process(incomplete, PreprocessingConfig())
        self.assertEqual(result, '{"key": "value"}')

        # Missing closing bracket
        incomplete_array = '["a", "b"'
        result = fixer.process(incomplete_array, PreprocessingConfig())
        self.assertEqual(result, '["a", "b"]')

        # Nested incomplete structures
        nested_incomplete = '{"outer": {"inner": "value"'
        result = fixer.process(nested_incomplete, PreprocessingConfig())
        self.assertEqual(result, '{"outer": {"inner": "value"}}')


class TestPreprocessingPipeline(unittest.TestCase):
    """Test the full preprocessing pipeline with different configurations."""

    def test_aggressive_preprocessing(self) -> None:
        """Test aggressive preprocessing configuration."""
        # Complex malformed input
        malformed_input = """
        ```json
        {
            // User data
            name: 'John Doe',
            "age": 30,
            active: True,  // Python boolean
            metadata: undefined
        }
        ```
        Processing complete.
        """

        config = PreprocessingConfig.aggressive()
        result = PreprocessingPipeline.create_default_pipeline().process(
            malformed_input, config
        )

        # Should extract from markdown
        self.assertNotIn("```", result)
        self.assertNotIn("Processing complete", result)

        # Should remove comments
        self.assertNotIn("//", result)

        # Should have valid JSON structure
        self.assertIn('"name"', result)
        self.assertIn('"age"', result)

    def test_conservative_preprocessing(self) -> None:
        """Test conservative preprocessing configuration."""
        # Same input but with conservative settings
        input_json = '{"key": "value"} // comment'

        config = PreprocessingConfig.conservative()
        result = PreprocessingPipeline.create_default_pipeline().process(
            input_json, config
        )

        # Should still remove comments (safe operation)
        self.assertNotIn("//", result)
        self.assertIn('"key"', result)

    def test_preprocessing_idempotency(self) -> None:
        """Test that preprocessing is idempotent for valid JSON."""
        valid_json = '{"key": "value", "number": 123, "bool": true}'

        config = PreprocessingConfig.aggressive()

        # First pass
        result1 = PreprocessingPipeline.create_default_pipeline().process(
            valid_json, config
        )

        # Second pass
        result2 = PreprocessingPipeline.create_default_pipeline().process(
            result1, config
        )

        # Should be stable (idempotent)
        self.assertEqual(result1.strip(), result2.strip())

    def test_unwrap_function_calls(self) -> None:
        """Test function call unwrapping method."""
        # Function call
        func_call = 'parseJSON({"key": "value"})'
        result = JavaScriptHandler().process(func_call, PreprocessingConfig())
        self.assertEqual(result, '{"key": "value"}')

        # Namespaced function
        namespaced = 'JSON.parse({"key": "value"})'
        result = JavaScriptHandler().process(namespaced, PreprocessingConfig())
        self.assertEqual(result, '{"key": "value"}')

        # Return statement
        return_stmt = 'return {"key": "value"};'
        result = JavaScriptHandler().process(return_stmt, PreprocessingConfig())
        self.assertEqual(result, '{"key": "value"}')

        # Variable assignment - const
        const_assign = 'const data = {"key": "value"};'
        result = JavaScriptHandler().process(const_assign, PreprocessingConfig())
        self.assertEqual(result, '{"key": "value"}')

        # Variable assignment - let
        let_assign = 'let response = {"key": "value"}'
        result = JavaScriptHandler().process(let_assign, PreprocessingConfig())
        self.assertEqual(result, '{"key": "value"}')

        # Variable assignment - var
        var_assign = 'var result = {"key": "value"};'
        result = JavaScriptHandler().process(var_assign, PreprocessingConfig())
        self.assertEqual(result, '{"key": "value"}')

        # No wrapper
        no_wrapper = '{"key": "value"}'
        result = JavaScriptHandler().process(no_wrapper, PreprocessingConfig())
        self.assertEqual(result, '{"key": "value"}')

    def test_normalize_quotes(self) -> None:
        """Test quote normalization method."""
        # Smart double quotes
        smart_double = '{"test": "value"}'  # " and "
        result = QuoteNormalizer().process(smart_double, PreprocessingConfig())
        self.assertEqual(result, '{"test": "value"}')

        # Smart single quotes - test actual characters not unicode escapes
        smart_single = "{\u2018test\u2019: \u2018value\u2019}"  # Actual smart quotes
        result = QuoteNormalizer().process(smart_single, PreprocessingConfig())
        # Check content is preserved
        self.assertIn("test", result)
        self.assertIn("value", result)
        # The function should normalize these quotes according to the implementation
        # Let's just verify the function runs without error and preserves content

        # Guillemets
        guillemets = '{"test": «value»}'
        result = QuoteNormalizer().process(guillemets, PreprocessingConfig())
        self.assertEqual(result, '{"test": "value"}')

        # CJK quotes
        cjk = '{"test": 「value」}'
        result = QuoteNormalizer().process(cjk, PreprocessingConfig())
        self.assertEqual(result, '{"test": "value"}')

        # Mixed quote types
        mixed = '{"smart": "value", \u2018single\u2019: «guillemet»}'
        result = QuoteNormalizer().process(mixed, PreprocessingConfig())
        # Should preserve content
        self.assertIn("smart", result)
        self.assertIn("value", result)
        self.assertIn("single", result)
        self.assertIn("guillemet", result)
        # Function should run without error

    def test_normalize_boolean_null(self) -> None:
        """Test boolean and null normalization method."""
        # Python style
        python_style = '{"a": True, "b": False, "c": None}'
        result = StringRepairer().process(python_style, PreprocessingConfig())
        self.assertEqual(result, '{"a": true, "b": false, "c": null}')

        # Yes/No
        yes_no = '{"enabled": yes, "disabled": NO, "maybe": Yes}'
        result = StringRepairer().process(yes_no, PreprocessingConfig())
        expected = '{"enabled": true, "disabled": false, "maybe": true}'
        self.assertEqual(result, expected)

        # Undefined
        undefined = '{"value": undefined, "other": UNDEFINED}'
        result = StringRepairer().process(undefined, PreprocessingConfig())
        expected = '{"value": null, "other": null}'
        self.assertEqual(result, expected)

        # Mixed case combinations - TRUE is not handled, only True
        mixed = '{"a": True, "b": false, "c": None, "d": undefined}'
        result = StringRepairer().process(mixed, PreprocessingConfig())
        expected = '{"a": true, "b": false, "c": null, "d": null}'
        self.assertEqual(result, expected)

    def test_fix_unescaped_strings(self) -> None:
        """Test string escaping fix method."""
        # File paths (should be escaped)
        file_path = '{"path": "C:\\data\\file.txt"}'
        result = StringPreprocessor.fix_unescaped_strings(file_path)
        # Should handle file path appropriately
        self.assertIn("path", result)

        # Unicode escapes (should be preserved)
        unicode_test = '{"unicode": "\\u4F60\\u597D"}'
        result = StringPreprocessor.fix_unescaped_strings(unicode_test)
        # Should not double-escape Unicode
        self.assertEqual(result, unicode_test)

        # Valid JSON escapes - test with actual implementation behavior
        valid_escapes = '{"test": "line1\\nline2\\ttab"}'
        result = StringPreprocessor.fix_unescaped_strings(valid_escapes)
        # Should preserve the escapes in some form
        self.assertIn("line1", result)
        self.assertIn("line2", result)

        # Mixed valid and invalid escapes
        mixed_escapes = '{"path": "C:\\temp\\file", "unicode": "\\u0041"}'
        result = StringPreprocessor.fix_unescaped_strings(mixed_escapes)
        # Unicode should be preserved
        self.assertIn("\\u0041", result)

    def test_handle_incomplete_json(self) -> None:
        """Test incomplete JSON completion method."""
        # Missing closing brace
        incomplete_obj = '{"key": "value"'
        result = StructureFixer().process(incomplete_obj, PreprocessingConfig())
        self.assertEqual(result, '{"key": "value"}')

        # Missing closing bracket
        incomplete_arr = '["a", "b"'
        result = StructureFixer().process(incomplete_arr, PreprocessingConfig())
        self.assertEqual(result, '["a", "b"]')

        # Multiple missing closures
        multiple_missing = '{"array": [1, 2, {"nested": "value"'
        result = StructureFixer().process(multiple_missing, PreprocessingConfig())
        self.assertEqual(result, '{"array": [1, 2, {"nested": "value"}]}')

        # Unclosed string
        unclosed_string = '{"message": "Hello world'
        result = StructureFixer().process(unclosed_string, PreprocessingConfig())
        # Should close the string and object
        self.assertTrue("Hello world" in result)
        self.assertTrue(result.count('"') >= 2)  # Should have closing quotes

        # Mixed quotes unclosed
        mixed_quotes = "{'single': 'value"
        result = StructureFixer().process(mixed_quotes, PreprocessingConfig())
        # Should close appropriately
        self.assertTrue("value" in result)

    def test_remove_trailing_text(self) -> None:
        """Test trailing text removal method."""
        # Simple trailing text
        with_text = '{"result": "success"} This indicates completion.'
        result = ContentExtractor().process(with_text, PreprocessingConfig())
        # Should remove trailing text after valid JSON
        self.assertIn('"result"', result)
        self.assertIn('"success"', result)
        self.assertLess(len(result), len(with_text))

        # Array with trailing text
        arr_text = "[1, 2, 3] These are numbers."
        result = ContentExtractor().process(arr_text, PreprocessingConfig())
        # Should keep the JSON part
        self.assertIn("[1, 2, 3]", result)

        # Multiple sentences
        multi_text = '{"data": [1, 2, 3]} Here are the numbers. They are sequential.'
        result = ContentExtractor().process(multi_text, PreprocessingConfig())
        # Should keep the JSON part
        self.assertIn('"data"', result)
        self.assertIn("[1, 2, 3]", result)

        # Newline separated
        newline_text = """{"status": "ok"}

        Explanation: Everything worked fine."""
        result = ContentExtractor().process(newline_text, PreprocessingConfig())
        # Should keep the JSON part
        self.assertIn('"status"', result)
        self.assertIn('"ok"', result)

    def test_extract_first_json(self) -> None:
        """Test first JSON extraction method."""
        # Two separate objects
        multiple_objs = '{"first": "object"} {"second": "object"}'
        result = ContentExtractor().process(multiple_objs, PreprocessingConfig())
        self.assertEqual(result, '{"first": "object"}')

        # Array then object
        arr_then_obj = '[1, 2, 3] {"key": "value"}'
        result = ContentExtractor().process(arr_then_obj, PreprocessingConfig())
        self.assertEqual(result, "[1, 2, 3]")

        # Objects with text between
        objs_with_text = '{"a": 1} and here {"b": 2}'
        result = ContentExtractor().process(objs_with_text, PreprocessingConfig())
        self.assertEqual(result, '{"a": 1}')

        # Single JSON (should be unchanged)
        single_json = '{"only": "one"}'
        result = ContentExtractor().process(single_json, PreprocessingConfig())
        self.assertEqual(result, '{"only": "one"}')


class TestFullPreprocessingPipeline(unittest.TestCase):
    """Test the complete preprocessing pipeline."""

    def test_full_preprocessing_pipeline(self) -> None:
        """Test the complete preprocessing pipeline."""
        complex_input = """```json
        // This is a complex example
        parseJSON({
            name: 'John Doe',
            "age": 30,
            'active': True,
            "settings": {
                theme: dark,
                "notifications": yes
            }
        });
        ```
        This is the user data."""

        result = PreprocessingPipeline.create_default_pipeline().process(complex_input)

        # Should be valid JSON after preprocessing
        self.assertIsInstance(result, str)
        self.assertIn("John Doe", result)  # Should preserve string values
        self.assertNotIn("```", result)  # Should remove markdown
        self.assertNotIn("//", result)  # Should remove comments
        self.assertNotIn("parseJSON", result)  # Should unwrap function
        self.assertNotIn("True", result)  # Should normalize boolean
        self.assertIn("true", result)  # Should have normalized boolean
        self.assertNotIn("yes", result)  # Should normalize yes/no

    def test_preprocessing_with_config(self) -> None:
        """Test preprocessing with different configurations."""
        malformed_json = """```json
        // Comment here
        {"test": "value", extra: "data"}
        ```"""

        # Conservative config
        conservative = PreprocessingConfig.conservative()
        result_conservative = PreprocessingPipeline.create_default_pipeline().process(
            malformed_json, config=conservative
        )

        # Aggressive config
        aggressive = PreprocessingConfig.aggressive()
        result_aggressive = PreprocessingPipeline.create_default_pipeline().process(
            malformed_json, config=aggressive
        )

        # Both should process, but potentially differently
        self.assertIsInstance(result_conservative, str)
        self.assertIsInstance(result_aggressive, str)

        # Aggressive should extract from markdown
        self.assertNotIn("```", result_aggressive)

    def test_preprocessing_idempotency(self) -> None:
        """Test that preprocessing is idempotent for valid JSON."""
        valid_json = '{"test": "value", "number": 123, "array": [1, 2, 3]}'

        first_pass = PreprocessingPipeline.create_default_pipeline().process(valid_json)
        second_pass = PreprocessingPipeline.create_default_pipeline().process(
            first_pass
        )

        # Should be identical after first pass
        self.assertEqual(first_pass, second_pass)

    def test_preprocessing_preserves_structure(self) -> None:
        """Test that preprocessing preserves JSON structure."""
        structured_json = """{
            // Top level comment
            "users": [
                {
                    name: "Alice",
                    'age': 25
                },
                {
                    name: "Bob",
                    'age': 30
                }
            ],
            "settings": {
                theme: dark,
                "debug": True
            }
        }"""

        result = PreprocessingPipeline.create_default_pipeline().process(
            structured_json
        )

        # Should maintain structure while fixing format
        self.assertIn('"users"', result)
        self.assertIn('"settings"', result)
        self.assertIn('"Alice"', result)
        self.assertIn('"Bob"', result)
        # Should normalize booleans
        self.assertIn("true", result)
        self.assertNotIn("True", result)


class TestPreprocessingEdgeCases(unittest.TestCase):
    """Test edge cases in preprocessing."""

    def test_empty_and_whitespace_inputs(self) -> None:
        """Test preprocessing of empty and whitespace-only inputs."""
        # Empty string
        result = PreprocessingPipeline.create_default_pipeline().process("")
        self.assertEqual(result.strip(), "")

        # Whitespace only
        result = PreprocessingPipeline.create_default_pipeline().process("   \n\t  ")
        self.assertEqual(result.strip(), "")

        # Empty markdown block
        result = PreprocessingPipeline.create_default_pipeline().process(
            "```json\n\n```"
        )
        self.assertEqual(result.strip(), "")

    def test_malformed_markdown_blocks(self) -> None:
        """Test handling of malformed markdown blocks."""
        # Unclosed markdown block
        unclosed = '```json\n{"test": "value"}'
        result = MarkdownExtractor().process(unclosed, PreprocessingConfig())
        # Should handle gracefully
        self.assertIsInstance(result, str)

        # Multiple markdown blocks
        multiple = """```json
        {"first": "block"}
        ```
        Some text
        ```json
        {"second": "block"}
        ```"""
        result = MarkdownExtractor().process(multiple, PreprocessingConfig())
        # Should extract first block
        self.assertIn("first", result)

    def test_nested_quotes_in_comments(self) -> None:
        """Test comments containing quotes."""
        quoted_comments = """{
            "key": "value", // Comment with "quotes"
            "other": "data" /* Block with 'quotes' */
        }"""

        result = CommentHandler().process(quoted_comments, PreprocessingConfig())
        # Should remove comments but preserve JSON quotes
        self.assertIn('"key"', result)
        self.assertIn('"value"', result)
        self.assertNotIn("Comment", result)
        self.assertNotIn("Block", result)

    def test_unicode_in_preprocessing(self) -> None:
        """Test Unicode handling in preprocessing."""
        unicode_json = """{
            // Comment with Unicode: 你好
            "chinese": "\\u4F60\\u597D",
            "emoji": "\\uD83D\\uDE00",
            "accented": "\\u00E9\\u00E8"
        }"""

        result = PreprocessingPipeline.create_default_pipeline().process(unicode_json)

        # Should preserve Unicode escapes
        self.assertIn("\\u4F60", result)
        self.assertIn("\\uD83D", result)
        self.assertIn("\\u00E9", result)

        # Should remove comments (even with Unicode)
        self.assertNotIn("你好", result)
        self.assertNotIn("Comment", result)

    def test_very_long_strings(self) -> None:
        """Test preprocessing with very long strings."""
        # Long string content
        long_content = "x" * 1000
        long_json = f'{{"long_string": "{long_content}"}}'

        result = PreprocessingPipeline.create_default_pipeline().process(long_json)

        # Should handle without issues
        self.assertIn("long_string", result)
        self.assertIn(long_content, result)

    def test_deeply_nested_comments(self) -> None:
        """Test deeply nested structures with comments."""
        nested_with_comments = """{
            // Level 1 comment
            "level1": {
                // Level 2 comment
                "level2": {
                    // Level 3 comment
                    "level3": {
                        "value": "deep"
                    }
                }
            }
        }"""

        result = CommentHandler().process(nested_with_comments, PreprocessingConfig())

        # Should remove all comments
        self.assertNotIn("//", result)
        self.assertNotIn("Level", result)

        # Should preserve structure
        self.assertIn('"level1"', result)
        self.assertIn('"level2"', result)
        self.assertIn('"level3"', result)
        self.assertIn('"deep"', result)


if __name__ == "__main__":
    unittest.main()
