"""
Streaming JSON parser for handling large files.

This module provides streaming capabilities for parsing large JSON documents
without loading the entire content into memory.
"""

from collections.abc import Iterator
from typing import Any, NoReturn, TextIO

from ..core.constants import JSON_ESCAPE_MAP, get_structural_token_map
from ..core.parser_base import BaseParserMixin
from ..core.tokenizer import Position, Token, TokenType
from ..core.transformer import JSONPreprocessor
from ..security.exceptions import ErrorReporter, ParseError
from ..security.limits import LimitValidator

# Parser import moved to avoid circular imports
from ..utils.config import ParseConfig, ParseLimits


class StreamingLexer:
    """Streaming tokenizer that reads from a file-like object."""

    def __init__(self, stream: TextIO, buffer_size: int = 8192):
        self.stream = stream
        self.buffer_size = buffer_size
        self.buffer = ""
        self.position = Position(1, 1)
        self.eof_reached = False

    def _read_chunk(self) -> str:
        if self.eof_reached:
            return ""

        chunk = self.stream.read(self.buffer_size)
        if not chunk:
            self.eof_reached = True
        return chunk

    def _ensure_buffer(self, min_chars: int) -> bool:
        while len(self.buffer) < min_chars and not self.eof_reached:
            chunk = self._read_chunk()
            if not chunk:
                break
            self.buffer += chunk
        return len(self.buffer) >= min_chars

    def peek(self, offset: int = 0) -> str:
        """Peek at character at given offset without consuming it."""
        if not self._ensure_buffer(offset + 1):
            return ""

        if offset < len(self.buffer):
            return self.buffer[offset]
        return ""

    def advance(self) -> str:
        """Advance and return the next character."""
        if not self._ensure_buffer(1):
            return ""

        if not self.buffer:
            return ""

        char = self.buffer[0]
        self.buffer = self.buffer[1:]

        if char == "\n":
            self.position = Position(self.position.line + 1, 1)
        else:
            self.position = Position(self.position.line, self.position.column + 1)

        return char

    def current_position(self) -> Position:
        """Get current position in the stream."""
        return self.position


