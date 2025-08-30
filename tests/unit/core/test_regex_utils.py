"""
Unit tests for regex utilities with timeout protection.
"""

import re
import unittest
from typing import Any
from unittest.mock import patch

from jsonshiatsu.core.regex_utils import (
    RegexTimeout,
    safe_regex_findall,
    safe_regex_match,
    safe_regex_search,
    safe_regex_sub,
)


class TestRegexUtils(unittest.TestCase):
    """Test safe regex utility functions."""

    def test_safe_regex_sub_normal_operation(self) -> None:
        """Test safe_regex_sub with normal regex operations."""
        result = safe_regex_sub(r"hello", "hi", "hello world")
        self.assertEqual(result, "hi world")

        result = safe_regex_sub(r"\d+", "X", "abc123def456")
        self.assertEqual(result, "abcXdefX")

    def test_safe_regex_sub_with_function_replacement(self) -> None:
        """Test safe_regex_sub with function replacement."""

        def replace_func(match: re.Match[str]) -> str:
            return match.group().upper()

        result = safe_regex_sub(r"[a-z]+", replace_func, "hello world")
        self.assertEqual(result, "HELLO WORLD")

    def test_safe_regex_sub_with_flags(self) -> None:
        """Test safe_regex_sub with regex flags."""
        result = safe_regex_sub(r"HELLO", "hi", "hello world", flags=re.IGNORECASE)
        self.assertEqual(result, "hi world")

    def test_safe_regex_sub_timeout_protection(self) -> None:
        """Test that safe_regex_sub returns original string on timeout."""
        # This is a pattern known to cause catastrophic backtracking
        catastrophic_pattern = r"(a+)+b"
        input_string = "a" * 30  # No 'b' at the end, causes infinite backtracking

        result = safe_regex_sub(catastrophic_pattern, "X", input_string, timeout=1)
        # Should return original string due to timeout
        self.assertEqual(result, input_string)

    def test_safe_regex_search_normal_operation(self) -> None:
        """Test safe_regex_search with normal operations."""
        match = safe_regex_search(r"\d+", "abc123def")
        self.assertIsNotNone(match)
        assert match is not None  # For type checker
        self.assertEqual(match.group(), "123")

        match = safe_regex_search(r"xyz", "abc123def")
        self.assertIsNone(match)

    def test_safe_regex_search_with_flags(self) -> None:
        """Test safe_regex_search with regex flags."""
        match = safe_regex_search(r"HELLO", "hello world", flags=re.IGNORECASE)
        self.assertIsNotNone(match)
        assert match is not None  # For type checker
        self.assertEqual(match.group(), "hello")

    def test_safe_regex_search_timeout_protection(self) -> None:
        """Test that safe_regex_search returns None on timeout."""
        catastrophic_pattern = r"(a+)+b"
        input_string = "a" * 30

        result = safe_regex_search(catastrophic_pattern, input_string, timeout=1)
        self.assertIsNone(result)

    def test_safe_regex_findall_normal_operation(self) -> None:
        """Test safe_regex_findall with normal operations."""
        matches = safe_regex_findall(r"\d+", "abc123def456ghi")
        self.assertEqual(matches, ["123", "456"])

        matches = safe_regex_findall(r"xyz", "abc123def")
        self.assertEqual(matches, [])

    def test_safe_regex_findall_timeout_protection(self) -> None:
        """Test that safe_regex_findall returns empty list on timeout."""
        catastrophic_pattern = r"(a+)+b"
        input_string = "a" * 30

        result = safe_regex_findall(catastrophic_pattern, input_string, timeout=1)
        self.assertEqual(result, [])

    def test_safe_regex_match_normal_operation(self) -> None:
        """Test safe_regex_match with normal operations."""
        match = safe_regex_match(r"\d+", "123abc")
        self.assertIsNotNone(match)
        assert match is not None  # For type checker
        self.assertEqual(match.group(), "123")

        match = safe_regex_match(r"\d+", "abc123")
        self.assertIsNone(match)  # match() only matches at start

    def test_safe_regex_match_timeout_protection(self) -> None:
        """Test that safe_regex_match returns None on timeout."""
        catastrophic_pattern = r"(a+)+b"
        input_string = "a" * 30

        result = safe_regex_match(catastrophic_pattern, input_string, timeout=1)
        self.assertIsNone(result)

    def test_regex_timeout_exception(self) -> None:
        """Test RegexTimeout exception can be raised."""
        with self.assertRaises(RegexTimeout):
            raise RegexTimeout("Test timeout")

    @patch("jsonshiatsu.core.regex_utils.signal.signal")
    @patch("jsonshiatsu.core.regex_utils.signal.alarm")
    def test_signal_handling(self, mock_alarm: Any, mock_signal: Any) -> None:
        """Test that signal handling is properly set up and torn down."""
        safe_regex_sub(r"test", "replacement", "test string")

        # Should set up signal handler and alarm
        self.assertEqual(mock_signal.call_count, 1)
        self.assertEqual(mock_alarm.call_count, 2)  # Set and clear alarm

    def test_exception_handling_in_regex_operations(self) -> None:
        """Test that exceptions in regex operations are handled gracefully."""
        # Invalid regex pattern should be handled gracefully
        result_sub = safe_regex_sub("[", "replacement", "test string")
        self.assertEqual(result_sub, "test string")  # Should return original

        result_search = safe_regex_search("[", "test string")
        self.assertIsNone(result_search)

        result_findall = safe_regex_findall("[", "test string")
        self.assertEqual(result_findall, [])

        result_match = safe_regex_match("[", "test string")
        self.assertIsNone(result_match)


if __name__ == "__main__":
    unittest.main()
