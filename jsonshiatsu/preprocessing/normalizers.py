"""
Text normalization preprocessing steps.

This module contains preprocessing steps that normalize JSON text formatting,
including quote types, whitespace, and boolean/null values.
"""

import re
from typing import Any, Optional

from ..utils.config import PreprocessingConfig
from .base import PreprocessingStepBase
from .string_utils import create_string_aware_processor


class QuoteNormalizer(PreprocessingStepBase):
    """Normalizes quotes and handles unquoted keys/values."""

    def should_apply(self, config: PreprocessingConfig) -> bool:
        """Apply if quote normalization is enabled."""
        return config.normalize_quotes

    def process(self, text: str, config: PreprocessingConfig) -> str:
        """Normalize quotes in JSON text."""
        if not config.normalize_quotes:
            return text
        result = text
        result = self._normalize_quotes(result)
        result = self._quote_unquoted_keys(result)
        result = self._quote_unquoted_values_safe(result)
        return result

    @staticmethod
    def _normalize_quotes(text: str) -> str:
        """Convert various quote types to standard double quotes."""
        # First handle Unicode quotes using regex substitution
        # NOTE: Regular apostrophe (') U+0027 is handled separately by _convert_single_quotes_safe
        unicode_quote_map = {
            "«": '"',  # U+00AB Left-pointing double angle quotation mark
            "»": '"',  # U+00BB Right-pointing double angle quotation mark
            chr(0x201C): '"',  # U+201C Left double quotation mark
            chr(0x201D): '"',  # U+201D Right double quotation mark
            chr(0x2018): '"',  # U+2018 Left single quotation mark
            chr(0x2019): '"',  # U+2019 Right single quotation mark
            "‚": '"',  # U+201A Single low-9 quotation mark
            "„": '"',  # U+201E Double low-9 quotation mark
            "‹": '"',  # U+2039 Single left-pointing angle quotation mark
            "›": '"',  # U+203A Single right-pointing angle quotation mark
            "「": '"',  # U+300C Left corner bracket (CJK)
            "」": '"',  # U+300D Right corner bracket (CJK)
        }

        # Apply Unicode quote replacements
        for unicode_char, replacement in unicode_quote_map.items():
            text = text.replace(unicode_char, replacement)

        # Handle single quotes with proper string boundary awareness
        # Use character-by-character parsing to avoid converting apostrophes inside strings
        return QuoteNormalizer._convert_single_quotes_safe(text)

    @staticmethod
    def _convert_single_quotes_safe(text: str) -> str:
        """Convert single quotes to double quotes while preserving apostrophes inside strings."""
        result = []
        i = 0
        in_double_quote = False

        while i < len(text):
            char = text[i]

            # Track double quote string boundaries
            if char == '"' and (i == 0 or text[i - 1] != "\\"):
                in_double_quote = not in_double_quote
                result.append(char)
                i += 1
                continue

            # If we're inside a double-quoted string, don't convert single quotes
            if in_double_quote:
                result.append(char)
                i += 1
                continue

            # Outside double-quoted strings - check for single-quoted JSON values
            if char == "'" and (i == 0 or text[i - 1] != "\\"):
                # Look for context that suggests this is a JSON value, not an apostrophe
                if QuoteNormalizer._is_json_single_quote_context(text, i):
                    # Find the closing single quote
                    j = i + 1
                    while j < len(text) and text[j] != "'":
                        if text[j] == "\\" and j + 1 < len(text):
                            j += 2  # Skip escaped character
                        else:
                            j += 1

                    if j < len(text) and text[j] == "'":
                        # Convert single-quoted string to double-quoted
                        content = text[i + 1 : j]
                        # Escape any existing double quotes in the content
                        content = content.replace('"', '\\"')
                        result.append(f'"{content}"')
                        i = j + 1
                        continue

                # Not a JSON single-quote context, keep as is
                result.append(char)
            else:
                result.append(char)

            i += 1

        return "".join(result)

    @staticmethod
    def _is_json_single_quote_context(text: str, pos: int) -> bool:
        """Check if a single quote at position is in a JSON value context."""
        # Look backwards for JSON-like context
        i = pos - 1
        while i >= 0 and text[i].isspace():
            i -= 1

        # After colon, opening bracket, or comma suggests JSON value
        if i >= 0 and text[i] in ":,[{":
            return True

        # Look forwards to see if it looks like a complete quoted value
        # Find the closing quote
        j = pos + 1
        while j < len(text) and text[j] != "'":
            if text[j] == "\\" and j + 1 < len(text):
                j += 2  # Skip escaped character
            else:
                j += 1

        if j < len(text) and text[j] == "'":
            # Found closing quote, check what follows
            j += 1
            while j < len(text) and text[j].isspace():
                j += 1

            # Followed by comma, closing bracket/brace, or colon suggests JSON value
            if j < len(text) and text[j] in ",]}:":
                return True

        return False

    @staticmethod
    def _is_json_string_context(text: str, pos: int) -> bool:
        """Check if a quote at position is in a JSON string context."""
        # Look backwards for JSON-like context
        i = pos - 1
        while i >= 0 and text[i].isspace():
            i -= 1

        if i >= 0 and text[i] in ":,[{":
            return True

        # Look forwards for JSON-like context
        i = pos + 1
        # Skip to closing quote
        while i < len(text) and text[i] != "'":
            i += 1

        if i < len(text):
            i += 1
            while i < len(text) and text[i].isspace():
                i += 1
            if i < len(text) and text[i] in ":,]}":
                return True

        return False

    @staticmethod
    def _quote_unquoted_keys(text: str) -> str:
        """Add quotes to unquoted object keys."""
        result = []
        i = 0
        in_string = False
        string_char = None

        while i < len(text):
            char = text[i]

            # Handle string state transitions
            string_state_changed, new_i = QuoteNormalizer._handle_string_state(
                text, i, in_string, string_char
            )
            if string_state_changed and new_i is not None:
                in_string, string_char, i = new_i
                result.append(char)
                i += 1
                continue

            if in_string:
                result.append(char)
                i += 1
                continue

            # Process potential unquoted keys
            if QuoteNormalizer._is_potential_key_start(char):
                key_info = QuoteNormalizer._extract_key_candidate(text, i)
                if key_info and QuoteNormalizer._should_quote_key(key_info["key"]):
                    result.append(f'"{key_info["key"]}"')
                    result.append(key_info["whitespace"])
                    i = key_info["colon_pos"]
                else:
                    result.append(char)
                    i += 1
            else:
                result.append(char)
                i += 1

        return "".join(result)

    @staticmethod
    def _handle_string_state(
        text: str, pos: int, in_string: bool, string_char: Optional[str]
    ) -> tuple[bool, Optional[tuple[bool, Optional[str], int]]]:
        """Handle string state transitions. Returns (changed, new_state)."""
        char = text[pos]

        if not in_string and char in ['"', "'"]:
            return True, (True, char, pos)
        if in_string and char == string_char and (pos == 0 or text[pos - 1] != "\\"):
            return True, (False, None, pos)

        return False, None

    @staticmethod
    def _is_potential_key_start(char: str) -> bool:
        """Check if character could start an unquoted key."""
        return char.isalpha() or char == "_" or char == "\\"

    @staticmethod
    def _extract_key_candidate(text: str, start: int) -> Optional[dict[str, Any]]:
        """Extract a potential key and check if it's followed by a colon."""
        char = text[start]
        i = start

        # Handle Unicode escapes
        if char == "\\" and i + 1 < len(text) and text[i + 1] == "u":
            i = QuoteNormalizer._skip_unicode_sequences(text, i)
        else:
            # Regular identifier
            while i < len(text) and (text[i].isalnum() or text[i] == "_"):
                i += 1

        # Skip whitespace to find colon
        j = i
        while j < len(text) and text[j].isspace():
            j += 1

        # Check for colon
        if j < len(text) and text[j] == ":":
            return {"key": text[start:i], "whitespace": text[i:j], "colon_pos": j}
        return None

    @staticmethod
    def _skip_unicode_sequences(text: str, start: int) -> int:
        """Skip Unicode escape sequences in key."""
        i = start
        while i < len(text):
            if text[i] == "\\" and i + 5 < len(text) and text[i + 1] == "u":
                i += 6  # Skip \uXXXX
            elif text[i].isalnum() or text[i] == "_":
                i += 1
            else:
                break
        return i

    @staticmethod
    def _should_quote_key(key: str) -> bool:
        """Determine if a key should be quoted."""
        return key.lower() not in ["true", "false", "null"] and not key.isdigit()

    @staticmethod
    def _quote_unquoted_values(text: str) -> str:
        """Add quotes to unquoted string values."""
        processor = create_string_aware_processor()

        def process_outside_strings(
            text: str, i: int, char: str
        ) -> Optional[tuple[str, int]]:
            """Process characters outside strings."""
            if char == ":":
                result_part = char
                i += 1
                # Skip whitespace
                while i < len(text) and text[i].isspace():
                    result_part += text[i]
                    i += 1

                # Check if next token needs quoting
                if i < len(text) and QuoteNormalizer._should_quote_at_position(text, i):
                    # Find the end of the unquoted value
                    start = i
                    while (
                        i < len(text) and text[i] not in ",]}" and not text[i].isspace()
                    ):
                        i += 1

                    value = text[start:i]
                    if QuoteNormalizer._should_quote_value(value):
                        result_part += f'"{value}"'
                    else:
                        result_part += value

                    return result_part, i

                if i < len(text):
                    result_part += text[i]
                    i += 1
                return result_part, i

            return None  # Use default character handling

        return processor(text, process_outside_strings, None)

    @staticmethod
    def _should_quote_at_position(text: str, pos: int) -> bool:
        """Check if a value at position should be quoted."""
        if pos >= len(text):
            return False

        char = text[pos]

        # Already quoted
        if char in ['"', "'"]:
            return False

        # Boolean or null
        if text[pos:].startswith(("true", "false", "null")):
            return False

        # Number
        if char.isdigit() or char in ".-+":
            return False

        # Array or object
        # Looks like an unquoted string value
        return char not in "[{"

    @staticmethod
    def _should_quote_value(value: str) -> bool:
        """Check if a value should be quoted based on its content."""
        # List of conditions where we should NOT quote
        no_quote_conditions = [
            not value,  # Empty value
            value.startswith(('"', "'")),  # Already quoted
            value.lower()
            in ["true", "false", "null", "none", "yes", "no", "undefined"],
            QuoteNormalizer._is_valid_number(value),  # Numbers
            value.startswith(("[", "{")),  # Arrays or objects
            "://" in value,  # URLs
            "(" in value and ")" in value,  # Function-like expressions
            any(f" {op} " in value for op in ["+", "-", "*", "/"]),  # Math expressions
        ]

        return not any(no_quote_conditions)

    @staticmethod
    def _quote_unquoted_values_safe(text: str) -> str:
        """Add quotes to unquoted string values with proper string boundary awareness."""

        # Use a more targeted regex approach to avoid complex string tracking
        def quote_unquoted_value(match: re.Match[str]) -> str:
            colon_and_whitespace = match.group(1)  # The ": " part
            value = match.group(2)  # The unquoted value

            # Check if we should quote this value
            if QuoteNormalizer._should_quote_value(value):
                return f'{colon_and_whitespace}"{value}"'
            return match.group(0)

        # More conservative pattern: only match colons that are clearly JSON key-value separators
        # Use negative lookbehind to avoid timestamp colons (digit:digit patterns)
        pattern = r'(?<!\d)\s*(:\s*)([^",\]\}\s][^",\]\}]*?)(?=\s*[,\]\}]|$)'
        result = re.sub(pattern, quote_unquoted_value, text)

        return result

    @staticmethod
    def _is_valid_number(value: str) -> bool:
        """Check if a value is a valid number (including scientific notation)."""
        if not value:
            return False

        try:
            # Try to convert to float - this handles scientific notation
            float(value)
            return True
        except ValueError:
            # Also check for special number formats that might be valid
            value_lower = value.lower()
            return value_lower in ["nan", "infinity", "-infinity", "+infinity"]

    @staticmethod
    def _should_quote_value_safe(text: str, pos: int) -> bool:
        """Check if a value at position should be quoted, avoiding URLs."""
        if pos >= len(text):
            return False

        char = text[pos]

        # Quick character-based checks first
        no_quote_chars = ['"', "'", "[", "{"] + list("0123456789.-+")
        if char in no_quote_chars:
            return False
        # Check for keywords at this position
        if text[pos:].startswith(("true", "false", "null")):
            return False

        # For complex patterns, extract the full value
        value_end = QuoteNormalizer._find_unquoted_value_end(text, pos)
        value = text[pos:value_end]

        # List of patterns that should not be quoted
        complex_patterns = [
            "://" in value,  # URLs
            "(" in value and ")" in value,  # Function calls
            any(f" {op} " in value for op in ["+", "-", "*", "/"]),  # Math expressions
        ]
        return not any(complex_patterns)

    @staticmethod
    def _find_unquoted_value_end(text: str, start: int) -> int:
        """Find the end of an unquoted value."""
        i = start
        while i < len(text) and text[i] not in ",]}" and not text[i].isspace():
            i += 1
        return i


