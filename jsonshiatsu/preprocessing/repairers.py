"""
Structure repair preprocessing steps.

This module contains preprocessing steps that repair malformed JSON structures,
including missing commas, colons, unescaped strings, and incomplete objects.
"""

import re

from ..core.array_object_handler import ArrayObjectHandler
from ..core.string_preprocessors import StringPreprocessor
from ..utils.config import PreprocessingConfig
from .base import PreprocessingStepBase
from .string_utils import find_string_end_simple


class StructureFixer(PreprocessingStepBase):
    """Fixes structural issues in JSON text."""

    def should_apply(self, config: PreprocessingConfig) -> bool:
        """Apply based on configuration settings."""
        return (
            config.handle_incomplete_json or config.handle_sparse_arrays or True
        )  # Always try basic structure fixes

    def process(self, text: str, config: PreprocessingConfig) -> str:
        """Fix structural issues in JSON text."""
        result = text

        result = self._fix_assignment_operators(result)
        result = self._fix_missing_values(result)
        result = self._fix_missing_commas(result)
        result = self._fix_missing_colons(result)

        if config.handle_incomplete_json:
            result = self._handle_incomplete_json(result)

        if config.handle_sparse_arrays:
            result = self._handle_sparse_arrays(result)

        # Fix trailing commas AFTER sparse array handling
        result = self._fix_trailing_commas(result)

        return result

    @staticmethod
    def _fix_assignment_operators(text: str) -> str:
        """Convert assignment operators (=) to colons (:) in object contexts."""
        # Handle quoted keys with assignment: "key" = value -> "key": value
        result = re.sub(r'"([^"]*)"(\s*)=(\s*)', r'"\1"\2:\3', text)
        # Handle unquoted keys with assignment: key = value -> key: value
        result = re.sub(r"\b([a-zA-Z_]\w*)(\s*)=(\s*)(?![=<>!])", r"\1\2:\3", result)
        return result

    @staticmethod
    def _fix_missing_values(text: str) -> str:
        """Fix missing values after colons."""
        # Handle simple cases first: : followed directly by } or ,
        result = re.sub(r":\s*([},])", r": null\1", text)

        # Handle end of string case
        result = re.sub(r":\s*$", r": null", result)

        # Handle newline case more carefully - only if next non-empty line starts with } or ,
        # or if there's no next meaningful line
        lines = result.split("\n")
        for i, line in enumerate(lines):
            # Look for lines ending with : followed by whitespace
            if re.search(r":\s*$", line):
                # Check if next non-empty line has a value or is structural
                has_value_on_next_line = False
                for j in range(i + 1, len(lines)):
                    next_line = lines[j].strip()
                    if not next_line:  # Empty line, continue
                        continue
                    # If next line starts with a value or string concatenation
                    if (
                        next_line.startswith(('"', "'", "{", "["))
                        or re.match(r"^(true|false|null|\d)", next_line)
                        or "+" in next_line
                    ):  # String concatenation
                        has_value_on_next_line = True
                        break
                    # If next line is structural (}, ], or new key), no value
                    if (
                        next_line.startswith(("}", "]"))
                        or re.match(r'^"[^"]*"\s*:', next_line)  # New key
                        or re.match(r"^[a-zA-Z_]\w*\s*:", next_line)
                    ):  # Unquoted key
                        break
                    break  # Other content, assume it's a value

                if not has_value_on_next_line:
                    lines[i] = re.sub(r":\s*$", ": null", line)

        return "\n".join(lines)

    @staticmethod
    def _fix_missing_commas(text: str) -> str:
        """Add missing commas between JSON elements."""
        # First handle intra-line commas (like adjacent strings in arrays)
        text = StructureFixer._fix_intraline_commas(text)

        # Then handle inter-line commas
        lines = text.split("\n")
        result_lines = []

        for i, line in enumerate(lines):
            current_line = line.rstrip()
            next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""

            if (
                current_line
                and next_line
                and StructureFixer._needs_comma_between_lines(current_line, next_line)
                and not current_line.endswith(",")
            ):
                # Add comma between these lines
                current_line += ","

            result_lines.append(current_line)

        return "\n".join(result_lines)

    @staticmethod
    def _needs_comma_between_lines(current: str, next_line: str) -> bool:
        """Check if a comma is needed between two lines."""
        if not current.strip() or not next_line.strip():
            return False

        # Don't add comma after structural characters
        if current.strip().endswith((",", "{", "[", ":", "(")):
            return False

        # Don't add comma before closing characters
        if next_line.strip().startswith(("}", "]", ")")):
            return False

        # Check for object/array element patterns
        current_stripped = current.strip()
        next_stripped = next_line.strip()

        # Between object key-value pairs
        if next_stripped.startswith('"') or re.match(
            r"^[a-zA-Z_][a-zA-Z0-9_]*\s*:", next_stripped
        ):
            return True

        # Between array elements or objects
        return current_stripped.endswith(("}", "]", '"')) and next_stripped.startswith(
            ("{", "[", '"')
        )

    @staticmethod
    def _fix_missing_colons(text: str) -> str:
        """Add missing colons after object keys."""
        # Need to be string-aware - don't process content inside strings
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
            if in_string and char == string_char:
                # Check if quote is properly escaped
                escape_count = 0
                j = i - 1
                while j >= 0 and text[j] == "\\":
                    escape_count += 1
                    j -= 1

                # If even number of backslashes, the quote is NOT escaped
                if escape_count % 2 == 0:
                    in_string = False
                    string_char = None
                result.append(char)
                i += 1
                continue

            if in_string:
                result.append(char)
                i += 1
                continue

            # Only process missing colons when not inside strings
            # Look for pattern: "key" whitespace value_start (without colon)
            if char == '"':
                # Found start of potential key
                key_start = i
                key_end = StructureFixer._find_string_end_simple(text, i)
                if key_end != -1:
                    # Found complete quoted string
                    potential_key = text[key_start : key_end + 1]

                    # Look ahead for whitespace followed by value
                    j = key_end + 1
                    while j < len(text) and text[j].isspace():
                        j += 1

                    # Check if next character starts a value (not a colon)
                    if (
                        j < len(text)
                        and text[j] != ":"
                        and (text[j] in '"[{' or text[j].isalnum() or text[j] == "_")
                    ):
                        # This looks like a missing colon situation
                        # Add the key
                        result.extend(list(potential_key))
                        # Add colon and space
                        result.append(":")
                        result.append(" ")
                        # Skip the whitespace we detected
                        i = j
                        continue

            result.append(char)
            i += 1

        return "".join(result)

    @staticmethod
    def _fix_trailing_commas(text: str) -> str:
        """Remove trailing commas before closing braces/brackets."""
        # Need to be string-aware - don't process content inside strings
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
            if in_string and char == string_char:
                # Check if quote is properly escaped
                escape_count = 0
                j = i - 1
                while j >= 0 and text[j] == "\\":
                    escape_count += 1
                    j -= 1

                # If even number of backslashes, the quote is NOT escaped
                if escape_count % 2 == 0:
                    in_string = False
                    string_char = None
                result.append(char)
                i += 1
                continue

            if in_string:
                result.append(char)
                i += 1
                continue

            # Only process trailing commas when not inside strings
            # Look for pattern: comma whitespace closing_brace/bracket
            if char == ",":
                # Look ahead for closing brace/bracket
                j = i + 1
                while j < len(text) and text[j].isspace():
                    j += 1

                if j < len(text) and text[j] in "}]":
                    # This is a trailing comma - skip it and the whitespace
                    i = j
                    continue

            result.append(char)
            i += 1

        return "".join(result)

    @staticmethod
    def _fix_intraline_commas(text: str) -> str:
        """Fix missing commas within the same line, especially in arrays."""
        # Handle adjacent strings in arrays: ["item1" "item2"] -> ["item1", "item2"]
        # Be very careful to only apply this inside array contexts, not object contexts

        # Use regex approach that's more precise - only match strings that are clearly
        # array elements (inside brackets, no colons between them)
        # Pattern: [ ... "string1" whitespace "string2" ... ] where there's no comma between
        def add_comma_in_arrays(match: re.Match[str]) -> str:
            full_match = match.group(0)
            # Only add comma if there's no colon after the first string (not an object key)
            if ":" not in full_match:
                return re.sub(r'("([^"]*)")(\s+)("([^"]*)")', r"\1,\3\4", full_match)
            return full_match

        # Look for array contexts with adjacent strings
        # This is more conservative - only applies inside clear array brackets
        result = re.sub(
            r'\[([^\[\]]*"[^"]*"\s+"[^"]*"[^\[\]]*)\]', add_comma_in_arrays, text
        )

        return result

    @staticmethod
    def _find_string_end_simple(text: str, start: int) -> int:
        """Find the end of a quoted string starting at position start."""
        return find_string_end_simple(text, start)

    @staticmethod
    def _handle_incomplete_json(text: str) -> str:
        """Handle incomplete JSON structures by closing them."""
        text = text.strip()
        if not text:
            return text

        # Safety check: if text contains obvious malformed escapes, don't try to fix structure
        # This prevents infinite loops when processing strings with trailing backslashes
        # Odd number of quotes + malformed escapes = skip structural fixes
        if (
            text.count('"') % 2 != 0
            and "\\" in text
            and (text.endswith('\\"') or '\\"' in text)
        ):
            # Potentially malformed escape sequences, skip structural fixes
            return text

        # First, handle unclosed strings before structural completion
        # This ensures strings are closed properly before we add structural elements
        in_string = False
        string_char = None
        i = 0

        # First pass: detect if we have an unclosed string
        while i < len(text):
            char = text[i]
            if not in_string and char in ['"', "'"]:
                in_string = True
                string_char = char
            elif in_string and char == string_char:
                # Check if quote is properly escaped
                escape_count = 0
                j = i - 1
                while j >= 0 and text[j] == "\\":
                    escape_count += 1
                    j -= 1
                if escape_count % 2 == 0:
                    in_string = False
                    string_char = None
            i += 1

        # Handle unclosed strings first - before structure completion
        if in_string:
            # We need to find where this unclosed string actually started
            # Look backwards from the end to find the last quote that doesn't have a pair
            pos = len(text) - 1
            while pos >= 0:
                if text[pos] == string_char and (pos == 0 or text[pos - 1] != "\\"):
                    # Found unescaped quote - look for a good place to close this specific string
                    # The content likely ends before any structural characters
                    # For timestamps, look for common patterns
                    close_pos = pos + 1
                    content_end = close_pos

                    # Scan forward to find reasonable content boundary
                    while close_pos < len(text):
                        char = text[close_pos]
                        if char in ",\n}]":
                            # Found structural character - content likely ends here
                            content_end = (
                                close_pos  # Don't include the structural character
                            )
                            break
                        if char.isalnum() or char in ":+-TZ ":
                            # Valid content character (timestamp-like, including spaces)
                            content_end = close_pos + 1
                        else:
                            # Non-valid content character, stop here
                            content_end = close_pos
                            break
                        close_pos += 1

                    # Insert closing quote after the actual content
                    text = (
                        text[:content_end] + (string_char or '"') + text[content_end:]
                    )
                    break
                pos -= 1
            else:
                # Couldn't find the start, just close at end
                text += string_char or '"'

        # After handling strings, handle structural completion
        # Track unclosed structures
        stack = []
        in_string = False
        string_char = None
        i = 0

        while i < len(text):
            char = text[i]

            # Handle string state
            if not in_string and char in ['"', "'"]:
                in_string = True
                string_char = char
            elif in_string and char == string_char:
                # Check if quote is properly escaped by counting preceding backslashes
                escape_count = 0
                j = i - 1
                while j >= 0 and text[j] == "\\":
                    escape_count += 1
                    j -= 1

                # If even number of backslashes, the quote is NOT escaped
                if escape_count % 2 == 0:
                    in_string = False
                    string_char = None

            if in_string:
                i += 1
                continue

            # Track structure nesting
            if char == "{":
                stack.append("}")
            elif char == "[":
                stack.append("]")
            elif char in "}]" and stack and stack[-1] == char:
                stack.pop()

            i += 1

        # Close unclosed structures
        if stack:
            text += "".join(reversed(stack))

        return text

    @staticmethod
    def _handle_sparse_arrays(text: str) -> str:
        """Handle sparse arrays by replacing empty elements with null."""
        # Use the existing ArrayObjectHandler logic which handles this correctly
        try:
            return ArrayObjectHandler.handle_sparse_arrays(text)
        except ImportError:
            # Fallback implementation
            result = text

            # Keep applying until no more changes (handles multiple consecutive commas)
            max_iterations = 10  # Prevent infinite loops
            for _ in range(max_iterations):
                old_result = result

                # Pattern for empty array elements: [, or ,, or ,]
                patterns = [
                    (r"\[\s*,", "[null,"),  # [, -> [null,
                    (r",\s*,", ",null,"),  # ,, -> ,null,
                    (r",\s*\]", ",null]"),  # ,] -> ,null]
                ]

                for pattern, replacement in patterns:
                    result = re.sub(pattern, replacement, result)

                if result == old_result:
                    break

            return result


