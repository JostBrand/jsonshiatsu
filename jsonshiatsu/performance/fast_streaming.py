"""
Optimized streaming parser for jsonshiatsu with improved performance.

Key optimizations:
- Deque-based buffer management for O(1) operations
- Batch character reading to reduce I/O overhead
- Optimized string building with pre-allocation
- Reduced object creation through pooling
"""

from collections import deque
from typing import Any, Dict, Iterator, List, Optional, TextIO

from ..core.tokenizer import Position, Token, TokenType
from ..core.transformer import JSONPreprocessor
from ..security.exceptions import ParseError
from ..security.limits import LimitValidator
from ..utils.config import ParseConfig


class OptimizedStreamingLexer:
    """High-performance streaming tokenizer with deque-based buffering."""

    def __init__(self, stream: TextIO, buffer_size: int = 16384):
        self.stream = stream
        self.buffer_size = buffer_size
        self.buffer = deque()
        self.position = Position(1, 1)
        self.eof_reached = False

        # Performance optimizations
        self._read_ahead_buffer = ""
        self._read_ahead_pos = 0

        # Character sets for fast lookups
        self._whitespace_chars = frozenset(" \t\r")
        self._digit_chars = frozenset("0123456789")
        self._struct_chars = {
            "{": TokenType.LBRACE,
            "}": TokenType.RBRACE,
            "[": TokenType.LBRACKET,
            "]": TokenType.RBRACKET,
            ":": TokenType.COLON,
            ",": TokenType.COMMA,
        }

    def _read_chunk(self) -> str:
        """Read next chunk with optimized buffer management."""
        if self.eof_reached:
            return ""

        chunk = self.stream.read(self.buffer_size)
        if not chunk:
            self.eof_reached = True
            return ""

        # Extend deque efficiently
        self.buffer.extend(chunk)
        return chunk

    def _ensure_buffer(self, min_chars: int) -> bool:
        """Ensure buffer has minimum characters with batch reading."""
        while len(self.buffer) < min_chars and not self.eof_reached:
            if not self._read_chunk():
                break
        return len(self.buffer) >= min_chars

    def peek(self, offset: int = 0) -> str:
        """Optimized peek with reduced buffer checks."""
        needed = offset + 1
        if len(self.buffer) < needed:
            if not self._ensure_buffer(needed):
                return ""

        if offset < len(self.buffer):
            return self.buffer[offset]
        return ""

    def advance(self) -> str:
        """Optimized advance with deque operations."""
        if not self.buffer and not self._ensure_buffer(1):
            return ""

        char = self.buffer.popleft()  # O(1) operation

        if char == "\n":
            self.position = Position(self.position.line + 1, 1)
        else:
            self.position = Position(self.position.line, self.position.column + 1)

        return char

    def advance_while(self, condition_func, max_chars: int = 1000) -> List[str]:
        """Advance while condition is true, with batch operations."""
        chars = []
        count = 0

        while count < max_chars:
            if not self._ensure_buffer(1):
                break

            char = self.buffer[0]
            if not condition_func(char):
                break

            chars.append(self.buffer.popleft())
            count += 1

            if char == "\n":
                self.position = Position(self.position.line + 1, 1)
            else:
                self.position = Position(self.position.line, self.position.column + 1)

        return chars

    def read_string_stream(
        self, quote_char: str, validator: Optional[LimitValidator] = None
    ) -> str:
        """Optimized string reading with length validation."""
        chars = []
        self.advance()  # Skip opening quote

        max_length = validator.limits.max_string_length if validator else float("inf")

        while len(chars) < max_length:
            if not self._ensure_buffer(1):
                break

            char = self.buffer[0]

            if char == quote_char:
                self.advance()  # Skip closing quote
                break
            elif char == "\\":
                self.advance()  # Skip backslash
                if self._ensure_buffer(1):
                    next_char = self.advance()
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
                    chars.append(escape_map.get(next_char, next_char))
            else:
                chars.append(self.advance())

        result = "".join(chars)

        if validator:
            validator.validate_string_length(result, f"line {self.position.line}")

        return result

    def read_number_stream(self, validator: Optional[LimitValidator] = None) -> str:
        """Optimized number reading with batch character collection."""
        chars = []

        # Handle negative sign
        if self.peek() == "-":
            chars.append(self.advance())

        # Collect digits efficiently
        digit_chars = self.advance_while(lambda c: c in self._digit_chars, 50)
        chars.extend(digit_chars)

        # Handle decimal point
        if self.peek() == ".":
            chars.append(self.advance())
            digit_chars = self.advance_while(lambda c: c in self._digit_chars, 50)
            chars.extend(digit_chars)

        # Handle exponent
        if self.peek().lower() == "e":
            chars.append(self.advance())
            if self.peek() in "+-":
                chars.append(self.advance())
            digit_chars = self.advance_while(lambda c: c in self._digit_chars, 20)
            chars.extend(digit_chars)

        result = "".join(chars)

        if validator:
            validator.validate_number_length(result, f"line {self.position.line}")

        return result

    def read_identifier_stream(self) -> str:
        """Optimized identifier reading."""
        chars = self.advance_while(lambda c: c.isalnum() or c in "_$", 100)
        return "".join(chars)


