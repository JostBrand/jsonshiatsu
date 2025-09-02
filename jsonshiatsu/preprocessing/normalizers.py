"""
Text normalization preprocessing steps.

This module contains preprocessing steps that normalize JSON text formatting,
including quote types, whitespace, and boolean/null values.
"""

import re

from ..utils.config import PreprocessingConfig
from .pipeline import PreprocessingStepBase


class QuoteNormalizer(PreprocessingStepBase):
    """Normalizes quotes and handles unquoted keys/values."""

    def should_apply(self, config: PreprocessingConfig) -> bool:
        """Apply if quote normalization is enabled."""
        return config.normalize_quotes

    def process(self, text: str, config: PreprocessingConfig) -> str:
        """Normalize quotes in JSON text."""
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

            # Track string state
            if not in_string and char in ['"', "'"]:
                in_string = True
                string_char = char
                result.append(char)
                i += 1
                continue
            elif in_string and char == string_char and (i == 0 or text[i - 1] != "\\"):
                in_string = False
                string_char = None
                result.append(char)
                i += 1
                continue
            elif in_string:
                # Inside a string - don't process keys
                result.append(char)
                i += 1
                continue

            # Only look for unquoted keys when outside strings
            if char.isalpha() or char == "_" or char == "\\":
                # Potential start of unquoted key (including Unicode escapes)
                start = i

                # Handle Unicode escape sequences at start of key
                if char == "\\" and i + 1 < len(text) and text[i + 1] == "u":
                    # Skip Unicode escape sequences in the key
                    while i < len(text):
                        if text[i] == "\\" and i + 5 < len(text) and text[i + 1] == "u":
                            # Skip \uXXXX
                            i += 6
                        elif text[i].isalnum() or text[i] == "_":
                            i += 1
                        else:
                            break
                else:
                    # Collect the identifier (regular ASCII)
                    while i < len(text) and (text[i].isalnum() or text[i] == "_"):
                        i += 1

                # Skip whitespace
                j = i
                while j < len(text) and text[j].isspace():
                    j += 1

                # Check if followed by colon
                if j < len(text) and text[j] == ":":
                    key = text[start:i]
                    # Don't quote if it's a boolean, null, or number
                    if (
                        key.lower() not in ["true", "false", "null"]
                        and not key.isdigit()
                    ):
                        result.append(f'"{key}"')
                        # Add any whitespace that was skipped
                        result.append(text[i:j])
                        i = j
                    else:
                        result.append(text[start:i])
                else:
                    result.append(text[start:i])
            else:
                result.append(char)
                i += 1

        return "".join(result)

    @staticmethod
    def _quote_unquoted_values(text: str) -> str:
        """Add quotes to unquoted string values."""
        result = []
        i = 0
        in_string = False
        string_char = None

        while i < len(text):
            char = text[i]

            # Track string state
            if not in_string and char in ['"', "'"]:
                in_string = True
                string_char = char
                result.append(char)
                i += 1
                continue
            elif in_string and char == string_char and (i == 0 or text[i - 1] != "\\"):
                in_string = False
                string_char = None
                result.append(char)
                i += 1
                continue
            elif in_string:
                # Inside a string - don't process colons
                result.append(char)
                i += 1
                continue

            # Only process colons when outside strings
            if char == ":":
                result.append(char)
                i += 1

                # Skip whitespace
                while i < len(text) and text[i].isspace():
                    result.append(text[i])
                    i += 1

                # Check if next token needs quoting
                if i < len(text) and QuoteNormalizer._should_quote_value(text, i):
                    # Find the end of the unquoted value
                    start = i
                    while (
                        i < len(text) and text[i] not in ",]}" and not text[i].isspace()
                    ):
                        i += 1

                    value = text[start:i]
                    if (
                        value
                        and not value.startswith(('"', "'"))
                        and value.lower()
                        not in [
                            "true",
                            "false",
                            "null",
                            "none",
                            "yes",
                            "no",
                            "undefined",
                        ]
                        and not QuoteNormalizer._is_valid_number(value)
                        and not value.startswith(("[", "{"))
                        and "://" not in value
                        and not ("(" in value and ")" in value)
                        and not any(f" {op} " in value for op in ["+", "-", "*", "/"])
                    ):
                        result.append(f'"{value}"')
                    else:
                        result.append(value)
                else:
                    if i < len(text):
                        result.append(text[i])
                        i += 1
            else:
                result.append(char)
                i += 1

        return "".join(result)

    @staticmethod
    def _should_quote_value(text: str, pos: int) -> bool:
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
    def _quote_unquoted_values_safe(text: str) -> str:
        """Add quotes to unquoted string values with proper string boundary awareness."""

        # Use a more targeted regex approach to avoid complex string tracking
        def quote_unquoted_value(match: re.Match[str]) -> str:
            colon_and_whitespace = match.group(1)  # The ": " part
            value = match.group(2)  # The unquoted value

            # Don't quote if already quoted
            if value.startswith(('"', "'")):
                return match.group(0)

            # Don't quote booleans, null, numbers
            if value.lower() in [
                "true",
                "false",
                "null",
                "none",
                "yes",
                "no",
                "undefined",
            ] or QuoteNormalizer._is_valid_number(value):
                return match.group(0)

            # Don't quote arrays or objects
            if value.startswith(("[", "{")):
                return match.group(0)

            # Don't quote URLs
            if "://" in value:
                return match.group(0)

            # Don't quote function calls
            if "(" in value and ")" in value:
                return match.group(0)

            # Don't quote expressions with spaced operators
            if any(f" {op} " in value for op in ["+", "-", "*", "/"]):
                return match.group(0)

            # Quote simple unquoted values
            return f'{colon_and_whitespace}"{value}"'

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

        # Already quoted
        if char in ['"', "'"]:
            return False

        # Boolean or null
        if text[pos:].startswith(("true", "false", "null")):
            return False

        # Number (including scientific notation)
        if char.isdigit() or char in ".-+":
            return False

        # Array or object
        if char in "[{":
            return False

        # Check if this looks like a URL or other complex pattern that should not be quoted
        # Look ahead to see the full value
        value_end = QuoteNormalizer._find_unquoted_value_end(text, pos)
        value = text[pos:value_end]

        # Don't quote URLs
        if "://" in value:
            return False

        # Don't quote function calls
        if "(" in value and ")" in value:
            return False

        # Don't quote complex expressions with operators (but allow simple values with dashes like model names)
        # Only avoid quoting if there are spaces around operators (indicating expressions)
        # Looks like a simple unquoted string value
        return not any(f" {op} " in value for op in ["+", "-", "*", "/"])

    @staticmethod
    def _find_unquoted_value_end(text: str, start: int) -> int:
        """Find the end of an unquoted value."""
        i = start
        while i < len(text) and text[i] not in ",]}" and not text[i].isspace():
            i += 1
        return i


class WhitespaceNormalizer(PreprocessingStepBase):
    """Normalizes whitespace while preserving JSON structure."""

    def should_apply(self, config: PreprocessingConfig) -> bool:
        """Always apply whitespace normalization."""
        return True

    def process(self, text: str, config: PreprocessingConfig) -> str:
        """Normalize whitespace in JSON text."""
        return self._normalize_whitespace(text)

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """Normalize excessive whitespace while preserving JSON structure."""
        result = []
        i = 0
        in_string = False
        string_char = None

        while i < len(text):
            char = text[i]

            # Track string state
            if not in_string and char in ['"', "'"]:
                in_string = True
                string_char = char
                result.append(char)
                i += 1
                continue
            elif in_string and char == string_char and (i == 0 or text[i - 1] != "\\"):
                in_string = False
                string_char = None
                result.append(char)
                i += 1
                continue
            elif in_string:
                result.append(char)
                i += 1
                continue

            # Handle whitespace outside strings
            if char.isspace():
                # Collapse multiple whitespace to single space
                result.append(" ")
                while i + 1 < len(text) and text[i + 1].isspace():
                    i += 1
                i += 1
            else:
                result.append(char)
                i += 1

        # Clean up extra spaces around structural characters
        text_result = "".join(result)

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
