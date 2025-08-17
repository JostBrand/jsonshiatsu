"""
Test cases for security exceptions and error reporting.

Tests focus on error context creation, message formatting, and error reporting accuracy.
"""

import unittest
from jsonshiatsu.security.exceptions import (
    ErrorContext, jsonshiatsuError, ParseError, SecurityError, 
    ErrorReporter, ErrorSuggestionEngine
)
from jsonshiatsu.core.tokenizer import Position


class TestErrorContext(unittest.TestCase):
    """Test ErrorContext dataclass functionality."""
    
    def test_error_context_creation(self):
        """Test ErrorContext creation with all fields."""
        position = Position(line=5, column=10)
        context = ErrorContext(
            text="test json content",
            position=position,
            context_before="test ",
            context_after=" content",
            error_char="j",
            line_text="test json content",
            column_indicator="     ^"
        )
        
        self.assertEqual(context.text, "test json content")
        self.assertEqual(context.position, position)
        self.assertEqual(context.context_before, "test ")
        self.assertEqual(context.context_after, " content")
        self.assertEqual(context.error_char, "j")
        self.assertEqual(context.line_text, "test json content")
        self.assertEqual(context.column_indicator, "     ^")

    def test_error_context_minimal(self):
        """Test ErrorContext with minimal required fields."""
        position = Position(line=1, column=1)
        context = ErrorContext(
            text="x",
            position=position,
            context_before="",
            context_after="",
            error_char="x",
            line_text="x",
            column_indicator="^"
        )
        
        self.assertEqual(context.text, "x")
        self.assertEqual(context.error_char, "x")


class TestjsonshiatsuError(unittest.TestCase):
    """Test base jsonshiatsuError exception class."""
    
    def test_basic_error_creation(self):
        """Test basic error creation with message only."""
        error = jsonshiatsuError("Test error message")
        
        self.assertEqual(error.message, "Test error message")
        self.assertIsNone(error.position)
        self.assertIsNone(error.context)
        self.assertEqual(error.suggestions, [])
        self.assertIn("Test error message", str(error))

    def test_error_with_position(self):
        """Test error creation with position information."""
        position = Position(line=3, column=15)
        error = jsonshiatsuError("Parse error", position=position)
        
        self.assertEqual(error.position, position)
        self.assertIn("at line 3, column 15", str(error))

    def test_error_with_suggestions(self):
        """Test error creation with suggestions."""
        suggestions = ["Check for missing quotes", "Verify JSON syntax"]
        error = jsonshiatsuError("Syntax error", suggestions=suggestions)
        
        self.assertEqual(error.suggestions, suggestions)
        error_str = str(error)
        self.assertIn("Check for missing quotes", error_str)
        self.assertIn("Verify JSON syntax", error_str)

    def test_error_with_context(self):
        """Test error creation with full context."""
        position = Position(line=2, column=8)
        context = ErrorContext(
            text='{"key": value}',
            position=position,
            context_before='{"key": ',
            context_after="value}",
            error_char="v",
            line_text='{"key": value}',
            column_indicator="        ^"
        )
        error = jsonshiatsuError("Unquoted value", position=position, context=context)
        
        error_str = str(error)
        self.assertIn("Unquoted value", error_str)
        self.assertIn("at line 2, column 8", error_str)
        self.assertIn("Context:", error_str)
        self.assertIn('{"key": value}', error_str)
        self.assertIn("        ^", error_str)

    def test_error_formatting_edge_cases(self):
        """Test error formatting with edge cases."""
        # Error at start of line
        position = Position(line=1, column=1)
        error = jsonshiatsuError("Start error", position=position)
        self.assertIn("at line 1, column 1", str(error))
        
        # Error with empty suggestions
        error = jsonshiatsuError("Empty suggestions", suggestions=[])
        self.assertEqual(error.suggestions, [])


class TestParseError(unittest.TestCase):
    """Test ParseError specific functionality."""
    
    def test_parse_error_inheritance(self):
        """Test that ParseError inherits from jsonshiatsuError."""
        error = ParseError("Parse failure")
        self.assertIsInstance(error, jsonshiatsuError)
        self.assertEqual(error.message, "Parse failure")

    def test_parse_error_with_position(self):
        """Test ParseError with position information."""
        position = Position(line=4, column=20)
        error = ParseError("Expected colon", position=position)
        
        self.assertEqual(error.position, position)
        self.assertIn("Expected colon", str(error))
        self.assertIn("at line 4, column 20", str(error))


class TestSecurityError(unittest.TestCase):
    """Test SecurityError specific functionality."""
    
    def test_security_error_inheritance(self):
        """Test that SecurityError inherits from jsonshiatsuError."""
        error = SecurityError("Security violation")
        self.assertIsInstance(error, jsonshiatsuError)
        self.assertEqual(error.message, "Security violation")

    def test_security_error_formatting(self):
        """Test SecurityError message formatting."""
        error = SecurityError("Input too large: 5000 bytes exceeds limit 1000")
        error_str = str(error)
        self.assertIn("Input too large", error_str)
        self.assertIn("5000 bytes", error_str)


