"""
Partial error parsing for jsonshiatsu - extract valid data even from malformed JSON.

This module implements resilient JSON parsing that continues processing despite
syntax errors, collecting valid data while reporting detailed error information.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from ..core.tokenizer import Lexer, Position, Token, TokenType
from ..core.transformer import JSONPreprocessor
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
class ErrorLocation:
    """Location information for parsing errors."""
    path: str = ""  # JSONPath to error location
    line: int = 0  # Line number
    column: int = 0  # Column number

@dataclass
class ErrorContext:
    """Context information for parsing errors."""
    context_before: str = ""  # Text before error
    context_after: str = ""  # Text after error

@dataclass
class RecoveryInfo:
    """Information about recovery attempts."""
    recovery_attempted: bool = False
    recovery_action: Optional[RecoveryAction] = None
    original_value: str = ""  # Original malformed content
    recovered_value: Any = None  # What was recovered (if any)

class PartialParseError:
    """Detailed error information for partial parsing."""

    def __init__(
        self,
        error_type: str = "",
        message: str = "",
        suggestion: str = "",
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        **kwargs: Any  # Backward compatibility arguments
    ):
        self.error_type = error_type
        self.message = message
        self.suggestion = suggestion
        self.severity = severity
        self.location = ErrorLocation()
        self.context = ErrorContext()
        self.recovery = RecoveryInfo()

        # Handle backward compatibility args
        self._init_from_kwargs(kwargs)

    def _init_from_kwargs(self, kwargs: dict[str, Any]) -> None:
        """Initialize from keyword arguments for backward compatibility."""
        # Location args
        if 'path' in kwargs:
            self.location.path = kwargs['path']
        if 'line' in kwargs:
            self.location.line = kwargs['line']
        if 'column' in kwargs:
            self.location.column = kwargs['column']

        # Context args
        if 'context_before' in kwargs:
            self.context.context_before = kwargs['context_before']
        if 'context_after' in kwargs:
            self.context.context_after = kwargs['context_after']

        # Recovery args
        if 'recovery_attempted' in kwargs:
            self.recovery.recovery_attempted = kwargs['recovery_attempted']
        if 'recovery_action' in kwargs:
            self.recovery.recovery_action = kwargs['recovery_action']
        if 'original_value' in kwargs:
            self.recovery.original_value = kwargs['original_value']
        if 'recovered_value' in kwargs:
            self.recovery.recovered_value = kwargs['recovered_value']

    # Backward compatibility properties
    @property
    def path(self) -> str:
        """Get JSONPath to error location."""
        return self.location.path

    @path.setter
    def path(self, value: str) -> None:
        """Set JSONPath to error location."""
        self.location.path = value

    @property
    def line(self) -> int:
        """Get line number of error."""
        return self.location.line

    @line.setter
    def line(self, value: int) -> None:
        """Set line number of error."""
        self.location.line = value

    @property
    def column(self) -> int:
        """Get column number of error."""
        return self.location.column

    @column.setter
    def column(self, value: int) -> None:
        """Set column number of error."""
        self.location.column = value

    @property
    def context_before(self) -> str:
        """Get text before error."""
        return self.context.context_before

    @context_before.setter
    def context_before(self, value: str) -> None:
        """Set text before error."""
        self.context.context_before = value

    @property
    def context_after(self) -> str:
        """Get text after error."""
        return self.context.context_after

    @context_after.setter
    def context_after(self, value: str) -> None:
        """Set text after error."""
        self.context.context_after = value

    @property
    def recovery_attempted(self) -> bool:
        """Get whether recovery was attempted."""
        return self.recovery.recovery_attempted

    @recovery_attempted.setter
    def recovery_attempted(self, value: bool) -> None:
        """Set whether recovery was attempted."""
        self.recovery.recovery_attempted = value

    @property
    def recovery_action(self) -> Optional[RecoveryAction]:
        """Get recovery action taken."""
        return self.recovery.recovery_action

    @recovery_action.setter
    def recovery_action(self, value: Optional[RecoveryAction]) -> None:
        """Set recovery action taken."""
        self.recovery.recovery_action = value

    @property
    def original_value(self) -> str:
        """Get original malformed content."""
        return self.recovery.original_value

    @original_value.setter
    def original_value(self, value: str) -> None:
        """Set original malformed content."""
        self.recovery.original_value = value

    @property
    def recovered_value(self) -> Any:
        """Get recovered value."""
        return self.recovery.recovered_value

    @recovered_value.setter
    def recovered_value(self, value: Any) -> None:
        """Set recovered value."""
        self.recovery.recovered_value = value


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


@dataclass
class ParserState:
    """Current state of the parser."""
    pos: int = 0
    current_path: list[str] = field(default_factory=list)
    in_recovery_mode: bool = False
    recovery_depth: int = 0

@dataclass
class ParserConfig:
    """Parser configuration and dependencies."""
    tokens: list[Token] = field(default_factory=list)
    config: Optional[ParseConfig] = None
    recovery_level: RecoveryLevel = RecoveryLevel.SKIP_FIELDS
    validator: Optional[LimitValidator] = None
    error_reporter: Optional[ErrorReporter] = None


class PartialParser:
    """Parser that can recover from errors and extract partial data."""

    def __init__(
        self,
        tokens: list[Token],
        config: ParseConfig,
        recovery_level: RecoveryLevel = RecoveryLevel.SKIP_FIELDS,
    ):
        self.parser_config = ParserConfig(
            tokens=tokens,
            config=config,
            recovery_level=recovery_level,
            validator=LimitValidator(config.limits) if config.limits else None
        )
        self.state = ParserState()
        self.result = PartialParseResult()

    # Properties for backward compatibility
    @property
    def tokens(self) -> list[Token]:
        """Get token list."""
        return self.parser_config.tokens

    @property
    def tokens_length(self) -> int:
        """Get token list length."""
        return len(self.parser_config.tokens)

    @property
    def pos(self) -> int:
        """Get current position."""
        return self.state.pos

    @pos.setter
    def pos(self, value: int) -> None:
        """Set current position."""
        self.state.pos = value

    @property
    def config(self) -> ParseConfig:
        """Get parse configuration."""
        return self.parser_config.config  # type: ignore

    @property
    def recovery_level(self) -> RecoveryLevel:
        """Get recovery level."""
        return self.parser_config.recovery_level

    @property
    def validator(self) -> Optional[LimitValidator]:
        """Get limit validator."""
        return self.parser_config.validator

    @property
    def current_path(self) -> list[str]:
        """Get current JSONPath."""
        return self.state.current_path

    @current_path.setter
    def current_path(self, value: list[str]) -> None:
        """Set current JSONPath."""
        self.state.current_path = value

    @property
    def error_reporter(self) -> Optional[ErrorReporter]:
        """Get error reporter."""
        return self.parser_config.error_reporter

    @property
    def in_recovery_mode(self) -> bool:
        """Get recovery mode status."""
        return self.state.in_recovery_mode

    @in_recovery_mode.setter
    def in_recovery_mode(self, value: bool) -> None:
        """Set recovery mode status."""
        self.state.in_recovery_mode = value

    @property
    def recovery_depth(self) -> int:
        """Get recovery depth."""
        return self.state.recovery_depth

    @recovery_depth.setter
    def recovery_depth(self, value: int) -> None:
        """Set recovery depth."""
        self.state.recovery_depth = value

    def set_error_reporter(self, error_reporter: ErrorReporter) -> None:
        """Set error reporter for enhanced error information."""
        self.parser_config.error_reporter = error_reporter

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

        recovery_map = {
            "missing_quotes": self._recover_missing_quotes,
            "trailing_comma": self._recover_trailing_comma,
            "missing_colon": self._recover_missing_colon,
            "unclosed_string": self._recover_unclosed_string,
            "invalid_value": self._recover_invalid_value,
        }

        recovery_func = recovery_map.get(error.error_type)
        if recovery_func:
            return recovery_func(error)

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
            return self._parse_token_with_recovery(token)
        except (ValueError, TypeError, AttributeError) as e:
            error = self.create_error(f"Parse error: {str(e)}", "parse_exception")
            self.result.add_error(error)
            self.skip_to_recovery_point()
            return None, False

    def _parse_token_with_recovery(self, token: Token) -> tuple[Any, bool]:
        """Parse individual token types with recovery."""
        token_parsers = {
            TokenType.STRING: self._parse_string_token,
            TokenType.NUMBER: self._parse_number_token,
            TokenType.BOOLEAN: self._parse_boolean_token,
            TokenType.NULL: self._parse_null_token,
            TokenType.IDENTIFIER: self._parse_identifier_token,
            TokenType.LBRACE: lambda t: self.parse_object_with_recovery(),
            TokenType.LBRACKET: lambda t: self.parse_array_with_recovery(),
        }

        parser = token_parsers.get(token.type)
        if parser:
            return parser(token)

        error = self.create_error(f"Unexpected token: {token.type}", "syntax_error")
        self.result.add_error(error)
        self.advance()
        return None, False

    def _parse_string_token(self, token: Token) -> tuple[Any, bool]:
        """Parse string token with validation."""
        if self.validator:
            self.validator.validate_string_length(token.value)
        self.advance()
        self.result.successful_fields += 1
        return token.value, True

    def _parse_number_token(self, token: Token) -> tuple[Any, bool]:
        """Parse number token with validation and recovery."""
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

    def _parse_boolean_token(self, token: Token) -> tuple[Any, bool]:
        """Parse boolean token."""
        self.advance()
        self.result.successful_fields += 1
        return token.value == "true", True

    def _parse_null_token(self, token: Token) -> tuple[Any, bool]:
        """Parse null token."""
        _ = token  # Token parameter used for consistency in parser interface
        self.advance()
        self.result.successful_fields += 1
        return None, True

    def _parse_identifier_token(self, token: Token) -> tuple[Any, bool]:
        """Parse identifier token with recovery."""
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
        self.advance()
        return None, False

    def parse_object_with_recovery(self) -> tuple[dict[str, Any], bool]:
        """Parse an object with error recovery."""
        self.skip_whitespace_and_newlines()

        if not self._validate_object_start():
            return {}, False

        if self.validator:
            self.validator.enter_structure()

        self.advance()
        self.skip_whitespace_and_newlines()

        # Handle empty object
        if self._is_empty_object():
            if self.validator:
                self.validator.exit_structure()
            self.result.successful_fields += 1
            return {}, True

        obj, obj_success = self._parse_object_content()
        self._finalize_object_parsing(obj_success)

        if obj_success and obj:
            self.result.successful_fields += 1

        return obj, obj_success or bool(obj)

    def _validate_object_start(self) -> bool:
        """Validate object opening brace."""
        current_token = self.current_token()
        if not current_token or current_token.type != TokenType.LBRACE:
            error = self.create_error("Expected '{'", "syntax_error")
            self.result.add_error(error)
            return False
        return True

    def _is_empty_object(self) -> bool:
        """Check if object is empty."""
        current_token = self.current_token()
        return bool(
            current_token is not None and current_token.type == TokenType.RBRACE
        )

    def _parse_object_content(self) -> tuple[dict[str, Any], bool]:
        """Parse object key-value pairs."""
        obj: dict[str, Any] = {}
        obj_success = True

        while True:
            current_token = self.current_token()
            if not current_token or current_token.type == TokenType.RBRACE:
                break

            key_success, key, value_success, value = (
                self._parse_object_pair_with_recovery()
            )

            if key_success and key is not None and value_success:
                obj[key] = value

            if not self._handle_object_separator():
                obj_success = False
                break

        return obj, obj_success

    def _handle_object_separator(self) -> bool:
        """Handle comma/end of object. Returns True to continue, False to break."""
        self.skip_whitespace_and_newlines()
        current = self.current_token()

        if not current:
            error = self.create_error(
                "Unexpected end of input in object", "unclosed_object"
            )
            self.result.add_error(error)
            return False

        if current.type == TokenType.COMMA:
            self.advance()
            self.skip_whitespace_and_newlines()
            return self._handle_trailing_comma()

        if current.type == TokenType.RBRACE:
            return False

        return self._handle_object_separator_error(current)

    def _handle_trailing_comma(self) -> bool:
        """Handle trailing comma in object."""
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
            return False
        return True

    def _handle_object_separator_error(self, current: Token) -> bool:
        """Handle error in object separator."""
        error = self.create_error(
            f"Expected ', ' or '}}' but found {current.type}",
            "syntax_error",
        )
        self.result.add_error(error)

        if self.recovery_level in [
            RecoveryLevel.SKIP_FIELDS,
            RecoveryLevel.BEST_EFFORT,
            RecoveryLevel.EXTRACT_ALL,
        ]:
            self.skip_to_recovery_point()
            return True
        return False

    def _finalize_object_parsing(self, obj_success: bool) -> None:
        """Finalize object parsing and validate closing brace."""
        _ = obj_success  # Parameter kept for future error handling extensions
        current_token = self.current_token()
        if current_token and current_token.type == TokenType.RBRACE:
            self.advance()
            if self.validator:
                self.validator.exit_structure()
        else:
            error = self.create_error("Expected '}' to close object", "unclosed_object")
            self.result.add_error(error)

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

        if not self._validate_array_start():
            return [], False

        if self.validator:
            self.validator.enter_structure()

        self.advance()
        self.skip_whitespace_and_newlines()

        # Handle empty array
        if self._is_empty_array():
            if self.validator:
                self.validator.exit_structure()
            self.result.successful_fields += 1
            return [], True

        arr, arr_success = self._parse_array_content()
        self._finalize_array_parsing(arr_success)

        if arr_success and arr:
            self.result.successful_fields += 1

        return arr, arr_success or bool(arr)

    def _validate_array_start(self) -> bool:
        """Validate array opening bracket."""
        current_token = self.current_token()
        if not current_token or current_token.type != TokenType.LBRACKET:
            error = self.create_error("Expected '['", "syntax_error")
            self.result.add_error(error)
            return False
        return True

    def _is_empty_array(self) -> bool:
        """Check if array is empty."""
        current_token = self.current_token()
        return bool(
            current_token is not None and current_token.type == TokenType.RBRACKET
        )

    def _parse_array_content(self) -> tuple[list[Any], bool]:
        """Parse array elements."""
        arr: list[Any] = []
        arr_success = True
        element_index = 0

        while True:
            current_token = self.current_token()
            if not current_token or current_token.type == TokenType.RBRACKET:
                break

            if not self._parse_array_element(arr, element_index):
                arr_success = False
                break

            element_index += 1

        return arr, arr_success

    def _parse_array_element(self, arr: list[Any], element_index: int) -> bool:
        """Parse a single array element. Returns True to continue, False to break."""
        self.current_path.append(f"[{element_index}]")

        try:
            value, success = self.parse_value_with_recovery()

            if success:
                arr.append(value)
            elif self.recovery_level in [RecoveryLevel.EXTRACT_ALL]:
                arr.append(None)

            return self._handle_array_separator()
        finally:
            self.current_path.pop()

    def _handle_array_separator(self) -> bool:
        """Handle comma/end of array. Returns True to continue, False to break."""
        self.skip_whitespace_and_newlines()
        current = self.current_token()

        if not current:
            error = self.create_error(
                "Unexpected end of input in array", "unclosed_array"
            )
            self.result.add_error(error)
            return False

        if current.type == TokenType.COMMA:
            self.advance()
            self.skip_whitespace_and_newlines()
            return self._handle_array_trailing_comma()

        if current.type == TokenType.RBRACKET:
            return False

        return self._handle_array_separator_error(current)

    def _handle_array_trailing_comma(self) -> bool:
        """Handle trailing comma in array."""
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
            return False
        return True

    def _handle_array_separator_error(self, current: Token) -> bool:
        """Handle error in array separator."""
        error = self.create_error(
            f"Expected ', ' or ']' but found {current.type}",
            "syntax_error",
        )
        self.result.add_error(error)

        if self.recovery_level in [
            RecoveryLevel.SKIP_FIELDS,
            RecoveryLevel.BEST_EFFORT,
            RecoveryLevel.EXTRACT_ALL,
        ]:
            self.skip_to_recovery_point()
            return True
        return False

    def _finalize_array_parsing(self, arr_success: bool) -> None:
        """Finalize array parsing and validate closing bracket."""
        _ = arr_success  # Parameter kept for future error handling extensions
        current_token = self.current_token()
        if current_token and current_token.type == TokenType.RBRACKET:
            self.advance()
            if self.validator:
                self.validator.exit_structure()
        else:
            error = self.create_error("Expected ']' to close array", "unclosed_array")
            self.result.add_error(error)

    def parse_partial(self) -> PartialParseResult:
        """Parse with error recovery and return detailed results."""
        try:
            self.skip_whitespace_and_newlines()
            data, _ = self.parse_value_with_recovery()  # success unused for now

            self.result.data = data
            self.result.calculate_success_rate()

            return self.result

        except (ValueError, TypeError, AttributeError, RecursionError) as e:
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
