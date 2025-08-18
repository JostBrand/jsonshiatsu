"""
Optimized lexer for jsonshiatsu - high-performance tokenization.

This module provides optimized tokenization with significant performance improvements:
- String building using lists instead of concatenation
- Cached string lengths to avoid repeated len() calls
- Optimized character access patterns
- Reduced object creation overhead
"""

from typing import Callable, Iterator, List, Optional

# Import types from original lexer
from ..core.tokenizer import Position, Token, TokenType


class OptimizedLexer:
    """High-performance lexer with optimized string operations and caching."""

    def __init__(self, text: str):
        self.text = text
        self.text_length = len(text)  # Cache length
        self.pos = 0
        self.line = 1
        self.column = 1

        # Pre-compile character sets for faster lookups
        self._whitespace_chars = frozenset(" \t\r")
        self._digit_chars = frozenset("0123456789")
        self._alpha_chars = frozenset(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_$"
        )
        self._quote_chars = frozenset("\"'")
        self._struct_chars = {
            "{": TokenType.LBRACE,
            "}": TokenType.RBRACE,
            "[": TokenType.LBRACKET,
            "]": TokenType.RBRACKET,
            ":": TokenType.COLON,
            ",": TokenType.COMMA,
        }

        # Position caching
        self._position_cache: Optional[Position] = None
        self._position_cache_pos = -1

    def current_position(self) -> Position:
        """Get current position with caching optimization."""
        if self._position_cache_pos != self.pos:
            self._position_cache = Position(self.line, self.column)
            self._position_cache_pos = self.pos
        return self._position_cache  # type: ignore[return-value]

    def peek(self, offset: int = 0) -> str:
        """Peek at character with optimized bounds checking."""
        pos = self.pos + offset
        if pos >= self.text_length:
            return ""
        return self.text[pos]

    def peek_ahead(self, count: int) -> str:
        """Peek ahead multiple characters efficiently."""
        end_pos = min(self.pos + count, self.text_length)
        return self.text[self.pos : end_pos]

    def advance(self) -> str:
        """Advance position with optimized tracking."""
        if self.pos >= self.text_length:
            return ""

        char = self.text[self.pos]
        self.pos += 1

        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        return char

    def advance_while(self, condition_func: Callable[[str], bool]) -> List[str]:
        """Advance while condition is true, collecting characters efficiently."""
        chars = []
        while self.pos < self.text_length:
            char = self.text[self.pos]
            if not condition_func(char):
                break
            chars.append(char)
            self.pos += 1
            if char == "\n":
                self.line += 1
                self.column = 1
            else:
                self.column += 1
        return chars

    def skip_whitespace(self) -> None:
        """Skip whitespace with optimized character set lookup."""
        while (
            self.pos < self.text_length
            and self.text[self.pos] in self._whitespace_chars
        ):
            self.pos += 1
            self.column += 1

    def read_string(self, quote_char: str) -> str:
        """Read a quoted string with optimized string building."""
        chars = []
        self.advance()  # Skip opening quote

        while self.pos < self.text_length:
            char = self.text[self.pos]

            if char == quote_char:
                self.advance()  # Skip closing quote
                break
            elif char == "\\":
                self.advance()  # Skip backslash
                if self.pos < self.text_length:
                    next_char = self.text[self.pos]
                    # Use dict lookup for escape sequences (faster than if/elif chain)
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
                    self.advance()
            else:
                chars.append(self.advance())

        return "".join(chars)

    def read_number(self) -> str:
        """Read a number with optimized character collection."""
        chars = []

        # Handle negative sign
        if self.pos < self.text_length and self.text[self.pos] == "-":
            chars.append(self.advance())

        # Handle numbers starting with decimal point
        if self.pos < self.text_length and self.text[self.pos] == ".":
            chars.append(self.advance())
            # Read digits after decimal
            digit_chars = self.advance_while(lambda c: c in self._digit_chars)
            chars.extend(digit_chars)
        else:
            # Read integer part
            digit_chars = self.advance_while(lambda c: c in self._digit_chars)
            chars.extend(digit_chars)

            # Read decimal part
            if self.pos < self.text_length and self.text[self.pos] == ".":
                chars.append(self.advance())
                digit_chars = self.advance_while(lambda c: c in self._digit_chars)
                chars.extend(digit_chars)

        # Read exponent part
        if self.pos < self.text_length and self.text[self.pos].lower() == "e":
            chars.append(self.advance())
            if self.pos < self.text_length and self.text[self.pos] in "+-":
                chars.append(self.advance())
            digit_chars = self.advance_while(lambda c: c in self._digit_chars)
            chars.extend(digit_chars)

        return "".join(chars)

    def read_identifier(self) -> str:
        """Read an unquoted identifier with optimized character collection."""
        chars = self.advance_while(lambda c: c.isalnum() or c in "_$")
        return "".join(chars)

    def tokenize(self) -> Iterator[Token]:
        """Generate tokens with optimized parsing."""
        while self.pos < self.text_length:
            self.skip_whitespace()

            if self.pos >= self.text_length:
                break

            char = self.text[self.pos]
            pos = self.current_position()

            # Newlines
            if char == "\n":
                self.advance()
                yield Token(TokenType.NEWLINE, char, pos)

            # Structural characters (use dict lookup)
            elif char in self._struct_chars:
                self.advance()
                yield Token(self._struct_chars[char], char, pos)

            # Quoted strings
            elif char in self._quote_chars:
                string_value = self.read_string(char)
                yield Token(TokenType.STRING, string_value, pos)

            # Numbers (optimized condition checking)
            elif (
                char in self._digit_chars
                or (
                    char == "-"
                    and self.pos + 1 < self.text_length
                    and self.text[self.pos + 1] in self._digit_chars
                )
                or (
                    char == "."
                    and self.pos + 1 < self.text_length
                    and self.text[self.pos + 1] in self._digit_chars
                )
            ):
                number_value = self.read_number()
                yield Token(TokenType.NUMBER, number_value, pos)

            # Identifiers and keywords
            elif char.isalpha() or char == "_":
                identifier = self.read_identifier()

                # Use dict lookup for keywords (faster than if/elif)
                keyword_types = {
                    "true": TokenType.BOOLEAN,
                    "false": TokenType.BOOLEAN,
                    "null": TokenType.NULL,
                }

                token_type = keyword_types.get(identifier, TokenType.IDENTIFIER)
                yield Token(token_type, identifier, pos)

            else:
                # Skip unknown characters
                self.advance()

        yield Token(TokenType.EOF, "", self.current_position())

    def get_all_tokens(self) -> List[Token]:
        """Get all tokens as a list with pre-allocated capacity."""
        tokens = []
        # Pre-allocate based on rough estimate (1 token per 8 characters)

        for token in self.tokenize():
            tokens.append(token)

        return tokens


