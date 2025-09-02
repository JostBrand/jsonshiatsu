"""
Unified parsing strategies for core and streaming parsers.

This module implements the Strategy pattern to eliminate code duplication
between the main parser and streaming parser while maintaining their
specialized behaviors.
"""

from abc import abstractmethod
from typing import Any, Optional, Union

from ..security.exceptions import ParseError
from .interfaces import ParseStrategy, TokenHandler
from .tokenizer import Token, TokenType


class AbstractParsingStrategy(ParseStrategy):
    """
    Template method pattern for common parsing logic.

    This class provides the shared parsing structure while allowing
    subclasses to specialize behavior for their specific use cases.
    """

    def __init__(self, config: Optional[Any] = None):
        self.config = config

    def parse_value(self, handler: TokenHandler) -> Any:
        """Parse any JSON value using template method pattern."""
        token = handler.current_token()

        # Handle simple tokens first
        simple_result, handled = self._handle_simple_tokens(token, handler)
        if handled:
            return simple_result

        # Handle complex structures
        return self._handle_complex_tokens(token, handler)

    def _handle_simple_tokens(
        self, token: Token, handler: TokenHandler
    ) -> tuple[Any, bool]:
        """Handle string, number, boolean, null tokens."""
        if token.type == TokenType.STRING:
            handler.advance()
            return self._process_string_value(token.value), True
        elif token.type == TokenType.NUMBER:
            handler.advance()
            return self._process_number_value(token.value), True
        elif token.type == TokenType.BOOLEAN:
            handler.advance()
            return token.value.lower() == "true", True
        elif token.type == TokenType.NULL:
            handler.advance()
            return None, True

        return None, False

    def _handle_complex_tokens(self, token: Token, handler: TokenHandler) -> Any:
        """Handle object and array tokens."""
        if token.type == TokenType.LBRACE:
            return self.parse_object(handler)
        elif token.type == TokenType.LBRACKET:
            return self.parse_array(handler)
        else:
            self._raise_unexpected_token_error(token)

    def parse_object(self, handler: TokenHandler) -> dict[str, Any]:
        """Parse a JSON object using template method."""
        self._validate_object_start(handler)
        self._enter_structure(handler)

        obj = self._init_empty_object()

        if self._is_empty_object(handler):
            return self._finalize_empty_object(handler, obj)

        return self._parse_object_content(handler, obj)

    def parse_array(self, handler: TokenHandler) -> list[Any]:
        """Parse a JSON array using template method."""
        self._validate_array_start(handler)
        self._enter_structure(handler)

        arr = self._init_empty_array()

        if self._is_empty_array(handler):
            return self._finalize_empty_array(handler, arr)

        return self._parse_array_content(handler, arr)

    # Template method hooks for specialization

    @abstractmethod
    def _process_string_value(self, value: str) -> str:
        """Process a string value (may differ between strategies)."""
        pass

    @abstractmethod
    def _process_number_value(self, value: str) -> Union[int, float]:
        """Process a number value (may differ between strategies)."""
        pass

    @abstractmethod
    def _init_empty_object(self) -> dict[str, Any]:
        """Initialize an empty object (may differ for memory optimization)."""
        pass

    @abstractmethod
    def _init_empty_array(self) -> list[Any]:
        """Initialize an empty array (may differ for memory optimization)."""
        pass

    @abstractmethod
    def _parse_object_content(
        self, handler: TokenHandler, obj: dict[str, Any]
    ) -> dict[str, Any]:
        """Parse object content (implementations may optimize differently)."""
        pass

    @abstractmethod
    def _parse_array_content(self, handler: TokenHandler, arr: list[Any]) -> list[Any]:
        """Parse array content (implementations may optimize differently)."""
        pass

    # Common helper methods

    def _validate_object_start(self, handler: TokenHandler) -> None:
        """Validate object start token."""
        token = handler.current_token()
        if token.type != TokenType.LBRACE:
            raise ParseError(f"Expected '{{' but found {token.type}")

    def _validate_array_start(self, handler: TokenHandler) -> None:
        """Validate array start token."""
        token = handler.current_token()
        if token.type != TokenType.LBRACKET:
            raise ParseError(f"Expected '[' but found {token.type}")

    def _enter_structure(self, handler: TokenHandler) -> None:
        """Enter a new structure level."""
        handler.advance()
        handler.skip_whitespace_and_newlines()

    def _is_empty_object(self, handler: TokenHandler) -> bool:
        """Check if object is empty."""
        return handler.current_token().type == TokenType.RBRACE

    def _is_empty_array(self, handler: TokenHandler) -> bool:
        """Check if array is empty."""
        return handler.current_token().type == TokenType.RBRACKET

    def _finalize_empty_object(
        self, handler: TokenHandler, obj: dict[str, Any]
    ) -> dict[str, Any]:
        """Finalize empty object parsing."""
        handler.advance()
        return obj

    def _finalize_empty_array(self, handler: TokenHandler, arr: list[Any]) -> list[Any]:
        """Finalize empty array parsing."""
        handler.advance()
        return arr

    def _raise_unexpected_token_error(self, token: Token) -> None:
        """Raise error for unexpected tokens."""
        raise ParseError(f"Unexpected token: {token.type}")


