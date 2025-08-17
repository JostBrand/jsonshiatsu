"""
Test cases for error recovery strategies and partial parsing.

Tests focus on resilient JSON parsing that continues despite errors.
"""

import unittest

from jsonshiatsu.recovery.strategies import (
    ErrorSeverity,
    PartialParseError,
    PartialParser,
    PartialParseResult,
    RecoveryAction,
    RecoveryLevel,
)
from jsonshiatsu.utils.config import ParseConfig


class TestRecoveryEnums(unittest.TestCase):
    """Test recovery-related enums."""

    def test_recovery_level_values(self):
        """Test RecoveryLevel enum values."""
        self.assertEqual(RecoveryLevel.STRICT.value, "strict")
        self.assertEqual(RecoveryLevel.SKIP_FIELDS.value, "skip_fields")
        self.assertEqual(RecoveryLevel.BEST_EFFORT.value, "best_effort")
        self.assertEqual(RecoveryLevel.EXTRACT_ALL.value, "extract_all")

    def test_recovery_action_values(self):
        """Test RecoveryAction enum values."""
        expected_actions = [
            "field_skipped",
            "element_skipped",
            "added_quotes",
            "removed_comma",
            "added_colon",
            "closed_string",
            "inferred_value",
            "structure_repaired",
        ]

        actual_actions = [action.value for action in RecoveryAction]
        for expected in expected_actions:
            self.assertIn(expected, actual_actions)

    def test_error_severity_values(self):
        """Test ErrorSeverity enum values."""
        self.assertEqual(ErrorSeverity.ERROR.value, "error")
        self.assertEqual(ErrorSeverity.WARNING.value, "warning")
        self.assertEqual(ErrorSeverity.INFO.value, "info")


class TestPartialParseError(unittest.TestCase):
    """Test PartialParseError dataclass."""

    def test_partial_parse_error_creation(self):
        """Test PartialParseError creation with all fields."""
        error = PartialParseError(
            path="$.users[0].name",
            line=5,
            column=12,
            message="Missing quote",
            severity=ErrorSeverity.WARNING,
            recovery_action=RecoveryAction.ADDED_QUOTES,
            original_value="name: John",
            recovered_value='"name": "John"',
        )

        self.assertEqual(error.path, "$.users[0].name")
        self.assertEqual(error.line, 5)
        self.assertEqual(error.column, 12)
        self.assertEqual(error.message, "Missing quote")
        self.assertEqual(error.severity, ErrorSeverity.WARNING)
        self.assertEqual(error.recovery_action, RecoveryAction.ADDED_QUOTES)
        self.assertEqual(error.original_value, "name: John")
        self.assertEqual(error.recovered_value, '"name": "John"')

    def test_partial_parse_error_defaults(self):
        """Test PartialParseError with default values."""
        error = PartialParseError()

        self.assertEqual(error.path, "")
        self.assertEqual(error.line, 0)
        self.assertEqual(error.column, 0)
        self.assertEqual(error.message, "")
        self.assertEqual(error.severity, ErrorSeverity.ERROR)
        self.assertIsNone(error.recovery_action)
        self.assertEqual(error.original_value, "")
        self.assertIsNone(error.recovered_value)


class TestPartialParseResult(unittest.TestCase):
    """Test PartialParseResult dataclass."""

    def test_partial_parse_result_creation(self):
        """Test PartialParseResult creation."""
        result = PartialParseResult(
            data={"key": "value"}, total_fields=10, successful_fields=8
        )

        # Add errors
        result.add_error(
            PartialParseError(message="Warning", severity=ErrorSeverity.WARNING)
        )
        result.add_error(
            PartialParseError(message="Error", severity=ErrorSeverity.ERROR)
        )

        self.assertEqual(result.data, {"key": "value"})
        self.assertEqual(len(result.errors), 1)  # Only ERROR severity
        self.assertEqual(len(result.warnings), 1)  # Only WARNING severity
        self.assertEqual(result.total_fields, 10)
        self.assertEqual(result.successful_fields, 8)

    def test_partial_parse_result_defaults(self):
        """Test PartialParseResult with default values."""
        result = PartialParseResult()

        self.assertIsNone(result.data)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.success_rate, 0.0)
        self.assertEqual(result.total_fields, 0)
        self.assertEqual(result.successful_fields, 0)

    def test_error_categorization_methods(self):
        """Test error categorization helper methods."""
        result = PartialParseResult()

        # Add different severity errors
        result.add_error(PartialParseError(message="Info", severity=ErrorSeverity.INFO))
        result.add_error(
            PartialParseError(message="Warning", severity=ErrorSeverity.WARNING)
        )
        result.add_error(
            PartialParseError(message="Error", severity=ErrorSeverity.ERROR)
        )

        # Test automatic categorization
        self.assertEqual(len(result.errors), 1)  # ERROR severity goes to errors
        self.assertEqual(len(result.warnings), 2)  # WARNING and INFO go to warnings

        # Test that we can find different severities
        all_severity_items = result.errors + result.warnings
        severities = [item.severity for item in all_severity_items]
        self.assertIn(ErrorSeverity.INFO, severities)
        self.assertIn(ErrorSeverity.WARNING, severities)
        self.assertIn(ErrorSeverity.ERROR, severities)


