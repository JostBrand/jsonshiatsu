"""
Enhanced error reporting for jsonshiatsu.

This module provides detailed error information with position tracking and context.
"""

from dataclasses import dataclass
from typing import Optional

from ..core.tokenizer import Position


@dataclass
class ErrorContext:
    """Context information around an error location."""

    text: str  # The original text
    position: Position  # Error position
    context_before: str  # Text before error
    context_after: str  # Text after error
    error_char: str  # Character at error position
    line_text: str  # Full line containing error
    column_indicator: str  # Visual indicator of error column


class jsonshiatsuError(Exception):
    """Base exception for jsonshiatsu with enhanced error reporting."""

    def __init__(
        self,
        message: str,
        position: Optional[Position] = None,
        context: Optional[ErrorContext] = None,
        suggestions: Optional[list[str]] = None,
    ):
        self.message = message
        self.position = position
        self.context = context
        self.suggestions = suggestions or []
        super().__init__(self._format_error())

    def _format_error(self) -> str:
        """Format the error message with context and suggestions."""
        lines = [self.message]

        if self.position:
            lines.append(
                f"  at line {self.position.line}, column {self.position.column}"
            )

        if self.context:
            lines.append("")
            lines.append("Context:")
            lines.append(f"  {self.context.line_text}")
            lines.append(f"  {self.context.column_indicator}")

            if self.context.context_before or self.context.context_after:
                lines.append("")
                lines.append("Surrounding text:")
                surrounding = (
                    f"{self.context.context_before}█{self.context.context_after}"
                )
                lines.append(f"  ...{surrounding}...")

        if self.suggestions:
            lines.append("")
            lines.append("Suggestions:")
            for suggestion in self.suggestions:
                lines.append(f"  • {suggestion}")

        return "\n".join(lines)


class ParseError(jsonshiatsuError):
    """Enhanced parse error with position and context."""

    pass


class SecurityError(jsonshiatsuError):
    """Security limit exceeded error."""

    pass


class JSONDecodeError(jsonshiatsuError):
    """JSON decode error for compatibility with standard json module."""

    pass


class ErrorReporter:
    """Generates detailed error reports with context."""

    def __init__(self, text: str, max_context: int = 50):
        self.text = text
        self.max_context = max_context
        self.lines = text.splitlines(keepends=True)

    def create_context(self, position: Position) -> ErrorContext:
        """Create error context for a given position."""
        # Get the line containing the error
        line_idx = max(0, position.line - 1)
        line_text = ""
        if line_idx < len(self.lines):
            line_text = self.lines[line_idx].rstrip("\n\r")

        # Create column indicator
        column_indicator = " " * max(0, position.column - 1) + "^"

        # Get character at error position
        error_char = ""
        text_pos = self._position_to_text_index(position)
        if 0 <= text_pos < len(self.text):
            error_char = self.text[text_pos]

        # Get context before and after
        start_pos = max(0, text_pos - self.max_context)
        end_pos = min(len(self.text), text_pos + self.max_context)

        context_before = self.text[start_pos:text_pos]
        context_after = self.text[text_pos + 1 : end_pos]

        return ErrorContext(
            text=self.text,
            position=position,
            context_before=context_before,
            context_after=context_after,
            error_char=error_char,
            line_text=line_text,
            column_indicator=column_indicator,
        )

    def _position_to_text_index(self, position: Position) -> int:
        """Convert line/column position to text index."""
        text_pos = 0
        current_line = 1
        current_col = 1

        for char in self.text:
            if current_line == position.line and current_col == position.column:
                return text_pos

            if char == "\n":
                current_line += 1
                current_col = 1
            else:
                current_col += 1

            text_pos += 1

        return text_pos

    def create_parse_error(
        self, message: str, position: Position, suggestions: Optional[list[str]] = None
    ) -> ParseError:
        """Create a parse error with full context."""
        context = self.create_context(position)
        return ParseError(message, position, context, suggestions)

    def create_security_error(
        self,
        message: str,
        position: Optional[Position] = None,
        suggestions: Optional[list[str]] = None,
    ) -> SecurityError:
        """Create a security error with context if position is available."""
        context = None
        if position:
            context = self.create_context(position)
        return SecurityError(message, position, context, suggestions)


class ErrorSuggestionEngine:
    """Generates helpful suggestions for common JSON errors."""

    @staticmethod
    def suggest_for_unexpected_token(
        token_value: str, expected: Optional[str] = None
    ) -> list[str]:
        """Generate suggestions for unexpected token errors."""
        suggestions = []

        if expected:
            suggestions.append(f"Expected '{expected}' but found '{token_value}'")

        # Common fixes based on token
        if token_value in ['"', "'"]:
            suggestions.append("Check for unescaped quotes in strings")
            suggestions.append("Ensure quotes are properly paired")

        elif token_value == "}":
            suggestions.append("Check for missing comma between object properties")
            suggestions.append("Verify all object keys have values")

        elif token_value == "]":
            suggestions.append("Check for missing comma between array elements")
            suggestions.append("Verify array syntax is correct")

        elif token_value == ",":
            suggestions.append("Remove trailing comma if at end of object/array")
            suggestions.append("Check if comma placement is correct")

        return suggestions

    @staticmethod
    def suggest_for_unclosed_structure(structure_type: str) -> list[str]:
        """Generate suggestions for unclosed structures."""
        suggestions = []

        if structure_type == "object":
            suggestions.append("Add missing closing brace '}'")
            suggestions.append("Check for unmatched opening braces '{'")

        elif structure_type == "array":
            suggestions.append("Add missing closing bracket ']'")
            suggestions.append("Check for unmatched opening brackets '['")

        elif structure_type == "string":
            suggestions.append("Add missing closing quote")
            suggestions.append("Check for unescaped quotes in string content")

        suggestions.append("Enable aggressive mode for automatic structure completion")

        return suggestions

    @staticmethod
    def suggest_for_invalid_value(value: str) -> list[str]:
        """Generate suggestions for invalid values."""
        suggestions = []

        # Check for common mistakes
        if value.lower() in ["true", "false"]:
            suggestions.append(f"Use lowercase: '{value.lower()}'")

        elif value in ["True", "False"]:
            suggestions.append(f"Use JSON boolean: '{value.lower()}'")

        elif value == "None":
            suggestions.append("Use 'null' instead of 'None'")

        elif value == "undefined":
            suggestions.append("Use 'null' instead of 'undefined'")

        elif value.isalpha() and not value.startswith('"'):
            suggestions.append(f"Add quotes around string: '\"{value}\"'")

        return suggestions