class WhitespaceNormalizer(PreprocessingStepBase):
    """Normalizes whitespace while preserving JSON structure."""

    def should_apply(self, _config: PreprocessingConfig) -> bool:
        """Always apply whitespace normalization."""
        return True

    def process(self, text: str, _config: PreprocessingConfig) -> str:
        """Normalize whitespace in JSON text."""
        return self._normalize_whitespace(text)

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """Normalize excessive whitespace while preserving JSON structure."""
        processor = create_string_aware_processor()

        def process_outside_strings(
            text: str, i: int, char: str
        ) -> Optional[tuple[str, int]]:
            """Process characters outside strings."""
            if char.isspace():
                # Collapse multiple whitespace to single space
                result_part = " "
                while i + 1 < len(text) and text[i + 1].isspace():
                    i += 1
                i += 1
                return result_part, i
            return None  # Use default character handling

        # Process with string awareness
        text_result = processor(text, process_outside_strings, None)

        # Remove spaces around structural characters
        for chars in [
            (":", " : "),
            ("{", " { "),
            ("}", " } "),
            ("[", " [ "),
            ("]", " ] "),
            (",", " , "),
        ]:
            old_pattern, new_pattern = chars
            text_result = text_result.replace(new_pattern, old_pattern)
            text_result = text_result.replace(f" {old_pattern}", old_pattern)
            text_result = text_result.replace(f"{old_pattern} ", old_pattern)

        return text_result.strip()
