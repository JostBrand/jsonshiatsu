"""
Common constants and mappings used across the jsonshiatsu library.
"""

# Import here to avoid circular imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .tokenizer import TokenType

# Standard JSON escape sequences mapping
JSON_ESCAPE_MAP = {
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


# Structural token mapping function
def get_structural_token_type(char: str) -> str:
    """Get the token type name for a structural character."""
    mapping = {
        "{": "LBRACE",
        "}": "RBRACE",
        "[": "LBRACKET",
        "]": "RBRACKET",
        ":": "COLON",
        ",": "COMMA",
    }
    return mapping.get(char, "UNKNOWN")


# Token type mapping for structural characters
def get_structural_token_map() -> dict[str, "TokenType"]:
    """Get the mapping of structural characters to TokenType enums."""
    # Import here to avoid circular imports
    from .tokenizer import TokenType  # pylint: disable=import-outside-toplevel

    return {
        "{": TokenType.LBRACE,
        "}": TokenType.RBRACE,
        "[": TokenType.LBRACKET,
        "]": TokenType.RBRACKET,
        ":": TokenType.COLON,
        ",": TokenType.COMMA,
    }