class StringRepairer(PreprocessingStepBase):
    """Repairs issues with strings in JSON text."""

    def should_apply(self, config: PreprocessingConfig) -> bool:
        """Apply if string repair features are enabled."""
        # Always apply for multiline string fixing, or if other features are enabled
        return True

    def process(self, text: str, config: PreprocessingConfig) -> str:
        """Repair string issues in JSON text."""
        result = text

        # Always fix multiline strings and unescaped quotes as part of string repair
        result = self._fix_multiline_strings(result)
        result = self._fix_unescaped_quotes_in_strings(result)

        if config.fix_unescaped_strings:
            result = self._fix_unescaped_strings(result)

        if config.normalize_boolean_null:
            result = self.normalize_boolean_null(result)

        return result

    @staticmethod
    def _fix_multiline_strings(text: str) -> str:
        """Fix multiline strings by combining them properly."""
        return StringPreprocessor.fix_multiline_strings(text)

    @staticmethod
    def _fix_unescaped_quotes_in_strings(text: str) -> str:
        """Fix unescaped quotes within strings."""
        return StringPreprocessor.fix_unescaped_quotes_in_strings(text)

    @staticmethod
    def _fix_unescaped_strings(text: str) -> str:
        """Fix unescaped characters in strings."""
        # Use the comprehensive string preprocessing method
        return StringPreprocessor.fix_unescaped_strings(text)

    @staticmethod
    def normalize_boolean_null(text: str) -> str:
        """Normalize boolean and null values to JSON standard."""
        # Comprehensive boolean and null value replacements
        replacements = [
            # Python-style
            (r"\bTrue\b", "true"),
            (r"\bFalse\b", "false"),
            (r"\bNone\b", "null"),
            # JavaScript/generic (case-insensitive)
            (r"\bundefined\b", "null"),
            (r"\bUNDEFINED\b", "null"),
            (r"\bUndefined\b", "null"),
            # NULL variants
            (r"\bNULL\b", "null"),
            (r"\bNull\b", "null"),
            # Yes/No variants (case insensitive)
            (r"\b[Yy][Ee][Ss]\b", "true"),
            (r"\b[Nn][Oo]\b", "false"),
            # Note: NaN and Infinity are handled by JavaScriptHandler, not here
        ]

        result = text
        for pattern, replacement in replacements:
            result = re.sub(pattern, replacement, result)

        return result
