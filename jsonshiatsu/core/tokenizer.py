"""
Lexer for jsonshiatsu - tokenizes input strings for parsing.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Iterator, List, NamedTuple, Optional


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
        """Read a quoted string, handling escape sequences."""
        result = ""
        self.advance()  # Skip opening quote

        while self.pos < len(self.text):
            char = self.peek()

            if char == quote_char:
                self.advance()  # Skip closing quote
                break
            elif char == "\\":
                self.advance()  # Skip backslash
                next_char = self.peek()
                if next_char == "u":
                    # Handle Unicode escape \uXXXX
                    saved_pos = self.pos
                    unicode_result = self._read_unicode_escape()
                    if unicode_result is not None:
                        result += unicode_result
                    else:
                        # Invalid Unicode escape, treat literally
                        # Reset position and treat as literal \u
                        self.pos = saved_pos
                        result += self.advance()  # Add the 'u' character
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
        """Read a number (integer or float)."""
        result = ""

        # Handle negative sign
        if self.peek() == "-":
            result += self.advance()

        # Handle numbers starting with decimal point
        if self.peek() == ".":
            result += self.advance()
            while self.pos < len(self.text) and self.peek().isdigit():
                result += self.advance()
        else:
            # Read integer part
            while self.pos < len(self.text) and self.peek().isdigit():
                result += self.advance()

            # Read decimal part
            if self.peek() == ".":
                result += self.advance()
                while self.pos < len(self.text) and self.peek().isdigit():
                    result += self.advance()

        # Read exponent part
        if self.peek().lower() == "e":
            result += self.advance()
            if self.peek() in "+-":
                result += self.advance()
            while self.pos < len(self.text) and self.peek().isdigit():
                result += self.advance()

        return result

    def read_identifier(self) -> str:
        """Read an unquoted identifier, supporting Unicode escapes."""
        result = ""
        while self.pos < len(self.text):
            char = self.peek()
            if char.isalnum() or char in "_$":
                result += self.advance()
            elif char == "\\" and self.peek(1) == "u":
                # Handle Unicode escape in identifier
                self.advance()  # Skip '\'
                unicode_result = self._read_unicode_escape()
                if unicode_result is not None:
                    result += unicode_result
                else:
                    # Invalid Unicode escape, treat literally
                    result += "u"
            else:
                break
        return result

    def _read_unicode_escape(self) -> Optional[str]:
        """Read a Unicode escape sequence like u0041 or surrogate pairs like
        uD83DuDE00."""
        if self.peek() != "u":
            return None

        self.advance()  # Skip 'u'

        # Read exactly 4 hex digits
        hex_digits = ""
        for _ in range(4):
            char = self.peek()
            if char and char in "0123456789abcdefABCDEF":
                hex_digits += self.advance()
            else:
                # Invalid or incomplete hex sequence
                return None

        try:
            # Convert hex to code point
            code_point = int(hex_digits, 16)

            # Check if this is a high surrogate (for emojis)
            if 0xD800 <= code_point <= 0xDBFF:
                # This is a high surrogate, look for low surrogate
                low_surrogate = self._read_low_surrogate()
                if low_surrogate is not None:
                    # Combine surrogates into full Unicode character
                    high = code_point - 0xD800
                    low = low_surrogate - 0xDC00
                    combined = 0x10000 + (high << 10) + low
                    return chr(combined)
                else:
                    # No valid low surrogate found, treat as invalid
                    # Return replacement character instead of invalid surrogate
                    return "\uFFFD"  # Unicode replacement character
            elif 0xDC00 <= code_point <= 0xDFFF:
                # This is a low surrogate without a high surrogate (invalid)
                # Return replacement character instead of invalid surrogate
                return "\uFFFD"  # Unicode replacement character
            else:
                # Regular Unicode character
                return chr(code_point)

        except (ValueError, OverflowError):
            # Invalid code point
            return None

    def _read_low_surrogate(self) -> Optional[int]:
        """Try to read a low surrogate that follows a high surrogate."""
        # Save current position in case we need to backtrack
        saved_pos = self.pos
        saved_line = self.line
        saved_column = self.column

        # Look for \u pattern
        if self.peek() == "\\" and self.peek(1) == "u":
            self.advance()  # Skip '\'
            self.advance()  # Skip 'u'

            # Read 4 hex digits
            hex_digits = ""
            for _ in range(4):
                char = self.peek()
                if char and char in "0123456789abcdefABCDEF":
                    hex_digits += self.advance()
                else:
                    # Not a valid surrogate, backtrack
                    self.pos = saved_pos
                    self.line = saved_line
                    self.column = saved_column
                    return None

            try:
                code_point = int(hex_digits, 16)
                # Check if this is a valid low surrogate
                if 0xDC00 <= code_point <= 0xDFFF:
                    return code_point
                else:
                    # Not a low surrogate, backtrack
                    self.pos = saved_pos
                    self.line = saved_line
                    self.column = saved_column
                    return None
            except ValueError:
                # Invalid hex, backtrack
                self.pos = saved_pos
                self.line = saved_line
                self.column = saved_column
                return None
        else:
            # No following \u pattern
            return None

    def tokenize(self) -> Iterator[Token]:
        """Generate tokens from the input text."""
        while self.pos < len(self.text):
            self.skip_whitespace()

            if self.pos >= len(self.text):
                break

            char = self.peek()
            pos = self.current_position()

            # Newlines
            if char == "\n":
                self.advance()
                yield Token(TokenType.NEWLINE, char, pos)

            # Structural characters
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

            # Quoted strings
            elif char in "\"'":
                string_value = self.read_string(char)
                yield Token(TokenType.STRING, string_value, pos)

            # Numbers
            elif (
                char.isdigit()
                or (char == "-" and self.peek(1).isdigit())
                or (char == "." and self.peek(1).isdigit())
            ):
                number_value = self.read_number()
                yield Token(TokenType.NUMBER, number_value, pos)

            # Handle negative special values like -Infinity, -NaN
            elif char == "-" and self.peek(1).isalpha():
                # Look ahead to see if this is -Infinity or -NaN
                saved_pos = self.pos
                self.advance()  # Skip '-'
                identifier = self.read_identifier()
                if identifier in ["Infinity", "NaN"]:
                    # Create negative special identifier
                    yield Token(TokenType.IDENTIFIER, f"-{identifier}", pos)
                else:
                    # Not a special case, backtrack and treat as separate tokens
                    self.pos = saved_pos
                    self.advance()  # Just advance past the '-'
                    # The minus will be treated as an unknown character and skipped
                    # The identifier will be processed in the next iteration

            # Identifiers and keywords
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
                # Skip unknown characters
                self.advance()

        yield Token(TokenType.EOF, "", self.current_position())

    def get_all_tokens(self) -> List[Token]:
        """Get all tokens as a list."""
        return list(self.tokenize())
