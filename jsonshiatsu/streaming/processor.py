"""
Streaming JSON parser for handling large files.

This module provides streaming capabilities for parsing large JSON documents
without loading the entire content into memory.
"""

from collections.abc import Iterator
from typing import Any, TextIO

from ..core.tokenizer import Position, Token, TokenType
from ..core.transformer import JSONPreprocessor
from ..security.exceptions import ErrorReporter, ParseError
from ..security.limits import LimitValidator

# Parser import moved to avoid circular imports
from ..utils.config import ParseConfig


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
        if not self._ensure_buffer(offset + 1):
            return ""

        if offset < len(self.buffer):
            return self.buffer[offset]
        return ""

    def advance(self) -> str:
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
        return self.position


class StreamingParser:
    def __init__(self, config: ParseConfig):
        self.config = config
        from ..utils.config import ParseLimits

        self.validator = LimitValidator(config.limits or ParseLimits())

    def parse_stream(self, stream: TextIO) -> Any:
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
        else:
            return self._parse_direct_stream(stream)

    def _parse_with_preprocessing(self, stream: TextIO) -> Any:
        content = stream.read()
        self.validator.validate_input_size(content)

        # Apply preprocessing
        preprocessed = JSONPreprocessor.preprocess(
            content, self.config.aggressive, self.config.preprocessing_config
        )

        from ..core.engine import parse

        return parse(
            preprocessed,
            fallback=self.config.fallback,
            duplicate_keys=self.config.duplicate_keys,
            aggressive=False,  # Already preprocessed
        )

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
                token_type = {
                    "{": TokenType.LBRACE,
                    "}": TokenType.RBRACE,
                    "[": TokenType.LBRACKET,
                    "]": TokenType.RBRACKET,
                    ":": TokenType.COLON,
                    ",": TokenType.COMMA,
                }[char]
                yield Token(token_type, char, pos)

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
            elif char == "\\":
                lexer.advance()
                next_char = lexer.peek()
                if next_char:
                    escape_map = {
                        "n": "\n",
                        "t": "\t",
                        "r": "\r",
                        "b": "\b",
                        "f": "\f",
                        '"': '"',
                        "'": "'",
                        "\\": "\\",
                        "/": "/",
                    }
                    result += escape_map.get(next_char, next_char)
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


class StreamingTokenParser:
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
        if hasattr(config, "_original_text"):
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

        if token.type == TokenType.STRING:
            self.advance()
            return token.value

        elif token.type == TokenType.NUMBER:
            self.advance()
            value = token.value
            if "." in value or "e" in value.lower():
                return float(value)
            return int(value)

        elif token.type == TokenType.BOOLEAN:
            self.advance()
            return token.value == "true"

        elif token.type == TokenType.NULL:
            self.advance()
            return None

        elif token.type == TokenType.IDENTIFIER:
            self.advance()
            return token.value

        elif token.type == TokenType.LBRACE:
            return self.parse_object()

        elif token.type == TokenType.LBRACKET:
            return self.parse_array()

        else:
            self._raise_parse_error(f"Unexpected token: {token.type}", token.position)

    def parse_object(self) -> dict[str, Any]:
        """Parse object with size validation."""
        self.skip_whitespace_and_newlines()

        if self.current_token().type != TokenType.LBRACE:
            self._raise_parse_error("Expected '{'", self.current_token().position)

        self.validator.enter_structure()
        self.advance()
        self.skip_whitespace_and_newlines()

        obj: dict[str, Any] = {}
        key_count = 0

        if self.current_token().type == TokenType.RBRACE:
            self.advance()
            self.validator.exit_structure()
            return obj

        while True:
            self.skip_whitespace_and_newlines()

            key_token = self.current_token()
            if key_token.type in [TokenType.STRING, TokenType.IDENTIFIER]:
                key = key_token.value
                self.advance()
                key_count += 1

                self.validator.validate_object_keys(key_count)
            else:
                self._raise_parse_error("Expected object key", key_token.position)

            self.skip_whitespace_and_newlines()

            if self.current_token().type != TokenType.COLON:
                self._raise_parse_error(
                    "Expected ':' after key", self.current_token().position
                )

            self.advance()
            self.skip_whitespace_and_newlines()

            value = self.parse_value()

            if key in obj and not self.config.duplicate_keys:
                obj[key] = value
            elif key in obj and self.config.duplicate_keys:
                if not isinstance(obj[key], list):
                    obj[key] = [obj[key]]
                obj[key].append(value)
            else:
                obj[key] = value

            self.skip_whitespace_and_newlines()

            if self.current_token().type == TokenType.COMMA:
                self.advance()
                self.skip_whitespace_and_newlines()

                if self.current_token().type == TokenType.RBRACE:
                    break
            elif self.current_token().type == TokenType.RBRACE:
                break
            else:
                if self.current_token().type == TokenType.EOF:
                    self._raise_parse_error(
                        "Unexpected end of input, expected '}'",
                        self.current_token().position,
                    )

        if self.current_token().type == TokenType.RBRACE:
            self.advance()
            self.validator.exit_structure()
        else:
            self._raise_parse_error("Expected '}'", self.current_token().position)

        return obj

    def parse_array(self) -> list[Any]:
        """Parse array with size validation."""
        self.skip_whitespace_and_newlines()

        if self.current_token().type != TokenType.LBRACKET:
            self._raise_parse_error("Expected '['", self.current_token().position)

        self.validator.enter_structure()
        self.advance()
        self.skip_whitespace_and_newlines()

        arr: list[Any] = []

        if self.current_token().type == TokenType.RBRACKET:
            self.advance()
            self.validator.exit_structure()
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
            elif self.current_token().type == TokenType.RBRACKET:
                break
            else:
                if self.current_token().type == TokenType.EOF:
                    self._raise_parse_error(
                        "Unexpected end of input, expected ']'",
                        self.current_token().position,
                    )

        if self.current_token().type == TokenType.RBRACKET:
            self.advance()
            self.validator.exit_structure()
        else:
            self._raise_parse_error("Expected ']'", self.current_token().position)

        return arr

    def _raise_parse_error(self, message: str, position: Position) -> None:
        """Raise a parse error with enhanced reporting if available."""
        if self.error_reporter:
            raise self.error_reporter.create_parse_error(message, position)
        else:
            raise ParseError(message, position)