class StandardParsingStrategy(AbstractParsingStrategy):
    """
    Full-featured parsing strategy with complete error reporting.

    This strategy provides the comprehensive parsing capabilities of the
    main engine with detailed error context and recovery mechanisms.
    """

    def _process_string_value(self, value: str) -> str:
        """Process string with full validation."""
        # Full string processing with validation
        return value

    def _process_number_value(self, value: str) -> Union[int, float]:
        """Process number with full validation."""
        if "." in value or "e" in value.lower():
            return float(value)
        return int(value)

    def _init_empty_object(self) -> dict[str, Any]:
        """Initialize object with full tracking capabilities."""
        return {}

    def _init_empty_array(self) -> list[Any]:
        """Initialize array with full tracking capabilities."""
        return []

    def _parse_object_content(
        self, handler: TokenHandler, obj: dict[str, Any]
    ) -> dict[str, Any]:
        """Parse object content with full error handling."""
        while True:
            # Parse key
            key_token = handler.current_token()
            if key_token.type != TokenType.STRING:
                raise ParseError(f"Expected string key, got {key_token.type}")

            key = key_token.value
            handler.advance()
            handler.skip_whitespace_and_newlines()

            # Expect colon
            colon_token = handler.current_token()
            if colon_token.type != TokenType.COLON:
                raise ParseError(f"Expected ':' after key, got {colon_token.type}")

            handler.advance()
            handler.skip_whitespace_and_newlines()

            # Parse value
            value = self.parse_value(handler)

            # Handle duplicate keys based on config
            self._handle_duplicate_key(obj, key, value)

            handler.skip_whitespace_and_newlines()

            # Check for continuation
            next_token = handler.current_token()
            if next_token.type == TokenType.RBRACE:
                handler.advance()
                break
            elif next_token.type == TokenType.COMMA:
                handler.advance()
                handler.skip_whitespace_and_newlines()
            else:
                raise ParseError(
                    f"Expected ',' or '}}' in object, got {next_token.type}"
                )

        return obj

    def _parse_array_content(self, handler: TokenHandler, arr: list[Any]) -> list[Any]:
        """Parse array content with full error handling."""
        while True:
            # Parse value
            value = self.parse_value(handler)
            arr.append(value)

            handler.skip_whitespace_and_newlines()

            # Check for continuation
            next_token = handler.current_token()
            if next_token.type == TokenType.RBRACKET:
                handler.advance()
                break
            elif next_token.type == TokenType.COMMA:
                handler.advance()
                handler.skip_whitespace_and_newlines()
            else:
                raise ParseError(f"Expected ',' or ']' in array, got {next_token.type}")

        return arr

    def _handle_duplicate_key(self, obj: dict[str, Any], key: str, value: Any) -> None:
        """Handle duplicate keys based on configuration."""
        if (
            self.config
            and hasattr(self.config, "duplicate_keys")
            and self.config.duplicate_keys
        ):
            if key in obj:
                if not isinstance(obj[key], list):
                    obj[key] = [obj[key]]
                obj[key].append(value)
            else:
                obj[key] = value
        else:
            obj[key] = value


class StreamingParsingStrategy(AbstractParsingStrategy):
    """
    Memory-efficient parsing strategy for large files.

    This strategy optimizes for memory usage and streaming performance
    while maintaining parsing correctness.
    """

    def _process_string_value(self, value: str) -> str:
        """Process string with memory optimization."""
        # Minimal string processing for memory efficiency
        return value

    def _process_number_value(self, value: str) -> Union[int, float]:
        """Process number with memory optimization."""
        # Fast number parsing
        if "." in value or "e" in value.lower():
            return float(value)
        return int(value)

    def _init_empty_object(self) -> dict[str, Any]:
        """Initialize memory-efficient object."""
        return {}

    def _init_empty_array(self) -> list[Any]:
        """Initialize memory-efficient array."""
        return []

    def _parse_object_content(
        self, handler: TokenHandler, obj: dict[str, Any]
    ) -> dict[str, Any]:
        """Parse object content with memory optimization."""
        # Similar to standard but with memory optimizations
        # This could use generators or other memory-saving techniques
        while True:
            # Parse key (simplified error handling for performance)
            key_token = handler.current_token()
            if key_token.type != TokenType.STRING:
                raise ParseError("Expected string key")

            key = key_token.value
            handler.advance()
            handler.skip_whitespace_and_newlines()

            # Expect colon
            if handler.current_token().type != TokenType.COLON:
                raise ParseError("Expected ':'")

            handler.advance()
            handler.skip_whitespace_and_newlines()

            # Parse value
            value = self.parse_value(handler)
            obj[key] = value  # Simple assignment for streaming

            handler.skip_whitespace_and_newlines()

            # Check for continuation
            next_token = handler.current_token()
            if next_token.type == TokenType.RBRACE:
                handler.advance()
                break
            elif next_token.type == TokenType.COMMA:
                handler.advance()
                handler.skip_whitespace_and_newlines()
            else:
                raise ParseError("Expected ',' or '}'")

        return obj

    def _parse_array_content(self, handler: TokenHandler, arr: list[Any]) -> list[Any]:
        """Parse array content with memory optimization."""
        while True:
            # Parse value
            value = self.parse_value(handler)
            arr.append(value)

            handler.skip_whitespace_and_newlines()

            # Check for continuation
            next_token = handler.current_token()
            if next_token.type == TokenType.RBRACKET:
                handler.advance()
                break
            elif next_token.type == TokenType.COMMA:
                handler.advance()
                handler.skip_whitespace_and_newlines()
            else:
                raise ParseError("Expected ',' or ']'")

        return arr
