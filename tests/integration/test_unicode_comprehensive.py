"""
Comprehensive test cases for Unicode handling in jsonshiatsu.

These tests cover Unicode normalization conflicts, escape sequences,
and the recently fixed preprocessing issues with Unicode.
"""

import json
import unittest

import jsonshiatsu


class TestUnicodeEscapeSequences(unittest.TestCase):
    """Test Unicode escape sequence handling."""

    def test_basic_unicode_escapes(self) -> None:
        """Test basic Unicode escape sequences."""
        # Simple ASCII character
        result = jsonshiatsu.loads('{"test": "\\u0041"}')
        self.assertEqual(result, {"test": "A"})

        # Multiple Unicode escapes
        result = jsonshiatsu.loads('{"test": "\\u0041\\u0042\\u0043"}')
        self.assertEqual(result, {"test": "ABC"})

        # Unicode in keys
        result = jsonshiatsu.loads('{"\\u0041": "value"}')
        self.assertEqual(result, {"A": "value"})

    def test_non_ascii_unicode_escapes(self) -> None:
        """Test non-ASCII Unicode characters."""
        # Chinese characters
        result = jsonshiatsu.loads('{"chinese": "\\u4F60\\u597D"}')
        self.assertEqual(result, {"chinese": "你好"})

        # Accented characters
        result = jsonshiatsu.loads('{"accented": "\\u00E9\\u00E8\\u00EA"}')
        self.assertEqual(result, {"accented": "éèê"})

        # Cyrillic characters
        result = jsonshiatsu.loads(
            '{"cyrillic": "\\u041F\\u0440\\u0438\\u0432\\u0435\\u0442"}'
        )
        self.assertEqual(result, {"cyrillic": "Привет"})

    def test_emoji_unicode_escapes(self) -> None:
        """Test emoji Unicode escape sequences."""
        # Simple emoji (single code point)
        result = jsonshiatsu.loads('{"smile": "\\u263A"}')
        self.assertEqual(result, {"smile": "☺"})

        # Emoji requiring surrogate pairs
        result = jsonshiatsu.loads('{"grin": "\\uD83D\\uDE00"}')
        expected_emoji = "😀"
        self.assertEqual(result, {"grin": expected_emoji})

        # Multiple emojis
        result = jsonshiatsu.loads(
            '{"emojis": "\\uD83D\\uDE00\\uD83D\\uDE01\\uD83D\\uDE02"}'
        )
        expected = "😀😁😂"
        self.assertEqual(result, {"emojis": expected})

    def test_mixed_unicode_and_ascii(self) -> None:
        """Test mixed Unicode escapes and regular ASCII."""
        result = jsonshiatsu.loads('{"mixed": "Hello \\u4F60\\u597D World!"}')
        self.assertEqual(result, {"mixed": "Hello 你好 World!"})

        # Mixed with other escape sequences
        result = jsonshiatsu.loads(
            '{"complex": "Line1\\nUnicode: \\u4F60\\u597D\\tTab"}'
        )
        self.assertEqual(result, {"complex": "Line1\nUnicode: 你好\tTab"})

    def test_invalid_unicode_escapes(self) -> None:
        """Test handling of invalid Unicode escape sequences."""
        # Incomplete Unicode escape (should handle gracefully by treating literally)
        result = jsonshiatsu.loads('{"incomplete": "\\u00"}')
        self.assertEqual(result, {"incomplete": "u00"})

        # Invalid hex characters (should handle gracefully by treating literally)
        result = jsonshiatsu.loads('{"invalid": "\\u00ZZ"}')
        self.assertEqual(result, {"invalid": "u00ZZ"})

        # Just \\u without digits (should handle gracefully by treating literally)
        result = jsonshiatsu.loads('{"just_u": "\\u"}')
        self.assertEqual(result, {"just_u": "u"})

    def test_unicode_compatibility_with_standard_json(self) -> None:
        """Test that valid Unicode escapes match standard JSON behavior."""
        test_cases = [
            '{"test": "\\u0041"}',
            '{"test": "\\u4F60\\u597D"}',
            '{"test": "\\u00E9"}',
            '{"mixed": "Hello \\u4F60\\u597D"}',
        ]

        for test_case in test_cases:
            with self.subTest(test_case=test_case):
                try:
                    std_result = json.loads(test_case)
                    flex_result = jsonshiatsu.loads(test_case)
                    self.assertEqual(std_result, flex_result)
                except json.JSONDecodeError:
                    # If standard JSON fails, jsonshiatsu should still handle it
                    # gracefully
                    flex_result = jsonshiatsu.loads(test_case)
                    self.assertIsInstance(flex_result, dict)


