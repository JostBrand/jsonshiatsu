"""
Partial error parsing for jsonshiatsu - extract valid data even from malformed JSON.

This module implements resilient JSON parsing that continues processing despite
syntax errors, collecting valid data while reporting detailed error information.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from ..core.tokenizer import Lexer, Position, Token, TokenType
from ..security.exceptions import ErrorReporter
from ..security.limits import LimitValidator
from ..utils.config import ParseConfig


class RecoveryLevel(Enum):
    """Levels of error recovery during parsing."""

    STRICT = "strict"  # Fail on first error (current behavior)
    SKIP_FIELDS = "skip_fields"  # Skip malformed fields, keep valid ones
    BEST_EFFORT = "best_effort"  # Try to repair common issues
    EXTRACT_ALL = "extract_all"  # Get any valid data, report everything


class RecoveryAction(Enum):
    """Types of recovery actions that can be taken."""

    FIELD_SKIPPED = "field_skipped"
    ELEMENT_SKIPPED = "element_skipped"
    ADDED_QUOTES = "added_quotes"
    REMOVED_COMMA = "removed_comma"
    ADDED_COLON = "added_colon"
    CLOSED_STRING = "closed_string"
    INFERRED_VALUE = "inferred_value"
    STRUCTURE_REPAIRED = "structure_repaired"


class ErrorSeverity(Enum):
    """Severity levels for parsing errors."""

    ERROR = "error"  # Fatal error, data lost
    WARNING = "warning"  # Non-fatal issue, data preserved
    INFO = "info"  # Informational, recovery applied


@dataclass
class PartialParseError:
    """Detailed error information for partial parsing."""

    path: str = ""  # JSONPath to error location
    line: int = 0  # Line number
    column: int = 0  # Column number
    error_type: str = ""  # Category of error
    message: str = ""  # Human-readable description
    suggestion: str = ""  # How to fix it
    context_before: str = ""  # Text before error
    context_after: str = ""  # Text after error
    severity: ErrorSeverity = ErrorSeverity.ERROR
    recovery_attempted: bool = False
    recovery_action: Optional[RecoveryAction] = None
    original_value: str = ""  # Original malformed content
    recovered_value: Any = None  # What was recovered (if any)


@dataclass
class PartialParseResult:
    """Result of partial parsing with error recovery."""

    data: Any = None  # Successfully parsed data
    errors: list[PartialParseError] = field(default_factory=list)
    warnings: list[PartialParseError] = field(default_factory=list)
    success_rate: float = 0.0  # Percentage of input successfully parsed
    recovery_actions: list[RecoveryAction] = field(default_factory=list)
    total_fields: int = 0  # Total fields/elements encountered
    successful_fields: int = 0  # Successfully parsed fields/elements

    def add_error(self, error: PartialParseError) -> None:
        """Add an error to the appropriate collection."""
        if error.severity == ErrorSeverity.ERROR:
            self.errors.append(error)
        else:
            self.warnings.append(error)

        if error.recovery_action:
            self.recovery_actions.append(error.recovery_action)

    def calculate_success_rate(self) -> float:
        """Calculate the success rate based on processed fields."""
        if self.total_fields == 0:
            self.success_rate = 0.0
        else:
            self.success_rate = (self.successful_fields / self.total_fields) * 100.0
        return self.success_rate


class PartialParser:
    """Parser that can recover from errors and extract partial data."""

    def __init__(
        self,
        tokens: list[Token],
        config: ParseConfig,
        recovery_level: RecoveryLevel = RecoveryLevel.SKIP_FIELDS,
    ):
        self.tokens = tokens
        self.tokens_length = len(tokens)
        self.pos = 0
        self.config = config
        self.recovery_level = recovery_level
        self.validator = LimitValidator(config.limits) if config.limits else None

        self.current_path: list[str] = []
        self.result = PartialParseResult()
        self.error_reporter: Optional[ErrorReporter] = None

        self.in_recovery_mode = False
        self.recovery_depth = 0

    def set_error_reporter(self, error_reporter: ErrorReporter) -> None:
        """Set error reporter for enhanced error information."""
        self.error_reporter = error_reporter

    def current_token(self) -> Optional[Token]:
        """Get current token safely."""
        if self.pos >= self.tokens_length:
            return None
        return self.tokens[self.pos]

    def advance(self) -> Optional[Token]:
        """Advance to next token."""
        token = self.current_token()
        if self.pos < self.tokens_length - 1:
            self.pos += 1
        return token

    def peek_token(self, offset: int = 1) -> Optional[Token]:
        """Peek at future token."""
        pos = self.pos + offset
        if pos >= self.tokens_length:
            return None
        return self.tokens[pos]

    def skip_whitespace_and_newlines(self) -> None:
        """Skip whitespace and newline tokens."""
        while self.pos < self.tokens_length and self.tokens[self.pos].type in [
            TokenType.WHITESPACE,
            TokenType.NEWLINE,
        ]:
            self.pos += 1

    def create_error(
        self,
        message: str,
        error_type: str = "syntax_error",
        suggestion: str = "",
        severity: ErrorSeverity = ErrorSeverity.ERROR,
    ) -> PartialParseError:
        """Create a detailed error object."""
        token = self.current_token()
        position = token.position if token else Position(0, 0)

        error = PartialParseError(
            path=".".join(self.current_path),
            line=position.line,
            column=position.column,
            error_type=error_type,
            message=message,
            suggestion=suggestion,
            severity=severity,
        )

        if self.error_reporter and token:
            context = self.error_reporter.create_context(position)
            error.context_before = context.context_before
            error.context_after = context.context_after

        return error

    def attempt_recovery(self, error: PartialParseError) -> tuple[bool, Any]:
        """Attempt to recover from an error."""
        if self.recovery_level == RecoveryLevel.STRICT:
            return False, None

        if error.error_type == "missing_quotes":
            return self._recover_missing_quotes(error)
        elif error.error_type == "trailing_comma":
            return self._recover_trailing_comma(error)
        elif error.error_type == "missing_colon":
            return self._recover_missing_colon(error)
        elif error.error_type == "unclosed_string":
            return self._recover_unclosed_string(error)
        elif error.error_type == "invalid_value":
            return self._recover_invalid_value(error)

        return False, None

    def _recover_missing_quotes(self, error: PartialParseError) -> tuple[bool, Any]:
        """Try to recover from missing quotes around keys/values."""
        if self.recovery_level not in [
            RecoveryLevel.BEST_EFFORT,
            RecoveryLevel.EXTRACT_ALL,
        ]:
            return False, None

        token = self.current_token()
        if not token or token.type != TokenType.IDENTIFIER:
            return False, None

        recovered_value = token.value
        error.recovery_attempted = True
        error.recovery_action = RecoveryAction.ADDED_QUOTES
        error.recovered_value = recovered_value
        error.severity = ErrorSeverity.WARNING

        return True, recovered_value

    def _recover_trailing_comma(self, error: PartialParseError) -> tuple[bool, Any]:
        """Recover from trailing commas."""
        if self.recovery_level not in [
            RecoveryLevel.BEST_EFFORT,
            RecoveryLevel.EXTRACT_ALL,
        ]:
            return False, None

        current_token = self.current_token()
        if current_token and current_token.type == TokenType.COMMA:
            self.advance()
            error.recovery_attempted = True
            error.recovery_action = RecoveryAction.REMOVED_COMMA
            error.severity = ErrorSeverity.WARNING
            return True, None

        return False, None

    def _recover_missing_colon(self, error: PartialParseError) -> tuple[bool, Any]:
        """Recover from missing colon after object key."""
        # Look ahead to see if we can infer the structure
        next_token = self.peek_token()
        if next_token and next_token.type in [
            TokenType.STRING,
            TokenType.NUMBER,
            TokenType.BOOLEAN,
            TokenType.NULL,
        ]:
            error.recovery_attempted = True
            error.recovery_action = RecoveryAction.ADDED_COLON
            error.severity = ErrorSeverity.WARNING
            return True, None

        return False, None

    def _recover_unclosed_string(self, error: PartialParseError) -> tuple[bool, Any]:
        """Recover from unclosed strings."""
        token = self.current_token()
        if not token:
            return False, None

        recovered_value = token.value
        error.recovery_attempted = True
        error.recovery_action = RecoveryAction.CLOSED_STRING
        error.recovered_value = recovered_value
        error.severity = ErrorSeverity.WARNING

        return True, recovered_value

    def _recover_invalid_value(self, error: PartialParseError) -> tuple[bool, Any]:
        """Recover from invalid values by inference."""
        token = self.current_token()
        if not token:
            return False, None

        value = token.value.lower()
        recovered: Any
        if value in ["true", "false"]:
            recovered = value == "true"
        elif value in ["null", "none", "undefined"]:
            recovered = None
        elif token.type == TokenType.IDENTIFIER:
            recovered = token.value
        else:
            return False, None

        error.recovery_attempted = True
        error.recovery_action = RecoveryAction.INFERRED_VALUE
        error.recovered_value = recovered
        error.severity = ErrorSeverity.WARNING

        return True, recovered

    def skip_to_recovery_point(self) -> None:
        """Skip tokens until we find a reasonable recovery point."""
        recovery_tokens = [
            TokenType.COMMA,
            TokenType.RBRACE,
            TokenType.RBRACKET,
            TokenType.EOF,
        ]

        while self.pos < self.tokens_length:
            token = self.current_token()
            if not token or token.type in recovery_tokens:
                break
            self.advance()

    def parse_value_with_recovery(self) -> tuple[Any, bool]:
        """Parse a value with error recovery."""
        self.skip_whitespace_and_newlines()
        token = self.current_token()

        if not token:
            error = self.create_error("Unexpected end of input")
            self.result.add_error(error)
            return None, False

        self.result.total_fields += 1

        try:
            if token.type == TokenType.STRING:
                if self.validator:
                    self.validator.validate_string_length(token.value)
                self.advance()
                self.result.successful_fields += 1
                return token.value, True

            elif token.type == TokenType.NUMBER:
                if self.validator:
                    self.validator.validate_number_length(token.value)
                self.advance()
                value = token.value
                try:
                    if "." in value or "e" in value.lower():
                        result = float(value)
                    else:
                        result = int(value)
                    self.result.successful_fields += 1
                    return result, True
                except ValueError:
                    error = self.create_error(
                        f"Invalid number format: {value}", "invalid_number"
                    )
                    recovered, recovery_value = self.attempt_recovery(error)
                    self.result.add_error(error)
                    if recovered:
                        self.result.successful_fields += 1
                        return recovery_value, True
                    return None, False

            elif token.type == TokenType.BOOLEAN:
                self.advance()
                self.result.successful_fields += 1
                return token.value == "true", True

            elif token.type == TokenType.NULL:
                self.advance()
                self.result.successful_fields += 1
                return None, True

            elif token.type == TokenType.IDENTIFIER:
                error = self.create_error(
                    f"Unquoted identifier: {token.value}",
                    "missing_quotes",
                    "Add quotes around the value",
                )
                recovered, recovery_value = self.attempt_recovery(error)
                self.result.add_error(error)

                if recovered:
                    self.advance()
                    self.result.successful_fields += 1
                    return recovery_value, True
                else:
                    self.advance()
                    return None, False

            elif token.type == TokenType.LBRACE:
                return self.parse_object_with_recovery()

            elif token.type == TokenType.LBRACKET:
                return self.parse_array_with_recovery()

            else:
                error = self.create_error(
                    f"Unexpected token: {token.type}", "syntax_error"
                )
                self.result.add_error(error)
                self.advance()
                return None, False

        except Exception as e:
            error = self.create_error(f"Parse error: {str(e)}", "parse_exception")
            self.result.add_error(error)
            self.skip_to_recovery_point()
            return None, False

    def parse_object_with_recovery(self) -> tuple[dict[str, Any], bool]:
        """Parse an object with error recovery."""
        self.skip_whitespace_and_newlines()

        current_token = self.current_token()
        if not current_token or current_token.type != TokenType.LBRACE:
            error = self.create_error("Expected '{'", "syntax_error")
            self.result.add_error(error)
            return {}, False

        if self.validator:
            self.validator.enter_structure()

        self.advance()
        self.skip_whitespace_and_newlines()

        obj: dict[str, Any] = {}
        obj_success = True

        current_token = self.current_token()
        if current_token and current_token.type == TokenType.RBRACE:
            self.advance()
            if self.validator:
                self.validator.exit_structure()
            self.result.successful_fields += 1
            return obj, True

        while True:
            current_token = self.current_token()
            if not current_token or current_token.type == TokenType.RBRACE:
                break
            (
                key_success,
                key,
                value_success,
                value,
            ) = self._parse_object_pair_with_recovery()

            if key_success and key is not None and value_success:
                obj[key] = value

            self.skip_whitespace_and_newlines()

            current = self.current_token()
            if not current:
                error = self.create_error(
                    "Unexpected end of input in object", "unclosed_object"
                )
                self.result.add_error(error)
                obj_success = False
                break

            if current.type == TokenType.COMMA:
                self.advance()
                self.skip_whitespace_and_newlines()

                current_token = self.current_token()
                if current_token and current_token.type == TokenType.RBRACE:
                    if self.recovery_level in [
                        RecoveryLevel.BEST_EFFORT,
                        RecoveryLevel.EXTRACT_ALL,
                    ]:
                        warning = self.create_error(
                            "Trailing comma in object",
                            "trailing_comma",
                            "Remove trailing comma",
                            ErrorSeverity.WARNING,
                        )
                        warning.recovery_attempted = True
                        warning.recovery_action = RecoveryAction.REMOVED_COMMA
                        self.result.add_error(warning)
                    break
            elif current.type == TokenType.RBRACE:
                break
            else:
                error = self.create_error(
                    f"Expected ', ' or '}}' but found {current.type}",
                    "syntax_error",
                )
                self.result.add_error(error)
                obj_success = False

                if self.recovery_level in [
                    RecoveryLevel.SKIP_FIELDS,
                    RecoveryLevel.BEST_EFFORT,
                    RecoveryLevel.EXTRACT_ALL,
                ]:
                    self.skip_to_recovery_point()
                    continue
                else:
                    break

        current_token = self.current_token()
        if current_token and current_token.type == TokenType.RBRACE:
            self.advance()
            if self.validator:
                self.validator.exit_structure()
        else:
            error = self.create_error("Expected '}' to close object", "unclosed_object")
            self.result.add_error(error)
            obj_success = False

        if obj_success and obj:
            self.result.successful_fields += 1

        return obj, obj_success or bool(obj)

    def _parse_object_pair_with_recovery(self) -> tuple[bool, Optional[str], bool, Any]:
        """Parse a key-value pair with recovery."""
        self.skip_whitespace_and_newlines()

        key_token = self.current_token()
        if not key_token:
            return False, None, False, None

        key = None
        key_success = False

        if key_token.type in [TokenType.STRING, TokenType.IDENTIFIER]:
            key = key_token.value
            key_success = True

            if key_token.type == TokenType.IDENTIFIER:
                # Unquoted key - issue warning but continue
                warning = self.create_error(
                    f"Unquoted object key: {key}",
                    "missing_quotes",
                    "Add quotes around the key",
                    ErrorSeverity.WARNING,
                )
                warning.recovery_attempted = True
                warning.recovery_action = RecoveryAction.ADDED_QUOTES
                warning.recovered_value = key
                self.result.add_error(warning)

            self.current_path.append(key)
            self.advance()
        else:
            error = self.create_error(
                f"Expected object key, got {key_token.type}", "invalid_key"
            )
            self.result.add_error(error)

            if self.recovery_level in [
                RecoveryLevel.SKIP_FIELDS,
                RecoveryLevel.BEST_EFFORT,
                RecoveryLevel.EXTRACT_ALL,
            ]:
                self.skip_to_recovery_point()
                return False, None, False, None
            else:
                return False, None, False, None

        self.skip_whitespace_and_newlines()

        # Expect colon
        colon_token = self.current_token()
        if not colon_token or colon_token.type != TokenType.COLON:
            error = self.create_error("Expected ':' after object key", "missing_colon")

            if self.recovery_level in [
                RecoveryLevel.BEST_EFFORT,
                RecoveryLevel.EXTRACT_ALL,
            ]:
                # Try to recover by looking ahead
                next_token = self.peek_token()
                if next_token and next_token.type in [
                    TokenType.STRING,
                    TokenType.NUMBER,
                    TokenType.BOOLEAN,
                    TokenType.NULL,
                    TokenType.LBRACE,
                    TokenType.LBRACKET,
                ]:
                    error.recovery_attempted = True
                    error.recovery_action = RecoveryAction.ADDED_COLON
                    error.severity = ErrorSeverity.WARNING
                    self.result.add_error(error)
                    # Continue without advancing past colon
                else:
                    self.result.add_error(error)
                    if key:
                        self.current_path.pop()
                    return key_success, key, False, None
            else:
                self.result.add_error(error)
                if key:
                    self.current_path.pop()
                return key_success, key, False, None
        else:
            self.advance()  # Skip ':'

        self.skip_whitespace_and_newlines()

        # Parse value
        value, value_success = self.parse_value_with_recovery()

        if key:
            self.current_path.pop()

        return key_success, key, value_success, value

    def parse_array_with_recovery(self) -> tuple[list[Any], bool]:
        """Parse an array with error recovery."""
        self.skip_whitespace_and_newlines()

        current_token = self.current_token()
        if not current_token or current_token.type != TokenType.LBRACKET:
            error = self.create_error("Expected '['", "syntax_error")
            self.result.add_error(error)
            return [], False

        if self.validator:
            self.validator.enter_structure()

        self.advance()
        self.skip_whitespace_and_newlines()

        arr: list[Any] = []
        arr_success = True
        element_index = 0

        current_token = self.current_token()
        if current_token and current_token.type == TokenType.RBRACKET:
            self.advance()
            if self.validator:
                self.validator.exit_structure()
            self.result.successful_fields += 1
            return arr, True

        while True:
            current_token = self.current_token()
            if not current_token or current_token.type == TokenType.RBRACKET:
                break
            self.current_path.append(f"[{element_index}]")

            # Parse array element
            value, success = self.parse_value_with_recovery()

            if success:
                arr.append(value)
            elif self.recovery_level in [RecoveryLevel.EXTRACT_ALL]:
                # Include None for failed elements in extract_all mode
                arr.append(None)

            self.current_path.pop()
            element_index += 1

            self.skip_whitespace_and_newlines()

            current = self.current_token()
            if not current:
                error = self.create_error(
                    "Unexpected end of input in array", "unclosed_array"
                )
                self.result.add_error(error)
                arr_success = False
                break

            if current.type == TokenType.COMMA:
                self.advance()
                self.skip_whitespace_and_newlines()

                current_token = self.current_token()
                if current_token and current_token.type == TokenType.RBRACKET:
                    if self.recovery_level in [
                        RecoveryLevel.BEST_EFFORT,
                        RecoveryLevel.EXTRACT_ALL,
                    ]:
                        warning = self.create_error(
                            "Trailing comma in array",
                            "trailing_comma",
                            "Remove trailing comma",
                            ErrorSeverity.WARNING,
                        )
                        warning.recovery_attempted = True
                        warning.recovery_action = RecoveryAction.REMOVED_COMMA
                        self.result.add_error(warning)
                    break
            elif current.type == TokenType.RBRACKET:
                break
            else:
                error = self.create_error(
                    f"Expected ', ' or ']' but found {current.type}",
                    "syntax_error",
                )
                self.result.add_error(error)
                arr_success = False

                if self.recovery_level in [
                    RecoveryLevel.SKIP_FIELDS,
                    RecoveryLevel.BEST_EFFORT,
                    RecoveryLevel.EXTRACT_ALL,
                ]:
                    self.skip_to_recovery_point()
                    continue
                else:
                    break

        # Close array
        current_token = self.current_token()
        if current_token and current_token.type == TokenType.RBRACKET:
            self.advance()
            if self.validator:
                self.validator.exit_structure()
        else:
            error = self.create_error("Expected ']' to close array", "unclosed_array")
            self.result.add_error(error)
            arr_success = False

        if arr_success and arr:
            self.result.successful_fields += 1

        return arr, arr_success or bool(arr)  # Partial success if we got any data

    def parse_partial(self) -> PartialParseResult:
        """Parse with error recovery and return detailed results."""
        try:
            self.skip_whitespace_and_newlines()
            data, success = self.parse_value_with_recovery()

            self.result.data = data
            self.result.calculate_success_rate()

            return self.result

        except Exception as e:
            error = self.create_error(f"Fatal parsing error: {str(e)}", "fatal_error")
            self.result.add_error(error)
            self.result.calculate_success_rate()
            return self.result


def parse_partial(
    text: str,
    recovery_level: RecoveryLevel = RecoveryLevel.SKIP_FIELDS,
    config: Optional[ParseConfig] = None,
) -> PartialParseResult:
    """
    Parse JSON with error recovery, returning partial results and error details.

    Args:
        text: JSON string to parse
        recovery_level: Level of error recovery to attempt
        config: Optional parsing configuration

    Returns:
        PartialParseResult with data, errors, and recovery information
    """
    if config is None:
        config = ParseConfig(include_position=True, include_context=True)

    from ..core.transformer import JSONPreprocessor

    preprocessed_text = JSONPreprocessor.preprocess(
        text, aggressive=config.aggressive, config=config.preprocessing_config
    )

    lexer = Lexer(preprocessed_text)
    tokens = lexer.get_all_tokens()

    # Create error reporter
    error_reporter = (
        ErrorReporter(text, config.max_error_context)
        if config.include_position
        else None
    )

    # Parse with recovery
    parser = PartialParser(tokens, config, recovery_level)
    if error_reporter:
        parser.set_error_reporter(error_reporter)

    return parser.parse_partial()


def extract_valid_data(text: str, config: Optional[ParseConfig] = None) -> Any:
    """
    Simple utility to extract any valid data from malformed JSON, ignoring errors.

    Args:
        text: JSON string to parse
        config: Optional parsing configuration

    Returns:
        Valid data extracted from the input, or None if nothing could be parsed
    """
    result = parse_partial(text, RecoveryLevel.EXTRACT_ALL, config)
    return result.data


def parse_with_fallback(
    text: str,
    recovery_level: RecoveryLevel = RecoveryLevel.SKIP_FIELDS,
    config: Optional[ParseConfig] = None,
) -> tuple[Any, list[PartialParseError]]:
    """
    Parse with recovery, returning data and errors as a tuple for convenience.

    Args:
        text: JSON string to parse
        recovery_level: Level of error recovery to attempt
        config: Optional parsing configuration

    Returns:
        Tuple of (parsed_data, errors_list)
    """
    result = parse_partial(text, recovery_level, config)
    return result.data, result.errors
