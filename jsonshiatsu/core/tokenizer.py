"""
Lexer for jsonshiatsu - tokenizes input strings for parsing.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple, Optional


class TokenType(Enum):
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
    line: int
    column: int


class Token(NamedTuple):
    type: TokenType
    value: str
    position: Position


class Lexer:
    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0
        self.line = 1
        self.column = 1

    def current_position(self) -> Position:
        return Position(self.line, self.column)

    def peek(self, offset: int = 0) -> str:
        pos = self.pos + offset
        if pos >= len(self.text):
            return ""
        return self.text[pos]

    def advance(self) -> str:
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
        while self.pos < len(self.text) and self.text[self.pos] in " \t\r":
            self.advance()

    def read_string(self, quote_char: str) -> str:
        result = ""
        self.advance()

        while self.pos < len(self.text):
            char = self.peek()

            if char == quote_char:
                self.advance()
                break
            elif char == "\\":
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
                    self.advance()
            else:
                result += self.advance()

        return result

    def read_number(self) -> str:
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
        if self.peek() != "u":
            return None

        self.advance()

        hex_digits = ""
        for _ in range(4):
            char = self.peek()
            if char and char in "0123456789abcdefABCDEF":
                hex_digits += self.advance()
            else:
                return None

        try:
            code_point = int(hex_digits, 16)

            if 0xD800 <= code_point <= 0xDBFF:
                low_surrogate = self._read_low_surrogate()
                if low_surrogate is not None:
                    high = code_point - 0xD800
                    low = low_surrogate - 0xDC00
                    combined = 0x10000 + (high << 10) + low
                    return chr(combined)
                else:
                    return "\ufffd"
            elif 0xDC00 <= code_point <= 0xDFFF:
                return "\ufffd"  # Unicode replacement character
            else:
                return chr(code_point)

        except (ValueError, OverflowError):
            return None

    def _read_low_surrogate(self) -> Optional[int]:
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
                else:
                    self.pos = saved_pos
                    self.line = saved_line
                    self.column = saved_column
                    return None
            except ValueError:
                self.pos = saved_pos
                self.line = saved_line
                self.column = saved_column
                return None
        else:
            return None

    def tokenize(self) -> Iterator[Token]:
        while self.pos < len(self.text):
            self.skip_whitespace()

            if self.pos >= len(self.text):
                break

            char = self.peek()
            pos = self.current_position()

            if char == "\n":
                self.advance()
                yield Token(TokenType.NEWLINE, char, pos)

            elif char == "{":
                self.advance()
                yield Token(TokenType.LBRACE, char, pos)
            elif char == "}":
                self.advance()
                yield Token(TokenType.RBRACE, char, pos)
            elif char == "[":
                self.advance()
                yield Token(TokenType.LBRACKET, char, pos)
            elif char == "]":
                self.advance()
                yield Token(TokenType.RBRACKET, char, pos)
            elif char == ":":
                self.advance()
                yield Token(TokenType.COLON, char, pos)
            elif char == ",":
                self.advance()
                yield Token(TokenType.COMMA, char, pos)

            elif char in "\"'":
                string_value = self.read_string(char)
                yield Token(TokenType.STRING, string_value, pos)

            elif (
                char.isdigit()
                or (char == "-" and self.peek(1).isdigit())
                or (char == "." and self.peek(1).isdigit())
            ):
                number_value = self.read_number()
                yield Token(TokenType.NUMBER, number_value, pos)

            elif char == "-" and self.peek(1).isalpha():
                saved_pos = self.pos
                self.advance()
                identifier = self.read_identifier()
                if identifier in ["Infinity", "NaN"]:
                    yield Token(TokenType.IDENTIFIER, f"-{identifier}", pos)
                else:
                    self.pos = saved_pos
                    self.advance()

            elif (
                char.isalpha() or char == "_" or (char == "\\" and self.peek(1) == "u")
            ):
                identifier = self.read_identifier()

                if identifier == "true" or identifier == "false":
                    yield Token(TokenType.BOOLEAN, identifier, pos)
                elif identifier == "null":
                    yield Token(TokenType.NULL, identifier, pos)
                else:
                    yield Token(TokenType.IDENTIFIER, identifier, pos)

            else:
                self.advance()

        yield Token(TokenType.EOF, "", self.current_position())

    def get_all_tokens(self) -> list[Token]:
        return list(self.tokenize())