class TestUnicodeNormalizationConflicts(unittest.TestCase):
    """Test Unicode normalization conflicts with duplicate-looking keys."""

    def test_nfc_vs_nfd_normalization(self) -> None:
        """Test NFC vs NFD Unicode normalization conflicts."""
        # Create two visually identical keys with different Unicode representations
        # NFC: é as single codepoint (U+00E9)
        # NFD: é as e + combining accent (U+0065 + U+0301)

        nfc_key = "café"  # é as U+00E9
        nfd_key = "cafe\u0301"  # e + combining accent

        # These should be treated as different keys (following JSON spec)
        json_with_both = f'{{"{nfc_key}": "nfc", "{nfd_key}": "nfd"}}'
        result = jsonshiatsu.loads(json_with_both)

        # Should have both keys (they're different byte sequences)
        self.assertEqual(len(result), 2)
        self.assertIn(nfc_key, result)
        self.assertIn(nfd_key, result)
        self.assertEqual(result[nfc_key], "nfc")
        self.assertEqual(result[nfd_key], "nfd")

    def test_multiple_normalization_forms(self) -> None:
        """Test multiple Unicode normalization forms."""
        # Various ways to represent the same visual character
        variations = [
            "café",  # NFC
            "cafe\u0301",  # NFD
            # Add more variations if needed
        ]

        # Build JSON with all variations
        json_parts = [f'"{var}": "{i}"' for i, var in enumerate(variations)]
        json_string = "{" + ", ".join(json_parts) + "}"

        result = jsonshiatsu.loads(json_string)

        # Each variation should be treated as a separate key
        self.assertEqual(len(result), len(variations))
        for i, var in enumerate(variations):
            self.assertIn(var, result)
            self.assertEqual(result[var], str(i))

    def test_normalization_with_unicode_escapes(self) -> None:
        """Test normalization conflicts using Unicode escapes."""
        # Using Unicode escapes to create the same normalization conflict
        # \\u00E9 = é (NFC)
        # \\u0065\\u0301 = e + combining accent (NFD)

        json_string = '{"caf\\u00E9": "nfc", "cafe\\u0301": "nfd"}'
        result = jsonshiatsu.loads(json_string)

        # Should have both keys as they have different representations
        self.assertEqual(len(result), 2)
        # The keys will be the actual Unicode characters, not the escape sequences
        self.assertTrue(any("café" in key for key in result))


