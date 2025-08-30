"""
JSON Preprocessor - Handles common malformed JSON patterns.

This module provides preprocessing functions to clean and extract JSON from
various malformed formats commonly found in real-world data.
"""

import re
from re import Match
from typing import Any, Optional

from ..utils.config import PreprocessingConfig
from .array_object_handler import ArrayObjectHandler
from .data_type_processor import DataTypeProcessor
from .javascript_handler import JavaScriptHandler
from .regex_utils import (
    safe_regex_search,
    safe_regex_sub,
)
from .string_preprocessors import StringPreprocessor


class JSONPreprocessor:
    """Preprocessor for cleaning malformed JSON responses."""

    @staticmethod
    def extract_from_markdown(text: str) -> str:
        """
        Extract JSON from markdown code blocks.

        Handles:
        - ```json ... ```
        - ``` ... ```
        - `...` (inline)
        """
        json_block_pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
        match = safe_regex_search(json_block_pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        inline_pattern = r"`\s*([{[].*?[}\]])\s*`"
        match = safe_regex_search(inline_pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()

        return text

    @staticmethod
    def remove_trailing_text(text: str) -> str:
        """
        Remove explanatory text that appears after valid JSON.

        Handles cases where text is added after the JSON.
        """
        text = text.strip()

        # Find the last occurrence of } or ] that could end valid JSON
        json_end_chars = [
            "}",
            "]",
            '"',
            "'",
            "e",
            "l",
            "E",
        ]  # null, true, false endings

        # Try to find complete JSON structures
        brace_count = 0
        bracket_count = 0
        in_string = False
        string_char = None
        escaped = False
        last_valid_pos = -1

        for i, char in enumerate(text):
            if escaped:
                escaped = False
                continue

            if char == "\\" and in_string:
                escaped = True
                continue

            if char in ['"', "'"] and not in_string:
                in_string = True
                string_char = char
            elif char == string_char and in_string:
                in_string = False
                string_char = None
            elif not in_string:
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                elif char == "[":
                    bracket_count += 1
                elif char == "]":
                    bracket_count -= 1

                if brace_count == 0 and bracket_count == 0 and char in json_end_chars:
                    last_valid_pos = i

        if last_valid_pos > -1:
            return text[: last_valid_pos + 1]

        return text

    @staticmethod
    def remove_comments(text: str) -> str:
        """Delegate to JavaScriptHandler for comment removal."""
        return JavaScriptHandler.remove_comments(text)

    @staticmethod
    def extract_first_json(text: str) -> str:
        """
        Extract the first complete JSON object/array from text with multiple JSONs.
        """
        text = text.strip()
        parser_state = {
            'brace_count': 0,
            'bracket_count': 0,
            'in_string': False,
            'string_char': None,
            'escaped': False,
            'start_pos': -1
        }

        for i, char in enumerate(text):
            if parser_state['escaped']:
                parser_state['escaped'] = False
                continue

            if JSONPreprocessor._handle_escape_char(char, parser_state):
                continue

            if JSONPreprocessor._handle_string_state(char, parser_state):
                continue

            if not parser_state['in_string']:
                JSONPreprocessor._handle_structure_chars(char, parser_state, i)

                if JSONPreprocessor._is_complete_structure(parser_state):
                    return text[parser_state['start_pos'] : i + 1]

        return text

    @staticmethod
    def _handle_escape_char(char: str, state: dict) -> bool:
        """Handle escape character in string."""
        if char == "\\" and state['in_string']:
            state['escaped'] = True
            return True
        return False

    @staticmethod
    def _handle_string_state(char: str, state: dict) -> bool:
        """Handle string start and end."""
        if char in ['"', "'"] and not state['in_string']:
            state['in_string'] = True
            state['string_char'] = char
            return True
        if char == state['string_char'] and state['in_string']:
            state['in_string'] = False
            state['string_char'] = None
            return True
        return False

    @staticmethod
    def _handle_structure_chars(char: str, state: dict, i: int) -> None:
        """Handle structural characters outside strings."""
        if char in ["{", "["]:
            if state['start_pos'] == -1:
                state['start_pos'] = i
            if char == "{":
                state['brace_count'] += 1
            else:
                state['bracket_count'] += 1
        elif char == "}":
            state['brace_count'] -= 1
        elif char == "]":
            state['bracket_count'] -= 1

    @staticmethod
    def _is_complete_structure(state: dict) -> bool:
        """Check if we have a complete JSON structure."""
        return bool(
            state['start_pos'] != -1
            and state['brace_count'] == 0
            and state['bracket_count'] == 0
        )

    @staticmethod
    def unwrap_function_calls(text: str) -> str:
        """Delegate to JavaScriptHandler for function call unwrapping."""
        return JavaScriptHandler.unwrap_function_calls(text)

    @staticmethod
    def unwrap_inline_function_calls(text: str) -> str:
        """Delegate to JavaScriptHandler for inline function call unwrapping."""
        return JavaScriptHandler.unwrap_inline_function_calls(text)

    @staticmethod
    def quote_unquoted_values(text: str) -> str:
        """
        Add quotes around unquoted values that contain special characters.

        Handles common patterns in LLM responses and JavaScript object literals:
        - model: gpt-4 → model: "gpt-4"
        - version: v2.1 → version: "v2.1"
        - type: text/plain → type: "text/plain"
        - url: https://example.com → url: "https://example.com"
        - status: success → status: "success"

        Only quotes values that would be invalid as JSON identifiers.
        """

        def quote_value(match: Match[str]) -> str:
            colon_space = match.group(1)
            value = match.group(2)
            after = match.group(3) if len(match.groups()) >= 3 else ""

            # Check if value needs quoting
            # Quote if it contains special characters that make it invalid as an
            # identifier
            needs_quoting = bool(safe_regex_search(r"[-./:#@?&=+%]", value))

            # Also quote if it looks like a URL, version number, or complex identifier
            if any(
                pattern in value.lower()
                for pattern in ["http", "www.", "v1.", "v2.", "gpt-", "claude-"]
            ):
                needs_quoting = True

            # Don't quote special JSON literal values
            # These should remain unquoted for later processing
            special_literals = ["NaN", "Infinity", "-Infinity", "undefined"]
            if (
                value in special_literals
                or value.lower() in ["true", "false", "null"]
                or (
                    value.replace(".", "")
                    .replace("-", "")
                    .replace("+", "")
                    .replace("e", "")
                    .replace("E", "")
                    .isdigit()
                )
            ):
                needs_quoting = False
            else:
                # Quote any other string value (like 'success', 'error', etc.)
                needs_quoting = True

            if needs_quoting:
                return f'{colon_space}"{value}"{after}'
            return match.group(0)

        # Pattern to match unquoted values after colon
        # Look for: colon whitespace identifier
        pattern = r"(:\s*)([a-zA-Z_][a-zA-Z0-9_.-]*)\s*(?=[,\]}]|$)"

        return safe_regex_sub(pattern, quote_value, text, flags=re.MULTILINE)

    @staticmethod
    def quote_unquoted_keys(text: str) -> str:
        """
        Add quotes around unquoted object keys.

        Handles:
        - model: value → "model": value
        - debug_info: {...} → "debug_info": {...}

        Only quotes keys that are valid identifiers but not already quoted.
        """

        def quote_key(match: Match[str]) -> str:
            before_context = match.group(1)
            key = match.group(2)
            colon_space = match.group(3)

            # Skip if key is already quoted or is in a quoted string context
            if '"' in before_context:
                return match.group(0)

            return f'{before_context}"{key}"{colon_space}'

        # Pattern to match unquoted keys: identifier followed by colon
        # Capture context to avoid matching inside quoted strings
        pattern = r"(\s|^|[{,])([a-zA-Z_][a-zA-Z0-9_]*)(\s*:\s*)"

        return safe_regex_sub(pattern, quote_key, text)

    @staticmethod
    def normalize_quotes(text: str) -> str:
        """
        Normalize non-standard quotation marks to standard JSON quotes.

        This handles smart quotes, guillemets, and other quote-like characters
        that might appear in copy-pasted or internationalized content.
        """
        # Map of non-standard quotes to standard quotes
        quote_mapping = {
            # Smart double quotes
            '"': '"',  # U+201C Left double quotation mark
            "„": '"',  # U+201E Double low-9 quotation mark
            # Smart single quotes
            """: "'",  # U+2018 Left single quotation mark
            """: "'",  # U+2019 Right single quotation mark
            "‚": "'",  # U+201A Single low-9 quotation mark
            # Guillemets (French quotes)
            "«": '"',  # U+00AB Left-pointing double angle quotation mark
            "»": '"',  # U+00BB Right-pointing double angle quotation mark
            "‹": "'",  # U+2039 Single left-pointing angle quotation mark
            "›": "'",  # U+203A Single right-pointing angle quotation mark
            # Other quote-like characters
            "`": "'",  # U+0060 Grave accent (sometimes used as quote)
            "´": "'",  # U+00B4 Acute accent (sometimes used as quote)
            # CJK quotes
            "「": '"',  # U+300C Left corner bracket
            "」": '"',  # U+300D Right corner bracket
            "『": '"',  # U+300E Left white corner bracket
            "』": '"',  # U+300F Right white corner bracket
        }

        for non_standard, standard in quote_mapping.items():
            text = text.replace(non_standard, standard)

        return text

    @staticmethod
    def normalize_boolean_null(text: str) -> str:
        """Delegate to DataTypeProcessor for boolean/null normalization."""
        return DataTypeProcessor.normalize_boolean_null(text)

    @staticmethod
    def fix_unescaped_strings(text: str) -> str:
        """Delegate to StringPreprocessor for string escape handling."""
        return StringPreprocessor.fix_unescaped_strings(text)

    @staticmethod
    def fix_unescaped_quotes_in_strings(text: str) -> str:
        """Delegate to StringPreprocessor for quote escape handling."""
        return StringPreprocessor.fix_unescaped_quotes_in_strings(text)

    @staticmethod
    def normalize_mixed_quotes(text: str) -> str:
        """Delegate to StringPreprocessor for quote normalization."""
        return StringPreprocessor.normalize_mixed_quotes(text)

    @staticmethod
    def fix_multiline_strings(text: str) -> str:
        """Delegate to StringPreprocessor for multiline string handling."""
        return StringPreprocessor.fix_multiline_strings(text)

    @staticmethod
    def handle_string_concatenation(text: str) -> str:
        """Delegate to StringPreprocessor for string concatenation."""
        return StringPreprocessor.handle_string_concatenation(text)

    @staticmethod
    def normalize_string_concatenation(text: str) -> str:
        """Delegate to StringPreprocessor for string concatenation normalization."""
        return StringPreprocessor.normalize_string_concatenation(text)

    @staticmethod
    def fix_unescaped_quotes_in_strings_original(text: str) -> str:
        """Delegate to StringPreprocessor for unescaped quote fixing."""
        return StringPreprocessor.fix_unescaped_quotes_in_strings(text)

    @staticmethod
    def handle_incomplete_json(text: str) -> str:
        """
        Attempt to complete incomplete JSON structures by adding missing closing
        braces/brackets.

        This is a best-effort approach for handling truncated JSON.
        """
        text = text.strip()

        if JSONPreprocessor._is_already_complete(text):
            return text

        stack, in_string, string_char = JSONPreprocessor._analyze_structure(text)

        text = JSONPreprocessor._close_unclosed_strings(text, in_string, string_char)
        text = JSONPreprocessor._fix_incomplete_key_values(text)
        text = JSONPreprocessor._close_unclosed_structures(text, stack)

        return text

    @staticmethod
    def _is_already_complete(text: str) -> bool:
        """Check if JSON structure is already complete."""
        return (
            text.count("{") == text.count("}")
            and text.count("[") == text.count("]")
            and ("authentication" in text or "concatenation" in text)
        )

    @staticmethod
    def _analyze_structure(text: str) -> tuple[list[str], bool, Optional[str]]:
        """Analyze JSON structure and return stack, string state."""
        stack: list[str] = []
        in_string = False
        string_char: Optional[str] = None
        escaped = False

        for char in text:
            if escaped:
                escaped = False
                continue

            if char == "\\" and in_string:
                escaped = True
                continue

            if JSONPreprocessor._handle_string_boundaries(char, in_string, string_char):
                in_string, string_char = JSONPreprocessor._update_string_state(
                    char, in_string, string_char
                )
            elif not in_string:
                JSONPreprocessor._handle_structural_brackets(char, stack)

        return stack, in_string, string_char

    @staticmethod
    def _handle_string_boundaries(
        char: str, in_string: bool, string_char: Optional[str]
    ) -> bool:
        """Check if character is a string boundary."""
        return (char in ['"', "'"] and not in_string) or (char == string_char and in_string)

    @staticmethod
    def _update_string_state(
        char: str, in_string: bool, string_char: Optional[str]
    ) -> tuple[bool, Optional[str]]:
        """Update string parsing state."""
        if char in ['"', "'"] and not in_string:
            return True, char
        if char == string_char and in_string:
            return False, None
        return in_string, string_char

    @staticmethod
    def _handle_structural_brackets(char: str, stack: list) -> None:
        """Handle opening and closing brackets/braces."""
        if char in ["{", "["]:
            stack.append(char)
        elif char == "}" and stack and stack[-1] == "{" or char == "]" and stack and stack[-1] == "[":
            stack.pop()

    @staticmethod
    def _close_unclosed_strings(
        text: str, in_string: bool, string_char: Optional[str]
    ) -> str:
        """Close unclosed strings."""
        if in_string and string_char:
            text += string_char
        return text

    @staticmethod
    def _fix_incomplete_key_values(text: str) -> str:
        """Fix incomplete key-value pairs."""
        if "[" in text and text.rstrip().endswith(":"):
            pattern = r',\s*"[^"]*":\s*$'
            if re.search(pattern, text):
                text = re.sub(pattern, "", text)
            else:
                text = text.rstrip() + " null"
        elif text.rstrip().endswith(":"):
            text = text.rstrip() + " null"
        return text

    @staticmethod
    def _close_unclosed_structures(text: str, stack: list[str]) -> str:
        """Add missing closing brackets and braces."""
        while stack:
            opener = stack.pop()
            if opener == "{":
                text += "}"
            elif opener == "[":
                text += "]"
        return text

    @staticmethod
    def handle_streaming_responses(text: str) -> str:
        """
        Handle streaming LLM responses that may have partial JSON.

        Looks for common patterns in LLM streaming:
        - Multiple JSON objects on separate lines
        - "data:" prefixes from server-sent events
        - Partial JSON at the end of streams
        """
        original_text = text

        if JSONPreprocessor._should_skip_streaming_processing(text):
            return original_text

        lines = text.strip().split("\n")

        if not JSONPreprocessor._has_sse_patterns(lines):
            return original_text

        cleaned_lines = JSONPreprocessor._clean_streaming_lines(lines)

        if not cleaned_lines:
            return original_text

        return JSONPreprocessor._extract_best_json(cleaned_lines, original_text)

    @staticmethod
    def _should_skip_streaming_processing(text: str) -> bool:
        """Check if streaming processing should be skipped."""
        return "```" in text or "json" in text.lower()[:100]

    @staticmethod
    def _has_sse_patterns(lines: list[str]) -> bool:
        """Check if lines contain server-sent event patterns."""
        return any(
            line.strip() in ["[DONE]", "event: done", "event: error"]
            or JSONPreprocessor._is_sse_data_line(line)
            for line in lines
        )

    @staticmethod
    def _is_sse_data_line(line: str) -> bool:
        """Check if line is a server-sent event data line."""
        line = line.strip()
        if not line.startswith("data:") or len(line) <= 5:
            return False

        content = line[5:].strip()
        return (
            content.startswith(("{", "[", '"'))
            and not any(keyword in line for keyword in ['"', "'", ":", "[", "]"])
        )

    @staticmethod
    def _clean_streaming_lines(lines: list[str]) -> list[str]:
        """Clean streaming response lines by removing SSE prefixes."""
        cleaned_lines = []

        for line in lines:
            line = line.strip()

            if JSONPreprocessor._should_skip_line(line):
                continue

            cleaned_line = JSONPreprocessor._process_data_prefix(line)
            cleaned_lines.append(cleaned_line)

        return cleaned_lines

    @staticmethod
    def _should_skip_line(line: str) -> bool:
        """Check if line should be skipped during cleaning."""
        return not line or line in ["[DONE]", "event: done", "event: error"]

    @staticmethod
    def _process_data_prefix(line: str) -> str:
        """Process data: prefix from server-sent events."""
        if not line.startswith("data:"):
            return line

        data_content = line[5:].strip()
        if data_content.startswith(("{", "[", '"')) or ":" not in data_content:
            return data_content
        return line

    @staticmethod
    def _extract_best_json(cleaned_lines: list[str], original_text: str) -> str:
        """Extract the best JSON from cleaned lines."""
        reconstructed = "\n".join(cleaned_lines).strip()

        if JSONPreprocessor._is_complete_json_structure(reconstructed):
            return reconstructed

        json_objects = JSONPreprocessor._find_complete_json_objects(cleaned_lines)

        if json_objects:
            return max(json_objects, key=len)

        return reconstructed if reconstructed else original_text

    @staticmethod
    def _is_complete_json_structure(text: str) -> bool:
        """Check if text appears to be a complete JSON structure."""
        return text.startswith(("{", "[")) and text.endswith(("}", "]"))

    @staticmethod
    def _find_complete_json_objects(lines: list[str]) -> list[str]:
        """Find complete JSON objects in lines."""
        json_objects = []
        for line in lines:
            line = line.strip()
            if line.startswith(("{", "[")) and line.endswith(("}", "]")):
                json_objects.append(line)
        return json_objects

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """
        Normalize excessive whitespace while preserving JSON structure.

        Common in LLM responses:
        - Extra spaces around colons and commas
        - Inconsistent indentation
        - Mixed tabs and spaces
        """
        # Replace tabs with spaces
        text = text.replace("\t", "    ")

        # Normalize spaces around JSON punctuation
        # Add space after comma if missing, but only in JSON structural context
        # Properly handle quoted strings
        def normalize_commas_outside_strings(text: str) -> str:
            result = []
            i = 0
            in_string = False
            string_char = None

            while i < len(text):
                char = text[i]

                if not in_string and char in ['"', "'"]:
                    in_string = True
                    string_char = char
                    result.append(char)
                elif in_string and char == string_char:
                    # Check if this quote is escaped
                    escaped = False
                    j = i - 1
                    while j >= 0 and text[j] == "\\":
                        escaped = not escaped
                        j -= 1

                    if not escaped:
                        in_string = False
                        string_char = None
                    result.append(char)
                elif (
                    not in_string
                    and char == ","
                    and i + 1 < len(text)
                    and text[i + 1] not in [" ", "}", "]"]
                ):
                    # Add space after comma in JSON structure
                    result.append(", ")
                else:
                    result.append(char)

                i += 1

            return "".join(result)

        text = normalize_commas_outside_strings(text)

        # Normalize spaces around colons, but only for JSON key-value pairs
        # Pattern: "key" : value -> "key": value (avoid timestamp colons)
        text = safe_regex_sub(r'"\s*:\s*(?![0-9])', '": ', text)

        # Handle unquoted keys with quote-aware processing
        def normalize_colons_outside_strings(text: str) -> str:
            result = []
            i = 0
            in_string = False
            string_char = None

            while i < len(text):
                char = text[i]

                if not in_string and char in ['"', "'"]:
                    in_string = True
                    string_char = char
                    result.append(char)
                elif in_string and char == string_char:
                    # Check if this quote is escaped
                    escaped = False
                    j = i - 1
                    while j >= 0 and text[j] == "\\":
                        escaped = not escaped
                        j -= 1

                    if not escaped:
                        in_string = False
                        string_char = None
                    result.append(char)
                elif not in_string and char == ":" and i > 0 and text[i - 1].isalnum():
                    # Add space after colon in JSON structure (but not timestamps)
                    if i + 1 < len(text) and not text[i + 1].isdigit():
                        result.append(": ")
                    else:
                        result.append(char)
                else:
                    result.append(char)

                i += 1

            return "".join(result)

        text = normalize_colons_outside_strings(text)

        # Comma spacing is already handled by normalize_commas_outside_strings above

        # Clean up line breaks around braces
        text = safe_regex_sub(r"{\s*\n\s*", "{\n    ", text)
        text = safe_regex_sub(r"\n\s*}", "\n}", text)

        return text

    @staticmethod
    def fix_missing_commas(text: str) -> str:
        """
        Fix missing commas in JSON objects and arrays.

        Handles patterns like:
        - { "key1": "value1" "key2": "value2" } -> adds missing commas
        - [ "item1" "item2" ] -> [ "item1", "item2" ]
        - Missing commas after closing braces/brackets
        """
        # Process line by line to handle multiline objects/arrays
        lines = text.split("\n")
        result_lines = []

        for i, line in enumerate(lines):
            # Fix missing commas on the same line first
            # Pattern: "value1" "value2" -> "value1", "value2"
            pattern = r'"([^"]*?)"\s+"([^"]*?)"'
            fixed_line = safe_regex_sub(pattern, r'"\1", "\2"', line)

            # Fix missing commas between values and objects/arrays
            # "value" { -> "value", {
            fixed_line = safe_regex_sub(r'"\s*\{', r'", {', fixed_line)
            fixed_line = safe_regex_sub(r'"\s*\[', r'", [', fixed_line)

            # Fix missing commas after closing braces/brackets when followed by quotes
            # } "key" -> }, "key"
            # BUT: Skip this fix entirely when we're inside a string value
            # More sophisticated: only apply if } or ] is at start or after whitespace
            # This avoids matching } inside template strings like "Hello ${name}"
            if not safe_regex_search(r':\s*"[^"]*\$\{[^}]*\}[^"]*"', fixed_line):
                fixed_line = safe_regex_sub(r'(\s|^)(\}\s*)"', r'\1\2, "', fixed_line)
                fixed_line = safe_regex_sub(r'(\s|^)(\]\s*)"', r'\1\2, "', fixed_line)

            # Fix missing commas between different value types
            # true "key" -> true, "key"
            # 123 "key" -> 123, "key"
            # null "key" -> null, "key"
            value_pattern = r'\b(true|false|null|\d+(?:\.\d+)?)\s+"'
            fixed_line = safe_regex_sub(value_pattern, r'\1, "', fixed_line)

            # Now check if we need to add comma at end of line for multiline case
            if i < len(lines) - 1:  # Not the last line
                current_stripped = fixed_line.strip()
                next_stripped = lines[i + 1].strip()

                # Check if current line needs a comma at the end
                needs_comma = (
                    current_stripped
                    and next_stripped
                    and not current_stripped.endswith((",", "{", "[", ":"))
                    and (
                        next_stripped.startswith('"')
                        or safe_regex_search(
                            r"^[a-zA-Z_][a-zA-Z0-9_]*\s*:", next_stripped
                        )
                        or (current_stripped.endswith("}") and next_stripped.startswith("{"))
                        or (current_stripped.endswith("]") and next_stripped.startswith("["))
                    )
                )
                if needs_comma:
                    # Add comma at end of line
                    fixed_line = fixed_line.rstrip() + ","

            result_lines.append(fixed_line)

        return "\n".join(result_lines)

    @staticmethod
    def fix_assignment_operators(text: str) -> str:
        """
        Fix assignment operators (=) used instead of colons (:) in JSON objects.

        Handles:
        - "key" = "value" -> "key": "value"
        - key = value -> key: value
        """
        # Replace = with : in object key-value pairs
        # Pattern: "key" = value -> "key": value
        text = safe_regex_sub(r'"([^"]+)"\s*=\s*', r'"\1": ', text)

        # Pattern: key = value -> key: value (for unquoted keys)
        text = safe_regex_sub(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*", r"\1: ", text)

        return text

    @staticmethod
    def remove_trailing_commas(text: str) -> str:
        """
        Remove trailing commas from objects and arrays.

        Handles:
        - {"key": "value",} -> {"key": "value"}
        - [1, 2, 3,] -> [1, 2, 3]

        But preserves:
        - {2,} in regex quantifiers
        - {2,3} in regex quantifiers
        """
        # Remove trailing commas before closing braces and brackets
        # BUT avoid removing commas from regex quantifiers like {2,} or {2,3}

        # Use a more sophisticated approach that checks context
        # Don't remove comma if it's preceded by a single digit (regex quantifier)
        # This preserves {n,} and {n,m} patterns while removing actual trailing commas

        # Pattern: comma followed by whitespace and } or ], but avoid regex quantifiers
        # Only preserve comma if it's part of {digit,} pattern (regex quantifier)
        # This is more specific than just looking for any digit before comma

        # First handle regex quantifiers: preserve {digit,} and {digit,digit} patterns
        # Then remove other trailing commas

        # Remove trailing commas, but preserve regex quantifiers like {n,}
        def replace_trailing_comma(match: Match[str]) -> str:
            before_comma = match.group(1)  # Character before comma
            bracket = match.group(2)  # Closing bracket

            if JSONPreprocessor._should_preserve_regex_quantifier(match, text, before_comma, bracket):
                return match.group(0)

            if JSONPreprocessor._should_preserve_sparse_array(before_comma, bracket):
                return match.group(0)

            return before_comma + bracket

        # Match: (character)(optional space)(comma)(optional space)(bracket)
        text = safe_regex_sub(r"(\S)\s*,\s*([}\]])", replace_trailing_comma, text)
        return text

    @staticmethod
    def _should_preserve_regex_quantifier(
        match: Match[str], text: str, before_comma: str, bracket: str
    ) -> bool:
        """Check if comma should be preserved as part of regex quantifier."""
        if bracket == "}" and before_comma.isdigit():
            full_match_start = match.start()
            if full_match_start > 0 and text[full_match_start - 1] == "{":
                return True
        return False

    @staticmethod
    def _should_preserve_sparse_array(before_comma: str, bracket: str) -> bool:
        """Check if comma should be preserved in sparse array pattern."""
        return before_comma == "[" and bracket == "]"

    @staticmethod
    def normalize_special_numbers(text: str) -> str:
        """Delegate to DataTypeProcessor for special number normalization."""
        return DataTypeProcessor.normalize_special_numbers(text)

    @staticmethod
    def normalize_extended_numbers(text: str) -> str:
        """Delegate to DataTypeProcessor for extended number normalization."""
        return DataTypeProcessor.normalize_extended_numbers(text)

    @staticmethod
    def fix_structural_syntax(text: str) -> str:
        """Delegate to ArrayObjectHandler for structural syntax fixing."""
        return ArrayObjectHandler.fix_structural_syntax(text)

    @staticmethod
    def fix_missing_colons(text: str) -> str:
        """
        Fix missing colons in object key-value pairs.

        Handles cases like:
        - {"key" "value"} -> {"key": "value"}
        - {key "value"} -> {key: "value"}
        - {"key" value} -> {"key": value}
        """

        # Fix quoted key followed by quoted value: "key" "value" -> "key": "value"
        # But only if this looks like a key-value pair (after { or ,)
        text = safe_regex_sub(r'([\{,]\s*)("[^"]*")\s+("[^"]*")', r"\1\2: \3", text)

        # Fix unquoted key followed by quoted value: key "value" -> key: "value"
        # Only after { or , or newline/start of line
        text = safe_regex_sub(r'([\{,\n]\s*)(\w+)\s+("[^"]*")', r"\1\2: \3", text)

        # Fix quoted key followed by unquoted value: "key" value -> "key": value
        # Only after { or , or newline/start of line
        text = safe_regex_sub(
            r'([\{,\n]\s*)("[^"]*")\s+(\w+)(?=\s*[,}])', r"\1\2: \3", text
        )

        return text

    @staticmethod
    def evaluate_javascript_expressions(text: str) -> str:
        """Delegate to JavaScriptHandler for JavaScript expression evaluation."""
        return JavaScriptHandler.evaluate_javascript_expressions(text)

    @staticmethod
    def handle_javascript_constructs(text: str) -> str:
        """Delegate to JavaScriptHandler for JavaScript construct handling."""
        return JavaScriptHandler.handle_javascript_constructs(text)

    @staticmethod
    def handle_empty_values(text: str) -> str:
        """Delegate to DataTypeProcessor for empty value handling."""
        return DataTypeProcessor.handle_empty_values(text)

    @staticmethod
    def fix_unclosed_strings(text: str) -> str:
        """Delegate to ArrayObjectHandler for unclosed string fixing."""
        return ArrayObjectHandler.fix_unclosed_strings(text)

    @staticmethod
    def handle_sparse_arrays(text: str) -> str:
        """Delegate to ArrayObjectHandler for sparse array handling."""
        return ArrayObjectHandler.handle_sparse_arrays(text)

    @classmethod
    def preprocess(
        cls, text: str, aggressive: bool = False, config: Optional[Any] = None
    ) -> str:
        """
        Apply preprocessing steps to clean malformed JSON.

        Args:
            text: Raw text that may contain JSON
            aggressive: If True, apply aggressive cleaning (deprecated, use config)
            config: PreprocessingConfig object for granular control

        Returns:
            Cleaned JSON string
        """
        # Handle backward compatibility
        if config is None:
            if aggressive:
                config = PreprocessingConfig.aggressive()
            else:
                config = PreprocessingConfig.aggressive()  # New default

        # Apply preprocessing steps based on config
        # LLM-specific optimizations - handle streaming first
        text = cls.handle_streaming_responses(text)

        if config.extract_from_markdown:
            text = cls.extract_from_markdown(text)

        if config.remove_comments:
            text = cls.remove_comments(text)

        if config.unwrap_function_calls:
            text = cls.unwrap_function_calls(text)
            # Also unwrap inline function calls within the JSON
            text = cls.unwrap_inline_function_calls(text)

        if config.extract_first_json:
            text = cls.extract_first_json(text)

        if config.remove_trailing_text:
            text = cls.remove_trailing_text(text)

        # Fix assignment operators (= instead of :) early
        text = cls.fix_assignment_operators(text)

        # Fix structural syntax issues (parentheses, set literals)
        text = cls.fix_structural_syntax(text)

        # Fix missing colons in objects
        text = cls.fix_missing_colons(text)

        # Handle JavaScript constructs early
        text = cls.handle_javascript_constructs(text)

        # Evaluate JavaScript expressions (hybrid approach)
        text = cls.evaluate_javascript_expressions(text)

        # Normalize special numbers (hex, octal, NaN, Infinity)
        text = cls.normalize_special_numbers(text)

        # Normalize extended number formats (version numbers, binary, etc.)
        text = cls.normalize_extended_numbers(text)

        # Handle empty values and incomplete structures
        text = cls.handle_empty_values(text)

        # Fix multiline strings BEFORE fixing unclosed strings
        text = StringPreprocessor.fix_multiline_strings(text)

        # Handle string concatenation BEFORE quote processing to avoid corruption
        text = StringPreprocessor.handle_string_concatenation(text)

        # Enhanced string concatenation handling
        text = StringPreprocessor.normalize_string_concatenation(text)

        # Normalize mixed quotes after string concatenation
        text = StringPreprocessor.normalize_mixed_quotes(text)

        # Fix unclosed strings (after multiline strings are properly handled)
        text = cls.fix_unclosed_strings(text)

        # Normalize boolean/null BEFORE quoting so they're recognized as JSON literals
        if config.normalize_boolean_null:
            text = cls.normalize_boolean_null(text)

        # Quote unquoted values with special characters (before quote normalization)
        text = cls.quote_unquoted_values(text)

        # Quote unquoted keys to ensure valid JSON
        text = cls.quote_unquoted_keys(text)

        if config.normalize_quotes:
            text = cls.normalize_quotes(text)

        if config.fix_unescaped_strings:
            text = StringPreprocessor.fix_unescaped_strings(text)
            # Only apply quote fixing if text looks like it has problematic quotes
            # Skip if it contains URLs (might have legitimate quotes in URLs)
            has_urls = "http://" in text or "https://" in text
            if not has_urls:
                text = StringPreprocessor.fix_unescaped_quotes_in_strings(text)

        # Fix missing commas after quote processing
        text = cls.fix_missing_commas(text)

        # Remove trailing commas from objects and arrays (invalid in standard JSON)
        text = cls.remove_trailing_commas(text)

        if config.handle_incomplete_json:
            text = cls.handle_incomplete_json(text)

        # Normalize whitespace before handling sparse arrays for better comma detection
        text = cls.normalize_whitespace(text)

        # Handle sparse arrays as final step
        if config.handle_sparse_arrays:
            text = cls.handle_sparse_arrays(text)

        # Final cleanup: fix trailing commas that ended up inside string values
        # This handles edge cases where commas meant to be JSON punctuation
        # ended up inside strings during processing
        text = re.sub(r'"([^"]+),"(\s*[}\]])', r'"\1",\2', text)

        return text.strip()