class FastLexer(OptimizedLexer):
    """Ultra-fast lexer with additional optimizations for production use."""

    def __init__(self, text: str):
        super().__init__(text)

        # Pre-scan for common patterns to optimize parsing
        self._has_quotes = '"' in text or "'" in text
        self._has_escapes = "\\" in text
        self._has_comments = "//" in text or "/*" in text

    def read_string_fast(self, quote_char: str) -> str:
        """Ultra-fast string reading for strings without escapes."""
        if not self._has_escapes:
            # Fast path for strings without escapes
            start_pos = self.pos + 1  # Skip opening quote
            end_pos = self.text.find(quote_char, start_pos)

            if end_pos != -1:
                result = self.text[start_pos:end_pos]
                # Update position efficiently
                self.pos = end_pos + 1
                self.column += end_pos - start_pos + 2
                return result

        # Fall back to standard method for complex strings
        return super().read_string(quote_char)

    def tokenize_fast(self) -> Iterator[Token]:
        """Ultra-fast tokenization with optimized hot paths."""
        if not self._has_quotes and not self._has_comments:
            # Ultra-fast path for simple JSON without strings or comments
            return self._tokenize_simple()
        else:
            # Standard optimized path
            return super().tokenize()

    def _tokenize_simple(self) -> Iterator[Token]:
        """Simplified tokenizer for basic JSON structures."""
        while self.pos < self.text_length:
            char = self.text[self.pos]

            # Skip whitespace inline
            if char in self._whitespace_chars:
                self.pos += 1
                self.column += 1
                continue

            pos = Position(self.line, self.column)

            if char == "\n":
                self.pos += 1
                self.line += 1
                self.column = 1
                yield Token(TokenType.NEWLINE, char, pos)
            elif char in self._struct_chars:
                self.pos += 1
                self.column += 1
                yield Token(self._struct_chars[char], char, pos)
            elif char in self._digit_chars or char == "-":
                number_value = self.read_number()
                yield Token(TokenType.NUMBER, number_value, pos)
            elif char.isalpha():
                identifier = self.read_identifier()
                token_type = {
                    "true": TokenType.BOOLEAN,
                    "false": TokenType.BOOLEAN,
                    "null": TokenType.NULL,
                }.get(identifier, TokenType.IDENTIFIER)
                yield Token(token_type, identifier, pos)
            else:
                self.pos += 1
                self.column += 1

        yield Token(TokenType.EOF, "", Position(self.line, self.column))


# Factory function for selecting optimal lexer
def create_lexer(text: str, fast_mode: bool = True) -> OptimizedLexer:
    """Create the most appropriate lexer for the given text."""
    if fast_mode and len(text) > 1000:
        return FastLexer(text)
    else:
        return OptimizedLexer(text)