class TestUnicodeEdgeCases(unittest.TestCase):
    """Test Unicode edge cases and boundary conditions."""

    def test_unicode_in_different_contexts(self) -> None:
        """Test Unicode in various JSON contexts."""
        # Unicode in object keys
        result = jsonshiatsu.loads('{"\\u4F60\\u597D": "hello"}')
        self.assertEqual(result, {"你好": "hello"})

        # Unicode in array elements
        result = jsonshiatsu.loads('["\\u4F60", "\\u597D"]')
        self.assertEqual(result, ["你", "好"])

        # Unicode mixed with unquoted keys (jsonshiatsu extension)
        result = jsonshiatsu.loads('{\\u4F60\\u597D: "unquoted"}')
        self.assertEqual(result, {"你好": "unquoted"})

    def test_unicode_boundary_values(self) -> None:
        """Test Unicode boundary values and special ranges."""
        # Null character
        result = jsonshiatsu.loads('{"null_char": "\\u0000"}')
        self.assertEqual(result, {"null_char": "\u0000"})

        # Control characters
        result = jsonshiatsu.loads('{"control": "\\u0001\\u0002\\u0003"}')
        self.assertEqual(result, {"control": "\u0001\u0002\u0003"})

        # High Unicode values
        result = jsonshiatsu.loads('{"high": "\\uFFFF"}')
        self.assertEqual(result, {"high": "\uffff"})

    def test_unicode_with_other_malformed_patterns(self) -> None:
        """Test Unicode combined with other malformed JSON patterns."""
        # Unicode with comments
        malformed = """{
            // Chinese greeting
            "greeting": "\\u4F60\\u597D",
            name: "\\u5F20\\u4E09"  // Zhang San
        }"""

        result = jsonshiatsu.loads(malformed)
        expected = {"greeting": "你好", "name": "张三"}
        self.assertEqual(result, expected)

        # Unicode with function calls
        malformed = '{"date": Date("2025-08-01"), "chinese": "\\u4F60\\u597D"}'
        result = jsonshiatsu.loads(malformed)
        expected = {"date": "2025-08-01", "chinese": "你好"}
        self.assertEqual(result, expected)

    def test_unicode_preprocessing_fix(self) -> None:
        """Test the specific Unicode preprocessing bug that was fixed."""
        # This was the pattern that caused issues: Unicode escapes being
        # incorrectly identified as file paths by the preprocessing

        test_cases = [
            '{"test": "\\u0041"}',
            '{"test": "\\u4F60\\u597D"}',  # Multiple Unicode escapes
            '{"test": "\\uD83D\\uDE00"}',  # Emoji surrogate pair
        ]

        for test_case in test_cases:
            with self.subTest(test_case=test_case):
                # Should not be modified by preprocessing
                from jsonshiatsu.core.transformer import JSONPreprocessor

                preprocessed = JSONPreprocessor.preprocess(test_case)

                # The Unicode escapes should be preserved, not double-escaped
                self.assertNotIn("\\\\u", preprocessed)  # Should not have \\u
                self.assertIn("\\u", preprocessed)  # Should still have \u

                # Should parse correctly
                result = jsonshiatsu.loads(test_case)
                self.assertIsInstance(result, dict)
                self.assertIn("test", result)


class TestUnicodeFilePathDistinction(unittest.TestCase):
    """Test that Unicode escapes are distinguished from file paths."""

    def test_unicode_vs_file_paths(self) -> None:
        """Test that Unicode escapes and file paths are handled differently."""
        # Pure Unicode sequence (should not be treated as file path)
        unicode_case = '{"unicode": "\\u4F60\\u597D"}'
        result = jsonshiatsu.loads(unicode_case)
        self.assertEqual(result, {"unicode": "你好"})

        # Actual file path (should have backslashes escaped if needed)
        file_path_case = '{"path": "C:\\\\data\\\\file.txt"}'
        result = jsonshiatsu.loads(file_path_case)
        self.assertIn("path", result)
        # The exact result depends on the preprocessing logic

        # Mixed case - Unicode in a path-like context
        mixed_case = '{"mixed": "C:\\\\data\\\\\\u4F60\\u597D.txt"}'
        result = jsonshiatsu.loads(mixed_case)
        self.assertIn("mixed", result)

    def test_preprocessing_unicode_detection(self) -> None:
        """Test the preprocessing logic for detecting Unicode vs paths."""
        from jsonshiatsu.core.transformer import JSONPreprocessor

        # Pure Unicode sequences should not be modified
        pure_unicode = '{"test": "\\u4F60\\u597D"}'
        processed = JSONPreprocessor.fix_unescaped_strings(pure_unicode)
        self.assertEqual(processed, pure_unicode)  # Should be unchanged

        # File paths should be handled appropriately
        file_path = '{"path": "C:\\data\\file"}'
        processed = JSONPreprocessor.fix_unescaped_strings(file_path)
        # Should handle the file path escaping without breaking Unicode


if __name__ == "__main__":
    unittest.main()