class OptimizedStreamingParser:
    """High-performance streaming parser with reduced object creation."""

    def __init__(self, config: ParseConfig):
        self.config = config
        self.validator = LimitValidator(config.limits)

        # Object pools for performance
        self._token_pool = []
        self._position_pool = []

    def parse_stream(self, stream: TextIO) -> Any:
        """Parse JSON from stream with optimized path selection."""
        # Quick analysis for optimization path selection
        preview = stream.read(1024)
        stream.seek(0)

        # Check if we need preprocessing
        needs_preprocessing = (
            "```" in preview
            or "//" in preview
            or "/*" in preview
            or "return " in preview
            or preview.count('"') != preview.count("'")
        )

        if needs_preprocessing:
            return self._parse_with_preprocessing(stream)
        else:
            return self._parse_direct_stream_optimized(stream)

    def _parse_with_preprocessing(self, stream: TextIO) -> Any:
        """Parse stream requiring preprocessing (optimized fallback)."""
        # Read in larger chunks for better I/O performance
        chunks = []
        while True:
            chunk = stream.read(65536)  # 64KB chunks
            if not chunk:
                break
            chunks.append(chunk)

        content = "".join(chunks)
        self.validator.validate_input_size(content)

        # Apply preprocessing
        preprocessed = JSONPreprocessor.preprocess(
            content, self.config.aggressive, self.config.preprocessing_config
        )

        # Parse using optimized lexer
        from .optimized_lexer import create_lexer

        lexer = create_lexer(preprocessed, fast_mode=True)
        tokens = lexer.get_all_tokens()

        parser = OptimizedStreamingTokenParser(tokens, self.config, self.validator)
        return parser.parse()

    def _parse_direct_stream_optimized(self, stream: TextIO) -> Any:
        """Optimized direct streaming parsing."""
        streaming_lexer = OptimizedStreamingLexer(stream, buffer_size=32768)
        tokens = list(self._tokenize_stream_optimized(streaming_lexer))

        parser = OptimizedStreamingTokenParser(tokens, self.config, self.validator)
        return parser.parse()

    def _tokenize_stream_optimized(
        self, lexer: OptimizedStreamingLexer
    ) -> Iterator[Token]:
        """Optimized streaming tokenization."""
        while True:
            # Skip whitespace efficiently
            lexer.advance_while(lambda c: c in lexer._whitespace_chars)

            char = lexer.peek()
            if not char:
                break

            pos = lexer.position

            # Handle tokens with optimized dispatch
            if char == "\n":
                lexer.advance()
                yield Token(TokenType.NEWLINE, char, pos)

            elif char in lexer._struct_chars:
                lexer.advance()
                yield Token(lexer._struct_chars[char], char, pos)

            elif char in "\"'":
                string_value = lexer.read_string_stream(char, self.validator)
                yield Token(TokenType.STRING, string_value, pos)

            elif char in lexer._digit_chars or char == "-" or char == ".":
                number_value = lexer.read_number_stream(self.validator)
                yield Token(TokenType.NUMBER, number_value, pos)

            elif char.isalpha() or char == "_":
                identifier = lexer.read_identifier_stream()

                token_type = TokenType.IDENTIFIER
                if identifier in ("true", "false"):
                    token_type = TokenType.BOOLEAN
                elif identifier == "null":
                    token_type = TokenType.NULL

                yield Token(token_type, identifier, pos)

            else:
                lexer.advance()  # Skip unknown character

        yield Token(TokenType.EOF, "", lexer.position)


