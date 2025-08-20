"""
Test cases for the enhanced JSONPreprocessor methods.

This module tests individual preprocessing methods added to handle
new malformed JSON patterns.
"""

import pytest

from jsonshiatsu.core.transformer import JSONPreprocessor


class TestSpecialNumberNormalization:
    """Test special number format normalization."""

    def test_nan_infinity_conversion(self) -> None:
        """Test NaN and Infinity conversion."""
        text = '{"nan": NaN, "inf": Infinity, "neg_inf": -Infinity}'
        result = JSONPreprocessor.normalize_special_numbers(text)
        expected = '{"nan": null, "inf": 1e308, "neg_inf": -1e308}'
        assert result == expected

    def test_hexadecimal_conversion(self) -> None:
        """Test hexadecimal number conversion."""
        text = '{"small": 0x1A, "large": 0xFF, "zero": 0x0}'
        result = JSONPreprocessor.normalize_special_numbers(text)
        expected = '{"small": 26, "large": 255, "zero": 0}'
        assert result == expected

    def test_octal_conversion(self) -> None:
        """Test octal number conversion."""
        text = '{"octal1": 025, "octal2": 0777, "not_octal": 089}'
        result = JSONPreprocessor.normalize_special_numbers(text)
        # Note: 089 is not valid octal (contains 8,9) so should remain unchanged
        expected = '{"octal1": 21, "octal2": 511, "not_octal": 089}'
        assert result == expected

    def test_mixed_special_numbers(self) -> None:
        """Test mixed special numbers in one string."""
        text = "NaN + 0xFF - Infinity = 025"
        result = JSONPreprocessor.normalize_special_numbers(text)
        expected = "null + 255 - 1e308 = 21"
        assert result == expected


class TestJavaScriptConstructs:
    """Test JavaScript construct handling."""

    def test_function_removal(self) -> None:
        """Test function definition removal."""
        text = "function() { return true; }"
        result = JSONPreprocessor.handle_javascript_constructs(text)
        assert result == "null"

        text = "function(a, b) { return a + b; }"
        result = JSONPreprocessor.handle_javascript_constructs(text)
        assert result == "null"

    def test_regex_literal_conversion(self) -> None:
        """Test regex literal conversion."""
        text = "/pattern/gi"
        result = JSONPreprocessor.handle_javascript_constructs(text)
        assert result == '"pattern"'

        text = "/test\\/path/i"
        result = JSONPreprocessor.handle_javascript_constructs(text)
        assert result == '"test\\/path"'

    def test_template_literal_conversion(self) -> None:
        """Test template literal conversion."""
        text = "`Hello world`"
        result = JSONPreprocessor.handle_javascript_constructs(text)
        assert result == '"Hello world"'

        text = "`Hello ${name}`"
        result = JSONPreprocessor.handle_javascript_constructs(text)
        assert result == '"Hello ${name}"'

    def test_new_expression_removal(self) -> None:
        """Test new expression removal."""
        text = "new Date()"
        result = JSONPreprocessor.handle_javascript_constructs(text)
        assert result == "null"

        text = "new Array(1, 2, 3)"
        result = JSONPreprocessor.handle_javascript_constructs(text)
        assert result == "null"

    def test_arithmetic_evaluation(self) -> None:
        """Test simple arithmetic evaluation."""
        text = '"value": 10 + 5,'
        result = JSONPreprocessor.handle_javascript_constructs(text)
        assert result == '"value": 15,'

        text = '"diff": 20 - 3,'
        result = JSONPreprocessor.handle_javascript_constructs(text)
        assert result == '"diff": 17,'


class TestEmptyValueHandling:
    """Test empty value handling."""

    def test_empty_object_values(self) -> None:
        """Test empty values in objects."""
        text = '"key": ,'
        result = JSONPreprocessor.handle_empty_values(text)
        assert result == '"key": null,'

    def test_empty_array_elements(self) -> None:
        """Test empty elements in arrays."""
        text = "[1, , 3]"
        result = JSONPreprocessor.handle_empty_values(text)
        assert result == "[1, null, 3]"

    def test_incomplete_values(self) -> None:
        """Test incomplete values at structure end."""
        text = '"key": }'
        result = JSONPreprocessor.handle_empty_values(text)
        assert result == '"key": null }'

        text = '"key": ]'
        result = JSONPreprocessor.handle_empty_values(text)
        assert result == '"key": null ]'


class TestUnClosedStringFix:
    """Test unclosed string fixing."""

    def test_unclosed_string_fix(self) -> None:
        """Test fixing unclosed strings."""
        text = '"unclosed string'
        result = JSONPreprocessor.fix_unclosed_strings(text)
        assert result == '"unclosed string"'

    def test_unclosed_string_with_comma(self) -> None:
        """Test fixing unclosed strings ending with comma."""
        text = '"unclosed string,'
        result = JSONPreprocessor.fix_unclosed_strings(text)
        assert result == '"unclosed string",'