class TestErrorReporter(unittest.TestCase):
    """Test ErrorReporter functionality."""
    
    def setUp(self):
        """Set up test ErrorReporter."""
        self.test_text = '{"key": "value", "number": 123}'
        self.reporter = ErrorReporter(self.test_text)

    def test_error_reporter_creation(self):
        """Test ErrorReporter creation."""
        self.assertEqual(self.reporter.text, self.test_text)
        self.assertIsNotNone(self.reporter.lines)

    def test_create_parse_error(self):
        """Test creating ParseError through ErrorReporter."""
        position = Position(line=1, column=10)
        suggestions = ["Check syntax"]
        
        error = self.reporter.create_parse_error("Test parse error", position, suggestions)
        
        self.assertIsInstance(error, ParseError)
        self.assertEqual(error.message, "Test parse error")
        self.assertEqual(error.position, position)
        self.assertEqual(error.suggestions, suggestions)

    def test_create_security_error(self):
        """Test creating SecurityError through ErrorReporter."""
        error = self.reporter.create_security_error("Security issue")
        
        self.assertIsInstance(error, SecurityError)
        self.assertEqual(error.message, "Security issue")

    def test_error_context_generation(self):
        """Test error context generation."""
        position = Position(line=1, column=10)
        error = self.reporter.create_parse_error("Test error", position)
        
        # Should have context information
        self.assertIsNotNone(error.context)
        self.assertEqual(error.context.text, self.test_text)
        self.assertEqual(error.context.position, position)

    def test_multiline_text_handling(self):
        """Test error reporting with multiline text."""
        multiline_text = '{\n  "key": "value",\n  "error": here\n}'
        reporter = ErrorReporter(multiline_text)
        
        position = Position(line=3, column=12)
        error = reporter.create_parse_error("Unquoted value", position)
        
        self.assertIn("Unquoted value", str(error))
        self.assertIn("at line 3, column 12", str(error))

    def test_edge_position_handling(self):
        """Test error reporting with edge case positions."""
        # Position at end of text
        position = Position(line=1, column=len(self.test_text))
        error = self.reporter.create_parse_error("End of input", position)
        
        self.assertIsNotNone(error.context)
        
        # Position beyond text (should handle gracefully)
        position = Position(line=1, column=1000)
        error = self.reporter.create_parse_error("Beyond text", position)
        
        self.assertIsNotNone(error.context)


class TestErrorSuggestionEngine(unittest.TestCase):
    """Test ErrorSuggestionEngine functionality."""
    
    def test_suggest_for_unexpected_token(self):
        """Test suggestions for unexpected tokens."""
        suggestions = ErrorSuggestionEngine.suggest_for_unexpected_token('"')
        
        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0)
        self.assertTrue(any("quote" in s.lower() for s in suggestions))

    def test_suggest_for_unclosed_structure(self):
        """Test suggestions for unclosed structures."""
        # Test for object
        obj_suggestions = ErrorSuggestionEngine.suggest_for_unclosed_structure("object")
        self.assertIsInstance(obj_suggestions, list)
        self.assertTrue(any("}" in s for s in obj_suggestions))
        
        # Test for array
        arr_suggestions = ErrorSuggestionEngine.suggest_for_unclosed_structure("array")
        self.assertIsInstance(arr_suggestions, list)
        self.assertTrue(any("]" in s for s in arr_suggestions))

    def test_suggest_for_invalid_value(self):
        """Test suggestions for invalid values."""
        # Test with a value that should generate suggestions
        suggestions = ErrorSuggestionEngine.suggest_for_invalid_value("True")
        
        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0)
        
        # Test with a value that doesn't generate suggestions
        no_suggestions = ErrorSuggestionEngine.suggest_for_invalid_value("@")
        self.assertIsInstance(no_suggestions, list)
        self.assertEqual(len(no_suggestions), 0)

    def test_suggestion_quality(self):
        """Test that suggestions are helpful and non-empty."""
        test_cases = [
            ErrorSuggestionEngine.suggest_for_unexpected_token('"'),
            ErrorSuggestionEngine.suggest_for_unclosed_structure("object"),
            ErrorSuggestionEngine.suggest_for_invalid_value("True"),
        ]
        
        for suggestions in test_cases:
            self.assertIsInstance(suggestions, list)
            self.assertGreater(len(suggestions), 0)
            # All suggestions should be non-empty strings
            for suggestion in suggestions:
                self.assertIsInstance(suggestion, str)
                self.assertGreater(len(suggestion.strip()), 0)


if __name__ == '__main__':
    unittest.main()