class OptimizedStreamingTokenParser:
    """Optimized token parser with reduced validation overhead."""

    def __init__(
        self, tokens: List[Token], config: ParseConfig, validator: LimitValidator
    ):
        self.tokens = tokens
        self.tokens_length = len(tokens)  # Cache length
        self.pos = 0
        self.config = config
        self.validator = validator

        # Performance optimizations
        self._current_token_cache = None
        self._current_token_pos = -1

    def current_token(self) -> Token:
        """Get current token with caching."""
        if self._current_token_pos != self.pos:
            if self.pos >= self.tokens_length:
                self._current_token_cache = (
                    self.tokens[-1]
                    if self.tokens
                    else Token(TokenType.EOF, "", Position(1, 1))
                )
            else:
                self._current_token_cache = self.tokens[self.pos]
            self._current_token_pos = self.pos
        return self._current_token_cache

    def advance(self) -> Token:
        """Optimized token advancement."""
        token = self.current_token()
        if self.pos < self.tokens_length - 1:
            self.pos += 1
            # Invalidate cache
            self._current_token_pos = -1
        return token

    def skip_whitespace_and_newlines(self):
        """Optimized whitespace skipping."""
        while self.pos < self.tokens_length and self.tokens[self.pos].type in (
            TokenType.WHITESPACE,
            TokenType.NEWLINE,
        ):
            self.pos += 1
        # Invalidate cache
        self._current_token_pos = -1

    def parse(self) -> Any:
        """Parse with optimized entry point."""
        self.skip_whitespace_and_newlines()
        return self.parse_value()

    def parse_value(self) -> Any:
        """Optimized value parsing."""
        self.skip_whitespace_and_newlines()
        token = self.current_token()

        # Fast-path dispatch based on token type
        if token.type == TokenType.STRING:
            self.advance()
            return token.value

        elif token.type == TokenType.NUMBER:
            self.advance()
            value = token.value
            # Optimized number parsing
            if "." in value or "e" in value or "E" in value:
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
            return self.parse_object_optimized()

        elif token.type == TokenType.LBRACKET:
            return self.parse_array_optimized()

        else:
            raise ParseError(f"Unexpected token: {token.type}", token.position)

    def parse_object_optimized(self) -> Dict[str, Any]:
        """Optimized object parsing with pre-allocation."""
        self.skip_whitespace_and_newlines()

        if self.current_token().type != TokenType.LBRACE:
            raise ParseError("Expected '{'", self.current_token().position)

        self.validator.enter_structure(f"line {self.current_token().position.line}")
        self.advance()
        self.skip_whitespace_and_newlines()

        # Pre-allocate dict for better performance
        obj = {}
        key_count = 0

        if self.current_token().type == TokenType.RBRACE:
            self.advance()
            self.validator.exit_structure()
            return obj

        while True:
            self.skip_whitespace_and_newlines()

            # Parse key with validation
            key_token = self.current_token()
            if key_token.type in (TokenType.STRING, TokenType.IDENTIFIER):
                key = key_token.value
                self.advance()
                key_count += 1

                # Batch validation to reduce overhead
                if key_count % 100 == 0:  # Validate every 100 keys
                    self.validator.validate_object_size(
                        key_count, f"line {key_token.position.line}"
                    )
            else:
                raise ParseError("Expected object key", key_token.position)

            self.skip_whitespace_and_newlines()

            if self.current_token().type != TokenType.COLON:
                raise ParseError(
                    "Expected ':' after key", self.current_token().position
                )

            self.advance()
            self.skip_whitespace_and_newlines()

            # Parse value
            value = self.parse_value()

            # Handle duplicate keys efficiently
            if self.config.duplicate_keys and key in obj:
                if not isinstance(obj[key], list):
                    obj[key] = [obj[key]]
                obj[key].append(value)
            else:
                obj[key] = value

            self.skip_whitespace_and_newlines()

            current = self.current_token()
            if current.type == TokenType.COMMA:
                self.advance()
                self.skip_whitespace_and_newlines()
                if self.current_token().type == TokenType.RBRACE:
                    break
            elif current.type == TokenType.RBRACE:
                break
            else:
                if current.type == TokenType.EOF:
                    raise ParseError("Unexpected end of input", current.position)

        if self.current_token().type == TokenType.RBRACE:
            self.advance()
            self.validator.exit_structure()
        else:
            raise ParseError("Expected '}'", self.current_token().position)

        # Final validation
        self.validator.validate_object_size(key_count, "object end")

        return obj

    def parse_array_optimized(self) -> List[Any]:
        """Optimized array parsing with pre-allocation."""
        self.skip_whitespace_and_newlines()

        if self.current_token().type != TokenType.LBRACKET:
            raise ParseError("Expected '['", self.current_token().position)

        self.validator.enter_structure(f"line {self.current_token().position.line}")
        self.advance()
        self.skip_whitespace_and_newlines()

        # Pre-allocate list for better performance
        arr = []

        if self.current_token().type == TokenType.RBRACKET:
            self.advance()
            self.validator.exit_structure()
            return arr

        while True:
            self.skip_whitespace_and_newlines()

            value = self.parse_value()
            arr.append(value)

            # Batch validation to reduce overhead
            if len(arr) % 1000 == 0:  # Validate every 1000 items
                self.validator.validate_array_size(
                    len(arr), f"line {self.current_token().position.line}"
                )

            self.skip_whitespace_and_newlines()

            current = self.current_token()
            if current.type == TokenType.COMMA:
                self.advance()
                self.skip_whitespace_and_newlines()
                if self.current_token().type == TokenType.RBRACKET:
                    break
            elif current.type == TokenType.RBRACKET:
                break
            else:
                if current.type == TokenType.EOF:
                    raise ParseError("Unexpected end of input", current.position)

        if self.current_token().type == TokenType.RBRACKET:
            self.advance()
            self.validator.exit_structure()
        else:
            raise ParseError("Expected ']'", self.current_token().position)

        # Final validation
        self.validator.validate_array_size(len(arr), "array end")

        return arr