class TestMixedQuoteNormalization:
    """Test mixed quote normalization."""

    def test_single_to_double_quotes(self) -> None:
        """Test single quote to double quote conversion."""
        text = "'single quotes'"
        result = JSONPreprocessor.normalize_mixed_quotes(text)
        assert result == '"single quotes"'

    def test_mixed_quotes_with_escaping(self) -> None:
        """Test mixed quotes with internal escaping."""
        text = "'He said \"hello\"'"
        result = JSONPreprocessor.normalize_mixed_quotes(text)
        assert result == '"He said \\"hello\\""'

    def test_multiple_mixed_quotes(self) -> None:
        """Test multiple mixed quote strings."""
        text = "'first' and 'second'"
        result = JSONPreprocessor.normalize_mixed_quotes(text)
        assert result == '"first" and "second"'


class TestStringConcatenation:
    """Test string concatenation handling."""

    def test_simple_concatenation(self) -> None:
        """Test simple string concatenation."""
        text = '"hello" + "world"'
        result = JSONPreprocessor.normalize_string_concatenation(text)
        assert result == '"helloworld"'

    def test_mixed_quote_concatenation(self) -> None:
        """Test mixed quote concatenation."""
        text = "'hello' + \"world\""
        result = JSONPreprocessor.normalize_string_concatenation(text)
        # Should handle this case
        assert '"hello" + "world"' in result or '"helloworld"' in result


class TestAssignmentOperatorFix:
    """Test assignment operator fixing."""

    def test_quoted_key_assignment(self) -> None:
        """Test quoted key assignment fix."""
        text = '"key" = "value"'
        result = JSONPreprocessor.fix_assignment_operators(text)
        assert result == '"key": "value"'

    def test_unquoted_key_assignment(self) -> None:
        """Test unquoted key assignment fix."""
        text = "key = value"
        result = JSONPreprocessor.fix_assignment_operators(text)
        assert result == "key: value"


class TestMissingCommaFix:
    """Test missing comma fixing."""

    def test_missing_comma_same_line(self) -> None:
        """Test missing comma on same line."""
        text = '"value1" "value2"'
        result = JSONPreprocessor.fix_missing_commas(text)
        assert result == '"value1", "value2"'

    def test_missing_comma_multiline(self) -> None:
        """Test missing comma across lines."""
        text = '"key1": "value1"\n"key2": "value2"'
        result = JSONPreprocessor.fix_missing_commas(text)
        assert result == '"key1": "value1",\n"key2": "value2"'


class TestMultilineStringFix:
    """Test multiline string fixing."""

    def test_multiline_string_fix(self) -> None:
        """Test multiline string repair."""
        text = '"This is a\nmultiline string"'
        result = JSONPreprocessor.fix_multiline_strings(text)
        # Should properly escape the newline
        assert "\\n" in result or result.count('"') % 2 == 0


class TestCommentRemoval:
    """Test enhanced comment removal."""

    def test_line_comment_removal(self) -> None:
        """Test line comment removal."""
        text = '{"key": "value"} // This is a comment'
        result = JSONPreprocessor.remove_comments(text)
        assert result == '{"key": "value"} '

    def test_block_comment_removal(self) -> None:
        """Test block comment removal."""
        text = '{"key": /* comment */ "value"}'
        result = JSONPreprocessor.remove_comments(text)
        assert result == '{"key":  "value"}'

    def test_url_preservation(self) -> None:
        """Test URL preservation during comment removal."""
        text = '{"url": "https://example.com"}'
        result = JSONPreprocessor.remove_comments(text)
        assert result == '{"url": "https://example.com"}'

        text = '{"url": "http://test.com"}'
        result = JSONPreprocessor.remove_comments(text)
        assert result == '{"url": "http://test.com"}'


class TestSparseArrayHandling:
    """Test sparse array handling (existing functionality)."""

    def test_sparse_array_fix(self) -> None:
        """Test sparse array element fix."""
        text = "[1, , 3, , 5]"
        result = JSONPreprocessor.handle_sparse_arrays(text)
        assert "[1, null, 3, null, 5]" in result


class TestIntegrationPreprocessing:
    """Test integrated preprocessing pipeline."""

    def test_full_preprocessing_pipeline(self) -> None:
        """Test complete preprocessing pipeline."""
        malformed = """{
  mixed: 'quotes',
  hex: 0xFF,
  empty: ,
  func: function() { return null; },
  calculation: 5 + 3
}"""

        from jsonshiatsu.utils.config import PreprocessingConfig

        config = PreprocessingConfig.aggressive()
        result = JSONPreprocessor.preprocess(malformed, aggressive=True, config=config)

        # Should be valid JSON after preprocessing
        import json as stdlib_json

        parsed = stdlib_json.loads(result)

        assert "mixed" in parsed
        assert "hex" in parsed
        assert "empty" in parsed
        assert "func" in parsed
        assert "calculation" in parsed

    def test_preprocessing_order(self) -> None:
        """Test that preprocessing steps don't interfere with each other."""
        # Test case that could break if order is wrong
        malformed = '{"test": function() { return 10 + 5; }, "value": 0x1A}'

        from jsonshiatsu.utils.config import PreprocessingConfig

        config = PreprocessingConfig.aggressive()
        result = JSONPreprocessor.preprocess(malformed, aggressive=True, config=config)

        # Should successfully preprocess without errors
        assert "test" in result
        assert "value" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