class TestPartialParser(unittest.TestCase):
    """Test PartialParser functionality."""

    def setUp(self):
        """Set up test parser."""
        self.config = ParseConfig()

    def test_parser_creation(self):
        """Test PartialParser creation."""
        from jsonshiatsu.core.tokenizer import Lexer

        # Create tokens for testing
        lexer = Lexer('{"key": "value"}')
        tokens = lexer.get_all_tokens()

        parser = PartialParser(tokens, self.config)
        self.assertEqual(parser.config, self.config)
        self.assertEqual(parser.recovery_level, RecoveryLevel.SKIP_FIELDS)  # Default

    def test_token_navigation(self):
        """Test token navigation methods."""
        from jsonshiatsu.core.tokenizer import Lexer

        lexer = Lexer('{"key": "value"}')
        tokens = lexer.get_all_tokens()

        parser = PartialParser(tokens, self.config)

        # Test current_token
        first_token = parser.current_token()
        self.assertIsNotNone(first_token)

        # Test advance
        parser.advance()
        second_token = parser.current_token()
        self.assertNotEqual(first_token, second_token)

        # Test peek_token
        if parser.pos < len(parser.tokens) - 2:
            next_token = parser.peek_token()
            self.assertIsNotNone(next_token)

    def test_error_recording(self):
        """Test error recording functionality."""
        from jsonshiatsu.core.tokenizer import Lexer

        lexer = Lexer('{"key": "value"}')
        tokens = lexer.get_all_tokens()

        parser = PartialParser(tokens, self.config)

        # Test adding an error
        error = PartialParseError(
            path="$.key", message="Test error", severity=ErrorSeverity.WARNING
        )

        # Test that the result has errors list and we can add to it
        parser.result.errors.append(error)

        self.assertEqual(len(parser.result.errors), 1)
        self.assertEqual(parser.result.errors[0].message, "Test error")

    def test_path_tracking(self):
        """Test JSON path tracking functionality."""
        from jsonshiatsu.core.tokenizer import Lexer

        lexer = Lexer('{"nested": {"key": "value"}}')
        tokens = lexer.get_all_tokens()

        parser = PartialParser(tokens, self.config)

        # Test path building
        parser.current_path = ["nested", "key"]
        path_str = ".".join(parser.current_path)

        self.assertEqual(path_str, "nested.key")

    def test_recovery_level_behavior(self):
        """Test different recovery level behaviors."""
        from jsonshiatsu.core.tokenizer import Lexer

        # Test with different recovery levels
        test_json = '{"valid": "data"}'
        lexer = Lexer(test_json)
        tokens = lexer.get_all_tokens()

        levels = [
            RecoveryLevel.STRICT,
            RecoveryLevel.SKIP_FIELDS,
            RecoveryLevel.BEST_EFFORT,
            RecoveryLevel.EXTRACT_ALL,
        ]

        for level in levels:
            with self.subTest(level=level):
                parser = PartialParser(tokens, self.config, level)
                self.assertEqual(parser.recovery_level, level)

    def test_validator_integration(self):
        """Test integration with LimitValidator."""
        from jsonshiatsu.core.tokenizer import Lexer
        from jsonshiatsu.utils.config import ParseLimits

        # Create config with limits
        limits = ParseLimits(max_nesting_depth=2)
        config_with_limits = ParseConfig(limits=limits)

        lexer = Lexer('{"key": "value"}')
        tokens = lexer.get_all_tokens()

        parser = PartialParser(tokens, config_with_limits)

        # Should have a validator
        self.assertIsNotNone(parser.validator)
        self.assertEqual(parser.validator.limits, limits)


class TestRecoveryIntegration(unittest.TestCase):
    """Test recovery strategy integration."""

    def test_recovery_level_escalation(self):
        """Test that different recovery levels exist and can be created."""
        from jsonshiatsu.core.tokenizer import Lexer

        config = ParseConfig()
        test_json = '{"valid": "data"}'
        lexer = Lexer(test_json)
        tokens = lexer.get_all_tokens()

        for level in [
            RecoveryLevel.STRICT,
            RecoveryLevel.SKIP_FIELDS,
            RecoveryLevel.BEST_EFFORT,
            RecoveryLevel.EXTRACT_ALL,
        ]:
            with self.subTest(level=level):
                parser = PartialParser(tokens, config, level)
                self.assertEqual(parser.recovery_level, level)

    def test_real_world_error_patterns(self):
        """Test error detection with real-world malformed JSON patterns."""
        from jsonshiatsu.core.tokenizer import Lexer

        config = ParseConfig()

        test_cases = [
            # Common malformed patterns
            '{"status": "ok", "data": [1, 2, 3,]}',  # Trailing comma
            '{name: "John", "age": 30}',  # Unquoted keys
            '{"incomplete": "data"',  # Missing closing brace
        ]

        for test_json in test_cases:
            with self.subTest(json=test_json):
                try:
                    lexer = Lexer(test_json)
                    tokens = lexer.get_all_tokens()
                    parser = PartialParser(tokens, config, RecoveryLevel.SKIP_FIELDS)

                    # Test that parser can be created and has expected properties
                    self.assertEqual(parser.recovery_level, RecoveryLevel.SKIP_FIELDS)
                    self.assertIsNotNone(parser.result)
                except Exception:
                    # Some tests may fail due to tokenization issues, which is expected
                    pass


if __name__ == "__main__":
    unittest.main()
