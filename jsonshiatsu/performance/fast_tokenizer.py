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

    def __init__(self, text: str):
        self.text = text
        self.text_length = len(text)  # Cache length
        self.pos = 0
        self.line = 1
        self.column = 1

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

        self._position_cache: Optional[Position] = None
        self._position_cache_pos = -1

    def current_position(self) -> Position:
        if self._position_cache_pos != self.pos:
            self._position_cache = Position(self.line, self.column)
            self._position_cache_pos = self.pos
        assert self._position_cache is not None
        return self._position_cache

    def peek(self, offset: int = 0) -> str:
        pos = self.pos + offset
        if pos >= self.text_length:
            return ""
        return self.text[pos]

    def peek_ahead(self, count: int) -> str:
        end_pos = min(self.pos + count, self.text_length)
        return self.text[self.pos : end_pos]

    def advance(self) -> str:
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
        while (
            self.pos < self.text_length
            and self.text[self.pos] in self._whitespace_chars
        ):
            self.pos += 1
            self.column += 1

    def read_string(self, quote_char: str) -> str:
        chars = []
        self.advance()

        while self.pos < self.text_length:
            char = self.text[self.pos]

            if char == quote_char:
                self.advance()
                break
            elif char == "\\":
                self.advance()
                if self.pos < self.text_length:
                    next_char = self.text[self.pos]
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
        chars = []

        if self.pos < self.text_length and self.text[self.pos] == "-":
            chars.append(self.advance())

        if self.pos < self.text_length and self.text[self.pos] == ".":
            chars.append(self.advance())
            digit_chars = self.advance_while(lambda c: c in self._digit_chars)
            chars.extend(digit_chars)
        else:
            digit_chars = self.advance_while(lambda c: c in self._digit_chars)
            chars.extend(digit_chars)

            if self.pos < self.text_length and self.text[self.pos] == ".":
                chars.append(self.advance())
                digit_chars = self.advance_while(lambda c: c in self._digit_chars)
                chars.extend(digit_chars)

        if self.pos < self.text_length and self.text[self.pos].lower() == "e":
            chars.append(self.advance())
            if self.pos < self.text_length and self.text[self.pos] in "+-":
                chars.append(self.advance())
            digit_chars = self.advance_while(lambda c: c in self._digit_chars)
            chars.extend(digit_chars)

        return "".join(chars)

    def read_identifier(self) -> str:
        chars = self.advance_while(lambda c: c.isalnum() or c in "_$")
        return "".join(chars)

    def tokenize(self) -> Iterator[Token]:
        while self.pos < self.text_length:
            self.skip_whitespace()

            if self.pos >= self.text_length:
                break

            char = self.text[self.pos]
            pos = self.current_position()

            if char == "\n":
                self.advance()
                yield Token(TokenType.NEWLINE, char, pos)

            elif char in self._struct_chars:
                self.advance()
                yield Token(self._struct_chars[char], char, pos)

            elif char in self._quote_chars:
                string_value = self.read_string(char)
                yield Token(TokenType.STRING, string_value, pos)

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

            elif char.isalpha() or char == "_":
                identifier = self.read_identifier()

                keyword_types = {
                    "true": TokenType.BOOLEAN,
                    "false": TokenType.BOOLEAN,
                    "null": TokenType.NULL,
                }

                token_type = keyword_types.get(identifier, TokenType.IDENTIFIER)
                yield Token(token_type, identifier, pos)

            else:
                self.advance()

        yield Token(TokenType.EOF, "", self.current_position())

    def get_all_tokens(self) -> List[Token]:
        tokens = []

        for token in self.tokenize():
            tokens.append(token)

        return tokens


class FastLexer(OptimizedLexer):

    def __init__(self, text: str):
        super().__init__(text)

        self._has_quotes = '"' in text or "'" in text
        self._has_escapes = "\\" in text
        self._has_comments = "//" in text or "/*" in text

    def read_string_fast(self, quote_char: str) -> str:
        if not self._has_escapes:
            start_pos = self.pos + 1
            end_pos = self.text.find(quote_char, start_pos)

            if end_pos != -1:
                result = self.text[start_pos:end_pos]
                self.pos = end_pos + 1
                self.column += end_pos - start_pos + 2
                return result

        return super().read_string(quote_char)

    def tokenize_fast(self) -> Iterator[Token]:
        if not self._has_quotes and not self._has_comments:
            return self._tokenize_simple()
        else:
            return super().tokenize()

    def _tokenize_simple(self) -> Iterator[Token]:
        while self.pos < self.text_length:
            char = self.text[self.pos]

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


def create_lexer(text: str, fast_mode: bool = True) -> OptimizedLexer:
    if fast_mode and len(text) > 1000:
        return FastLexer(text)
    else:
        return OptimizedLexer(text)
