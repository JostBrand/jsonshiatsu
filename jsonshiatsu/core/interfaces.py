"""
Core interfaces and protocols for the JSON parsing system.

This module defines the contracts that different parsing components must implement,
enabling flexible composition and strategy patterns throughout the codebase.
"""

from abc import ABC, abstractmethod
from typing import Any, Protocol

from ..security.exceptions import ParseError
from .tokenizer import Token


class TokenHandler(Protocol):
    """Protocol for components that handle token stream operations."""

    def current_token(self) -> Token:
        """Get the current token without advancing."""
        ...

    def advance(self) -> None:
        """Move to the next token in the stream."""
        ...

    def skip_whitespace_and_newlines(self) -> None:
        """Skip whitespace and newline tokens."""
        ...


class StructureValidator(Protocol):
    """Protocol for components that validate JSON structure constraints."""

    def validate_and_enter_structure(self, validator: Any) -> None:
        """Validate and enter a new structural level (object/array)."""
        ...

    def validate_and_exit_structure(self, validator: Any) -> None:
        """Validate and exit the current structural level."""
        ...


class ParseStrategy(ABC):
    """Abstract strategy for parsing JSON values, objects, and arrays."""

    @abstractmethod
    def parse_value(self, handler: TokenHandler) -> Any:
        """Parse any JSON value (string, number, boolean, null, object, array)."""
        pass

    @abstractmethod
    def parse_object(self, handler: TokenHandler) -> dict[str, Any]:
        """Parse a JSON object."""
        pass

    @abstractmethod
    def parse_array(self, handler: TokenHandler) -> list[Any]:
        """Parse a JSON array."""
        pass


class PreprocessingStep(Protocol):
    """Protocol for preprocessing steps in the preprocessing pipeline."""

    def process(self, text: str, config: Any) -> str:
        """Process the input text according to this preprocessing step."""
        ...

    def should_apply(self, config: Any) -> bool:
        """Determine if this step should be applied given the configuration."""
        ...


class ErrorReporter(Protocol):
    """Protocol for error reporting and context building."""

    def report_error(self, message: str, position: int, context: str) -> None:
        """Report a parsing error with context."""
        ...

    def create_parse_error(self, message: str, position: int) -> ParseError:
        """Create a ParseError with appropriate context."""
        ...


class RecoveryStrategy(Protocol):
    """Protocol for error recovery strategies."""

    def can_recover(self, error: ParseError, context: Any) -> bool:
        """Determine if recovery is possible for the given error."""
        ...

    def attempt_recovery(self, error: ParseError, context: Any) -> Any:
        """Attempt to recover from the error and return a result."""
        ...
