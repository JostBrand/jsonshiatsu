"""
Lexer for jsonshiatsu - tokenizes input strings for parsing.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple, Optional

from .constants import JSON_ESCAPE_MAP, get_structural_token_map


class TokenType(Enum):
    """Token types for JSON parsing."""

    LBRACE = "LBRACE"
    RBRACE = "RBRACE"
    LBRACKET = "LBRACKET"
    RBRACKET = "RBRACKET"
    COLON = "COLON"
    COMMA = "COMMA"

    STRING = "STRING"
    NUMBER = "NUMBER"
    BOOLEAN = "BOOLEAN"
    NULL = "NULL"
    IDENTIFIER = "IDENTIFIER"

    WHITESPACE = "WHITESPACE"
    NEWLINE = "NEWLINE"
    EOF = "EOF"


@dataclass
class Position:
    """Position in source text (line and column)."""

    line: int
    column: int


class Token(NamedTuple):
    """Token with type, value and position information."""

    type: TokenType
    value: str
    position: Position


class Lexer:
    """Lexical analyzer for JSON input."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0
        self.line = 1
        self.column = 1

    def current_position(self) -> Position:
        """Get current position in the text."""
        return Position(self.line, self.column)

    def peek(self, offset: int = 0) -> str:
        """Peek at character at given offset without consuming it."""
        pos = self.pos + offset
        if pos >= len(self.text):
            return ""
        return self.text[pos]

    def advance(self) -> str:
        """Advance position and return the current character."""
        if self.pos >= len(self.text):
            return ""

        char = self.text[self.pos]
        self.pos += 1

        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        return char

    def skip_whitespace(self) -> None:
        """Skip whitespace characters (space, tab, carriage return)."""
        while self.pos < len(self.text) and self.text[self.pos] in " \t\r":
            self.advance()

    def read_string(self, quote_char: str) -> str:
        """Read a quoted string with escape sequence handling."""
        result = ""
        self.advance()

        while self.pos < len(self.text):
            char = self.peek()

            if char == quote_char:
                self.advance()
                break
            if char == "\\":
                self.advance()
                next_char = self.peek()
                if next_char == "u":
                    saved_pos = self.pos
                    unicode_result = self._read_unicode_escape()
                    if unicode_result is not None:
                        result += unicode_result
                    else:
                        self.pos = saved_pos
                        result += self.advance()
                elif next_char:
                    result += JSON_ESCAPE_MAP.get(next_char, next_char)
                    self.advance()
            else:
                result += self.advance()

        return result

    def read_number(self) -> str:
        """Read a numeric literal."""
        result = ""

        if self.peek() == "-":
            result += self.advance()

        if self.peek() == ".":
            result += self.advance()
            while self.pos < len(self.text) and self.peek().isdigit():
                result += self.advance()
        else:
            while self.pos < len(self.text) and self.peek().isdigit():
                result += self.advance()

            if self.peek() == ".":
                result += self.advance()
                while self.pos < len(self.text) and self.peek().isdigit():
                    result += self.advance()

        if self.peek().lower() == "e":
            result += self.advance()
            if self.peek() in "+-":
                result += self.advance()
            while self.pos < len(self.text) and self.peek().isdigit():
                result += self.advance()

        return result

    def read_identifier(self) -> str:
        """Read an identifier with optional unicode escapes."""
        result = ""
        while self.pos < len(self.text):
            char = self.peek()
            if char.isalnum() or char in "_$":
                result += self.advance()
            elif char == "\\" and self.peek(1) == "u":
                self.advance()
                unicode_result = self._read_unicode_escape()
                if unicode_result is not None:
                    result += unicode_result
                else:
                    result += "u"
            else:
                break
        return result

    def _read_unicode_escape(self) -> Optional[str]:
        """Read a Unicode escape sequence."""
        if self.peek() != "u":
            return None

        self.advance()
        hex_digits = self._read_hex_digits()
        if hex_digits is None:
            return None

        try:
            code_point = int(hex_digits, 16)
            return self._process_unicode_code_point(code_point)
        except (ValueError, OverflowError):
            return None

    def _read_hex_digits(self) -> Optional[str]:
        """Read exactly 4 hexadecimal digits."""
        hex_digits = ""
        for _ in range(4):
            char = self.peek()
            if char and char in "0123456789abcdefABCDEF":
                hex_digits += self.advance()
            else:
                return None
        return hex_digits

    def _process_unicode_code_point(self, code_point: int) -> str:
        """Process a Unicode code point, handling surrogates."""
        if 0xD800 <= code_point <= 0xDBFF:
            return self._handle_high_surrogate(code_point)
        if 0xDC00 <= code_point <= 0xDFFF:
            return "\ufffd"  # Unicode replacement character
        return chr(code_point)

    def _handle_high_surrogate(self, code_point: int) -> str:
        """Handle high surrogate pair."""
        low_surrogate = self._read_low_surrogate()
        if low_surrogate is not None:
            high = code_point - 0xD800
            low = low_surrogate - 0xDC00
            combined = 0x10000 + (high << 10) + low
            return chr(combined)
        return "\ufffd"

    def _read_low_surrogate(self) -> Optional[int]:
        """Read the low surrogate pair for Unicode surrogates."""
        saved_pos = self.pos
        saved_line = self.line
        saved_column = self.column

        if self.peek() == "\\" and self.peek(1) == "u":
            self.advance()
            self.advance()

            hex_digits = ""
            for _ in range(4):
                char = self.peek()
                if char and char in "0123456789abcdefABCDEF":
                    hex_digits += self.advance()
                else:
                    self.pos = saved_pos
                    self.line = saved_line
                    self.column = saved_column
                    return None

            try:
                code_point = int(hex_digits, 16)
                if 0xDC00 <= code_point <= 0xDFFF:
                    return code_point
                self.pos = saved_pos
                self.line = saved_line
                self.column = saved_column
                return None
            except ValueError:
                self.pos = saved_pos
                self.line = saved_line
                self.column = saved_column
                return None
        return None

    def tokenize(self) -> Iterator[Token]:
        """Tokenize the input text into a sequence of tokens."""
        while self.pos < len(self.text):
            self.skip_whitespace()

            if self.pos >= len(self.text):
                break

            char = self.peek()
            pos = self.current_position()

            # Try different token types in order
            token = self._try_newline_token(char, pos)
            if token:
                yield token
                continue

            token = self._try_structural_token(char, pos)
            if token:
                yield token
                continue

            token = self._try_string_token(char, pos)
            if token:
                yield token
                continue

            token = self._try_number_token(char, pos)
            if token:
                yield token
                continue

            token = self._try_negative_special_token(char, pos)
            if token:
                yield token
                continue

            token = self._try_identifier_token(char, pos)
            if token:
                yield token
                continue

            # Skip unknown character
            self.advance()

        yield Token(TokenType.EOF, "", self.current_position())

    def _try_newline_token(self, char: str, pos: Position) -> Optional[Token]:
        """Try to create a newline token."""
        if char == "\n":
            self.advance()
            return Token(TokenType.NEWLINE, char, pos)
        return None

    def _try_structural_token(self, char: str, pos: Position) -> Optional[Token]:
        """Try to create structural tokens (braces, brackets, etc.)."""
        token_map = get_structural_token_map()

        if char in token_map:
            self.advance()
            return Token(token_map[char], char, pos)
        return None

    def _try_string_token(self, char: str, pos: Position) -> Optional[Token]:
        """Try to create a string token."""
        if char in "\"'":
            string_value = self.read_string(char)
            return Token(TokenType.STRING, string_value, pos)
        return None

    def _try_number_token(self, char: str, pos: Position) -> Optional[Token]:
        """Try to create a number token."""
        if (
            char.isdigit()
            or (char == "-" and self.peek(1).isdigit())
            or (char == "." and self.peek(1).isdigit())
        ):
            number_value = self.read_number()
            return Token(TokenType.NUMBER, number_value, pos)
        return None

    def _try_negative_special_token(self, char: str, pos: Position) -> Optional[Token]:
        """Try to create negative special tokens (-Infinity, -NaN)."""
        if char == "-" and self.peek(1).isalpha():
            saved_pos = self.pos
            self.advance()
            identifier = self.read_identifier()
            if identifier in ["Infinity", "NaN"]:
                return Token(TokenType.IDENTIFIER, f"-{identifier}", pos)
            self.pos = saved_pos
            self.advance()
        return None

    def _try_identifier_token(self, char: str, pos: Position) -> Optional[Token]:
        """Try to create an identifier or keyword token."""
        if char.isalpha() or char == "_" or (char == "\\" and self.peek(1) == "u"):
            identifier = self.read_identifier()

            if identifier in {"true", "false"}:
                return Token(TokenType.BOOLEAN, identifier, pos)
            if identifier == "null":
                return Token(TokenType.NULL, identifier, pos)
            return Token(TokenType.IDENTIFIER, identifier, pos)
        return None

    def get_all_tokens(self) -> list[Token]:
        """Get all tokens as a list."""
        return list(self.tokenize())