class StreamingParser:
    """Streaming parser for handling large JSON files without loading all into memory.

    This parser can handle both streaming and regular parsing modes depending on
    the input size and complexity of preprocessing needed.
    """

    def __init__(self, config: ParseConfig):
        self.config = config
        self.validator = LimitValidator(config.limits or ParseLimits())

    def parse_stream(self, stream: TextIO) -> Any:
        """Parse JSON from stream, choosing optimal strategy based on content."""
        initial_chunk = stream.read(self.config.streaming_threshold // 10)
        stream.seek(0)

        preprocessed_sample = JSONPreprocessor.preprocess(
            initial_chunk, self.config.aggressive, self.config.preprocessing_config
        )

        if (
            len(preprocessed_sample) != len(initial_chunk)
            or preprocessed_sample != initial_chunk
        ):
            return self._parse_with_preprocessing(stream)
        return self._parse_direct_stream(stream)

    def _parse_with_preprocessing(self, stream: TextIO) -> Any:
        content = stream.read()
        self.validator.validate_input_size(content)

        # Apply preprocessing
        preprocessed = JSONPreprocessor.preprocess(
            content, self.config.aggressive, self.config.preprocessing_config
        )

        # Import here to avoid circular imports
        from ..core.tokenizer import Lexer  # pylint: disable=import-outside-toplevel

        lexer = Lexer(preprocessed)
        tokens = lexer.get_all_tokens()
        parser = StreamingTokenParser(tokens, self.config, self.validator)
        return parser.parse()

    def _parse_direct_stream(self, stream: TextIO) -> Any:
        """Parse stream directly without full preprocessing."""
        streaming_lexer = StreamingLexer(stream)
        tokens = list(self._tokenize_stream(streaming_lexer))

        parser = StreamingTokenParser(tokens, self.config, self.validator)
        return parser.parse()

    def _tokenize_stream(self, lexer: StreamingLexer) -> Iterator[Token]:
        """Tokenize from streaming lexer."""
        while True:
            # Skip whitespace
            while lexer.peek() and lexer.peek() in " \t\r":
                lexer.advance()

            if not lexer.peek():
                break

            char = lexer.peek()
            pos = lexer.current_position()

            # Handle different token types
            if char == "\n":
                lexer.advance()
                yield Token(TokenType.NEWLINE, char, pos)

            elif char in "{}[],:":
                lexer.advance()
                token_map = get_structural_token_map()
                yield Token(token_map[char], char, pos)

            elif char in "\"'":
                string_value = self._read_string_stream(lexer, char)
                yield Token(TokenType.STRING, string_value, pos)

            elif char.isdigit() or char == "-" or char == ".":
                number_value = self._read_number_stream(lexer)
                yield Token(TokenType.NUMBER, number_value, pos)

            elif char.isalpha() or char == "_":
                identifier = self._read_identifier_stream(lexer)

                if identifier in ["true", "false"]:
                    yield Token(TokenType.BOOLEAN, identifier, pos)
                elif identifier == "null":
                    yield Token(TokenType.NULL, identifier, pos)
                else:
                    yield Token(TokenType.IDENTIFIER, identifier, pos)

            else:
                # Skip unknown character
                lexer.advance()

        yield Token(TokenType.EOF, "", lexer.current_position())

    def _read_string_stream(self, lexer: StreamingLexer, quote_char: str) -> str:
        """Read string from stream."""
        result = ""
        lexer.advance()

        while True:
            char = lexer.peek()
            if not char:
                break

            if char == quote_char:
                lexer.advance()
                break
            if char == "\\":
                lexer.advance()
                next_char = lexer.peek()
                if next_char:
                    result += JSON_ESCAPE_MAP.get(next_char, next_char)
                    lexer.advance()
            else:
                result += lexer.advance()

            # Validate string length as we build it
            self.validator.validate_string_length(result, f"line {lexer.position.line}")

        return result

    def _read_number_stream(self, lexer: StreamingLexer) -> str:
        """Read number from stream."""
        result = ""

        # Handle negative sign
        if lexer.peek() == "-":
            result += lexer.advance()

        # Read digits
        while lexer.peek() and (lexer.peek().isdigit() or lexer.peek() in ".eE+-"):
            result += lexer.advance()

            # Validate number length
            self.validator.validate_number_length(result, f"line {lexer.position.line}")

        return result

    def _read_identifier_stream(self, lexer: StreamingLexer) -> str:
        """Read identifier from stream."""
        result = ""
        while lexer.peek() and (lexer.peek().isalnum() or lexer.peek() in "_$"):
            result += lexer.advance()
        return result

    def can_stream_directly(self, stream: TextIO) -> bool:
        """Determine if stream can be parsed directly without preprocessing."""
        initial_chunk = stream.read(self.config.streaming_threshold // 10)
        stream.seek(0)

        preprocessed_sample = JSONPreprocessor.preprocess(
            initial_chunk, self.config.aggressive, self.config.preprocessing_config
        )

        return (
            len(preprocessed_sample) == len(initial_chunk)
            and preprocessed_sample == initial_chunk
        )


class StreamingTokenParser(BaseParserMixin):
    """Parser that works with streaming tokens and enforces limits."""

    def __init__(
        self, tokens: list[Token], config: ParseConfig, validator: LimitValidator
    ):
        self.tokens = tokens
        self.pos = 0
        self.config = config
        self.validator = validator
        self.error_reporter = None

        # Create error reporter if we have the original text
        if hasattr(config, "_original_text") and config._original_text is not None:
            self.error_reporter = ErrorReporter(
                config._original_text, config.max_error_context
            )

    def current_token(self) -> Token:
        """Get current token."""
        if self.pos >= len(self.tokens):
            return (
                self.tokens[-1]
                if self.tokens
                else Token(TokenType.EOF, "", Position(1, 1))
            )
        return self.tokens[self.pos]

    def advance(self) -> Token:
        """Advance to next token."""
        token = self.current_token()
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return token

    def skip_whitespace_and_newlines(self) -> None:
        """Skip whitespace and newline tokens."""
        while (
            self.current_token().type in [TokenType.WHITESPACE, TokenType.NEWLINE]
            and self.current_token().type != TokenType.EOF
        ):
            self.advance()

    def parse(self) -> Any:
        """Parse tokens into Python data structure."""
        self.skip_whitespace_and_newlines()
        return self.parse_value()

    def parse_value(self) -> Any:
        """Parse a JSON value with validation."""
        self.skip_whitespace_and_newlines()
        token = self.current_token()

        self.validator.count_item()

        # Use a mapping to reduce return statements
        token_handlers = {
            TokenType.STRING: lambda: self._handle_string_token(token),
            TokenType.NUMBER: lambda: self._handle_number_token(token),
            TokenType.BOOLEAN: lambda: self._handle_boolean_token(token),
            TokenType.NULL: lambda: self._handle_null_token(token),
            TokenType.IDENTIFIER: lambda: self._handle_identifier_token(token),
            TokenType.LBRACE: self.parse_object,
            TokenType.LBRACKET: self.parse_array,
        }

        handler = token_handlers.get(token.type)
        if handler:
            return handler()

        self._raise_parse_error(f"Unexpected token: {token.type}", token.position)

    def _handle_string_token(self, token: Token) -> str:
        """Handle string token parsing."""
        self.advance()
        return token.value

    def _handle_number_token(self, token: Token) -> Any:
        """Handle number token parsing."""
        self.advance()
        return self.parse_number_token(token)

    def _handle_boolean_token(self, token: Token) -> bool:
        """Handle boolean token parsing."""
        self.advance()
        return self.parse_boolean_token(token)

    def _handle_null_token(self, token: Token) -> Any:
        """Handle null token parsing."""
        self.advance()
        return self.parse_null_token(token)

    def _handle_identifier_token(self, token: Token) -> str:
        """Handle identifier token parsing."""
        self.advance()
        return token.value

    def parse_object(self) -> dict[str, Any]:
        """Parse object with size validation."""
        self._validate_object_start()

        self.validate_and_enter_structure(self.validator)
        self.advance()
        self.skip_whitespace_and_newlines()

        obj = self.init_empty_object()

        # Handle empty object
        if self.current_token().type == TokenType.RBRACE:
            self.advance()
            self.validate_and_exit_structure(self.validator)
            return obj

        # Parse object content
        key_count = 0
        while True:
            key = self._parse_object_key()
            key_count += 1
            self.validator.validate_object_keys(key_count)

            self._expect_colon()
            value = self.parse_value()
            self._handle_duplicate_key(obj, key, value)

            if not self._handle_object_continuation():
                break

        self._validate_object_end()
        return obj

    def _validate_object_start(self) -> None:
        """Validate object opening brace."""
        self.skip_whitespace_and_newlines()
        if self.current_token().type != TokenType.LBRACE:
            self._raise_parse_error("Expected '{'", self.current_token().position)

    def _parse_object_key(self) -> str:
        """Parse and validate object key."""
        self.skip_whitespace_and_newlines()
        key_token = self.current_token()

        if key_token.type not in [TokenType.STRING, TokenType.IDENTIFIER]:
            self._raise_parse_error("Expected object key", key_token.position)

        key = key_token.value
        self.advance()
        return key

    def _expect_colon(self) -> None:
        """Expect and consume colon token."""
        self.skip_whitespace_and_newlines()
        if self.current_token().type != TokenType.COLON:
            self._raise_parse_error(
                "Expected ':' after key", self.current_token().position
            )
        self.advance()
        self.skip_whitespace_and_newlines()

    def _handle_duplicate_key(self, obj: dict[str, Any], key: str, value: Any) -> None:
        """Handle duplicate key based on configuration."""
        self.handle_duplicate_key(obj, key, value, self.config.duplicate_keys)

    def _handle_object_continuation(self) -> bool:
        """Handle object continuation (comma or end). Returns True to continue parsing."""
        self.skip_whitespace_and_newlines()
        current_type = self.current_token().type

        if current_type == TokenType.COMMA:
            self.advance()
            self.skip_whitespace_and_newlines()
            return self.current_token().type != TokenType.RBRACE

        if current_type == TokenType.RBRACE:
            return False

        if current_type == TokenType.EOF:
            self._raise_parse_error(
                "Unexpected end of input, expected '}'",
                self.current_token().position,
            )
        return False

    def _validate_object_end(self) -> None:
        """Validate and consume object closing brace."""
        if self.current_token().type == TokenType.RBRACE:
            self.advance()
            self.validate_and_exit_structure(self.validator)
        else:
            self._raise_parse_error("Expected '}'", self.current_token().position)

    def parse_array(self) -> list[Any]:
        """Parse array with size validation."""
        self.skip_whitespace_and_newlines()

        if self.current_token().type != TokenType.LBRACKET:
            self._raise_parse_error("Expected '['", self.current_token().position)

        self.validate_and_enter_structure(self.validator)
        self.advance()
        self.skip_whitespace_and_newlines()

        arr = self.init_empty_array()

        if self.current_token().type == TokenType.RBRACKET:
            self.advance()
            self.validate_and_exit_structure(self.validator)
            return arr

        while True:
            self.skip_whitespace_and_newlines()

            value = self.parse_value()
            arr.append(value)

            self.validator.validate_array_items(len(arr))

            self.skip_whitespace_and_newlines()

            if self.current_token().type == TokenType.COMMA:
                self.advance()
                self.skip_whitespace_and_newlines()

                if self.current_token().type == TokenType.RBRACKET:
                    break
            if self.current_token().type == TokenType.RBRACKET:
                break
            if self.current_token().type == TokenType.EOF:
                self._raise_parse_error(
                    "Unexpected end of input, expected ']'",
                    self.current_token().position,
                )

        if self.current_token().type == TokenType.RBRACKET:
            self.advance()
            self.validate_and_exit_structure(self.validator)
        else:
            self._raise_parse_error("Expected ']'", self.current_token().position)

        return arr

    def _raise_parse_error(self, message: str, position: Position) -> NoReturn:
        """Raise a parse error with enhanced reporting if available."""
        if self.error_reporter:
            raise self.error_reporter.create_parse_error(message, position)
        raise ParseError(message, position)
