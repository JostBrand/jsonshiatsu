"""
Common error handling utilities for JSON parsing.

This module provides centralized error collection, context building, and
error reporting functionality shared across different parsing strategies.
"""

from dataclasses import dataclass
from typing import Any, Optional

from ..security.exceptions import ParseError


@dataclass
class ErrorContext:
    """Context information for parsing errors."""

    position: int
    line: int
    column: int
    context_text: str
    original_text: Optional[str] = None


@dataclass
class RecoveryStats:
    """Statistics about recovery attempts and success rates."""

    attempted_recoveries: int = 0
    successful_recoveries: int = 0
    skipped_values: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate the recovery success rate."""
        if self.attempted_recoveries == 0:
            return 0.0
        return (self.successful_recoveries / self.attempted_recoveries) * 100.0


class ErrorCollector:
    """Collects and manages parsing errors during recovery operations."""

    def __init__(self, max_errors: int = 100):
        self.errors: list[ParseError] = []
        self.max_errors = max_errors
        self.stats = RecoveryStats()

    def add_error(self, error: ParseError) -> None:
        """Add an error to the collection."""
        if len(self.errors) < self.max_errors:
            self.errors.append(error)

    def should_continue(self) -> bool:
        """Determine if parsing should continue based on error count."""
        return len(self.errors) < self.max_errors

    def clear(self) -> None:
        """Clear all collected errors."""
        self.errors.clear()
        self.stats = RecoveryStats()


class ErrorContextBuilder:
    """Builds error context information from parsing state."""

    @staticmethod
    def build_context(
        position: int, original_text: str, context_length: int = 50
    ) -> ErrorContext:
        """Build error context from position and original text."""
        if not original_text:
            return ErrorContext(
                position=position,
                line=1,
                column=position + 1,
                context_text="",
                original_text=original_text,
            )

        # Calculate line and column
        line = original_text[:position].count("\n") + 1
        line_start = original_text.rfind("\n", 0, position) + 1
        column = position - line_start + 1

        # Extract context text
        start = max(0, position - context_length // 2)
        end = min(len(original_text), position + context_length // 2)
        context_text = original_text[start:end]

        return ErrorContext(
            position=position,
            line=line,
            column=column,
            context_text=context_text,
            original_text=original_text,
        )

    @staticmethod
    def build_context_from_handler(handler: Any, original_text: str) -> ErrorContext:
        """Build error context from a token handler."""
        try:
            # Try to get position from current token
            token = handler.current_token()
            position = getattr(token, "position", 0)
        except (AttributeError, TypeError, ValueError):
            position = 0

        return ErrorContextBuilder.build_context(position, original_text)


class ErrorReporterImpl:
    """Default implementation of error reporting."""

    def __init__(self, original_text: str = "", include_context: bool = True):
        self.original_text = original_text
        self.include_context = include_context

    def report_error(self, _message: str, position: int, context: str = "") -> None:
        """Report a parsing error (for logging/debugging)."""
        if self.include_context and not context and self.original_text:
            error_context = ErrorContextBuilder.build_context(
                position, self.original_text
            )
            context = f"Line {error_context.line}, Column {error_context.column}"

        # This could be extended to log to a logger
        # For now, we simply acknowledge the error without action

    def create_parse_error(self, message: str, position: int) -> ParseError:
        """Create a ParseError with appropriate context."""
        if self.include_context and self.original_text:
            error_context = ErrorContextBuilder.build_context(
                position, self.original_text
            )
            full_message = (
                f"{message} at line {error_context.line}, column {error_context.column}"
            )
            if error_context.context_text.strip():
                full_message += f": {error_context.context_text.strip()}"
            return ParseError(full_message)

        return ParseError(message)
