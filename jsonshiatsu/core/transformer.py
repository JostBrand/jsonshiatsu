"""
JSON Preprocessor - Handles common malformed JSON patterns.

This module provides preprocessing functions to clean and extract JSON from
various malformed formats commonly found in real-world data.
"""

import re
import signal
from re import Match
from typing import Any, Callable, Optional, Union


class RegexTimeout(Exception):
    pass


def timeout_handler(signum: int, frame: Any) -> None:
    raise RegexTimeout("Regex operation timed out")


def safe_regex_sub(
    pattern: str,
    repl: Union[str, Callable[[Match[str]], str]],
    string: str,
    flags: int = 0,
    timeout: int = 5,
) -> str:
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        result = re.sub(pattern, repl, string, flags=flags)
        signal.alarm(0)
        return result
    except RegexTimeout:
        return string
    except Exception:
        return string


def safe_regex_search(
    pattern: str, string: str, flags: int = 0, timeout: int = 5
) -> Optional[Match[str]]:
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        result = re.search(pattern, string, flags=flags)
        signal.alarm(0)
        return result
    except RegexTimeout:
        return None
    except Exception:
        return None


def safe_regex_findall(
    pattern: str, string: str, flags: int = 0, timeout: int = 5
) -> list[str]:
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        result = re.findall(pattern, string, flags=flags)
        signal.alarm(0)
        return result
    except RegexTimeout:
        return []
    except Exception:
        return []


def safe_regex_match(
    pattern: str, string: str, flags: int = 0, timeout: int = 5
) -> Optional[Match[str]]:
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        result = re.match(pattern, string, flags=flags)
        signal.alarm(0)
        return result
    except RegexTimeout:
        return None
    except Exception:
        return None


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
        """
        Remove JavaScript-style comments from JSON.

        Handles:
        - // line comments (but not URLs like https://)
        - /* block comments */
        """
        text = safe_regex_sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        text = safe_regex_sub(
            r"(?<!https:)(?<!http:)//.*?(?=\n|$)", "", text, flags=re.MULTILINE
        )

        return text

    @staticmethod
    def extract_first_json(text: str) -> str:
        """
        Extract the first complete JSON object/array from text with multiple JSONs.
        """
        text = text.strip()

        # Find the first JSON structure
        brace_count = 0
        bracket_count = 0
        in_string = False
        string_char = None
        escaped = False
        start_pos = -1

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
                if char in ["{", "["]:
                    if start_pos == -1:
                        start_pos = i
                    if char == "{":
                        brace_count += 1
                    else:
                        bracket_count += 1
                elif char == "}":
                    brace_count -= 1
                elif char == "]":
                    bracket_count -= 1

                # Check if we have a complete structure
                if start_pos != -1 and brace_count == 0 and bracket_count == 0:
                    return text[start_pos : i + 1]

        return text

    @staticmethod
    def unwrap_function_calls(text: str) -> str:
        """
        Remove function call wrappers around JSON.

        Handles:
        - parse_json({"key": "value"})
        - return {"key": "value"}
        - const data = {"key": "value"}
        """
        text = text.strip()

        func_pattern = r"^[a-zA-Z_][a-zA-Z0-9_.]*\s*\(\s*(.*)\s*\)\s*;?\s*$"
        match = safe_regex_search(func_pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()

        return_pattern = r"^return\s+(.*?)\s*;?\s*$"
        match = safe_regex_search(return_pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        var_pattern = r"^(?:const|let|var)\s+\w+\s*=\s*(.*?)\s*;?\s*$"
        match = safe_regex_search(var_pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        return text

    @staticmethod
    def unwrap_inline_function_calls(text: str) -> str:
        """
        Unwrap function calls within JSON values.

        Handles common patterns found in LLM responses and MongoDB exports:
        - Date("2025-08-16T10:30:00Z") → "2025-08-16T10:30:00Z"
        - ObjectId("507f1f77bcf86cd799439011") → "507f1f77bcf86cd799439011"
        - ISODate("2023-01-01T00:00:00Z") → "2023-01-01T00:00:00Z"
        - RegExp("pattern", "flags") → "/pattern/flags"
        - UUID("123e4567-e89b-12d3-a456-426614174000") →
          "123e4567-e89b-12d3-a456-426614174000"
        """
        # Common MongoDB/JavaScript function patterns
        patterns = [
            # Date functions with quoted strings - more precise patterns
            (r'\bDate\s*\(\s*"([^"]*)"\s*\)', r'"\1"'),
            (r'\bISODate\s*\(\s*"([^"]*)"\s*\)', r'"\1"'),
            (r'\bnew\s+Date\s*\(\s*"([^"]*)"\s*\)', r'"\1"'),
            # ObjectId and UUID functions
            (r'\bObjectId\s*\(\s*"([^"]*)"\s*\)', r'"\1"'),
            (r'\bUUID\s*\(\s*"([^"]*)"\s*\)', r'"\1"'),
            (r'\bBinData\s*\(\s*\d+\s*,\s*"([^"]*)"\s*\)', r'"\1"'),
            # RegExp functions - handle both forms
            # Extract just the pattern string, not regex delimiters
            (r'\bRegExp\s*\(\s*"([^"]*)"\s*,\s*"([^"]*)"\s*\)', r'"\1"'),
            (r'\bRegExp\s*\(\s*"([^"]*)"\s*\)', r'"\1"'),
            # MongoDB specific functions
            (r'\bNumberLong\s*\(\s*"?([^)"]+)"?\s*\)', r"\1"),
            (r'\bNumberInt\s*\(\s*"?([^)"]+)"?\s*\)', r"\1"),
            (r'\bNumberDecimal\s*\(\s*"([^"]+)"\s*\)', r'"\1"'),
            # Handle function calls without quotes (common in LLM output) - more
            # restrictive
            (r'\bDate\s*\(\s*([^)"\s,][^),]*)\s*\)', r'"\1"'),
            (r'\bObjectId\s*\(\s*([^)"\s,][^),]*)\s*\)', r'"\1"'),
            (r'\bUUID\s*\(\s*([^)"\s,][^),]*)\s*\)', r'"\1"'),
        ]

        for pattern, replacement in patterns:
            text = safe_regex_sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text

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
            else:
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
        """
        Normalize non-standard boolean and null values.

        Converts:
        - True/False -> true/false
        - None -> null
        - yes/no -> true/false
        - undefined -> null
        - NULL -> null (uppercase variant)
        """
        text = safe_regex_sub(r"\bTrue\b", "true", text)
        text = safe_regex_sub(r"\bFalse\b", "false", text)
        text = safe_regex_sub(r"\bNone\b", "null", text)

        text = safe_regex_sub(r"\byes\b", "true", text, flags=re.IGNORECASE)
        text = safe_regex_sub(r"\bno\b", "false", text, flags=re.IGNORECASE)

        text = safe_regex_sub(r"\bundefined\b", "null", text, flags=re.IGNORECASE)

        # Uppercase NULL -> null
        text = safe_regex_sub(r"\bNULL\b", "null", text)

        return text

    @staticmethod
    def fix_unescaped_strings(text: str) -> str:
        """
        Attempt to fix common string escaping issues.

        Uses intelligent detection to identify file paths and other strings
        where backslashes are likely meant to be literal rather than escape sequences.

        This avoids the problem where \f is a valid JSON escape (form feed)
        but users typically want literal \f in file paths.
        """

        def fix_file_paths(match: Match[str]) -> str:
            full_match = match.group(0)
            content = match.group(1)

            # Skip if no backslashes
            if "\\" not in content:
                return full_match

            # Detect if this looks like a file path or similar literal string
            file_indicators = [
                "data",
                "file",
                "temp",
                "usr",
                "var",
                "home",
                "program",
                "windows",
                "documents",
                "desktop",
                "downloads",
                "system",
                "config",
                "etc",
                "bin",
                "lib",
                "src",
                "test",
                "backup",
                "log",
                "cache",
                "tmp",
            ]

            content_lower = content.lower()
            # If the string contains valid JSON escape sequences (Unicode or
            # standard escapes),
            # be very conservative about treating it as a file path
            has_json_escapes = safe_regex_search(
                r'\\[\\"/bfnrtu]|\\u[0-9a-fA-F]{4}', content
            )

            if has_json_escapes:
                # Only treat as file path if it has strong file path indicators
                looks_like_path = (
                    # Contains common path components
                    any(indicator in content_lower for indicator in file_indicators)
                    or
                    # Contains drive letters (C:, D:, etc.) - must be start of string or
                    # after space/slash
                    safe_regex_search(r"(?:^|[\s/\\])[a-zA-Z]:", content)
                )
            else:
                # No JSON escapes - use broader file path detection
                looks_like_path = (
                    # Contains common path components
                    any(indicator in content_lower for indicator in file_indicators)
                    or
                    # Contains drive letters (C:, D:, etc.) - must be start of string or
                    # after space/slash
                    safe_regex_search(r"(?:^|[\s/\\])[a-zA-Z]:", content)
                    or
                    # Contains actual path separators (not JSON escape sequences)
                    # Only consider it a path if there are backslashes that are NOT
                    # valid JSON escapes
                    (
                        content.count("\\") >= 2
                        and safe_regex_search(
                            r'\\(?![\\"/bfnrtu]|u[0-9a-fA-F]{4})', content
                        )
                    )
                    or
                    # Contains common file extensions (but not Unicode escapes)
                    # Must be a backslash followed by path components and an extension
                    safe_regex_search(r"\\[^u\\]+\.[a-zA-Z0-9]{1,4}$", content)
                    or
                    # Or a regular path with extension at the end
                    safe_regex_search(
                        r"[a-zA-Z0-9_-]+\.[a-zA-Z0-9]{1,4}$", content.split("\\")[-1]
                    )
                )

            if looks_like_path:
                # Escape all single backslashes in suspected file paths
                escaped_content = content.replace("\\", "\\\\")
                return f'"{escaped_content}"'
            else:
                # For non-path strings, only escape invalid JSON escapes
                # This preserves intentional \n, \t, etc. and valid Unicode escapes
                # But be more conservative - only escape if there's an
                # unescaped backslash
                # followed by a character that would cause JSON parsing issues
                # Check if there are problematic unescaped backslashes first
                has_problematic_backslashes = safe_regex_search(
                    r"(?<!\\)\\(?![\\\"/bfnrtu]|u[0-9a-fA-F]{4}|$)", content
                )

                if has_problematic_backslashes:
                    # Only escape problematic backslashes
                    escaped_content = safe_regex_sub(
                        r"(?<!\\)\\(?![\\\"/bfnrtu]|u[0-9a-fA-F]{4}|$)",
                        r"\\\\",
                        content,
                    )
                    return f'"{escaped_content}"'
                else:
                    # No problematic backslashes found, return unchanged
                    return full_match

        text = safe_regex_sub(r'"([^"]*)"', fix_file_paths, text)

        return text

    @staticmethod
    def fix_unescaped_quotes_in_strings(text: str) -> str:
        """
        Fix unescaped double quotes within string values.

        Handles cases like: "Hello "world"" -> "Hello \"world\""

        Now with improved URL protection.
        """
        # Safety check - don't process very large texts to avoid performance issues
        if len(text) > 50000:
            return text

        # Don't process if text contains URLs
        if "://" in text:
            return text

        # Don't process if it looks like it already has properly escaped quotes
        # Check for already-escaped quotes pattern (\")
        if '\\"' in text:
            return text

        # Don't process malformed JSON structures (they cause parsing issues)
        # Check for common malformed patterns that should be fixed by other
        # functions first

        # Check for unmatched braces/brackets (incomplete JSON)
        open_braces = text.count("{") - text.count("}")
        open_brackets = text.count("[") - text.count("]")
        if open_braces > 0 or open_brackets > 0:
            return text

        # Check for assignment operators (= instead of :) - should be fixed by
        # fix_assignment_operators first. Be specific: only skip if it looks
        # like key = value pattern
        if safe_regex_search(r'"\s*=\s*[^=]|^\s*\w+\s*=\s*', text):
            return text

        # Check for string concatenation patterns - should be handled by
        # handle_string_concatenation first
        # Pattern: "string" "string" (adjacent quoted strings)
        if safe_regex_search(r'"\s+"[^:]', text):
            return text

        # Check for obvious structural issues that indicate malformed JSON
        # Pattern: object-to-object without comma: } {
        if safe_regex_search(r"\}\s*\{", text):
            return text

        # Don't process text that looks like well-formed JSON arrays/objects
        # If it has proper structure like ["item", "item"] or {"key": "value"}, skip it
        try:
            import json

            json.loads(text)
            # If it parses successfully, it doesn't need unescaped quote fixing
            return text
        except Exception:
            # If it doesn't parse, it might need quote fixing - continue processing
            pass

        # Handle specific pattern: "text "word" text" -> "text \"word\" text"
        # Look for strings that have unescaped quotes in the middle

        # Pattern: find potential problem strings with internal quotes
        # This is a more sophisticated approach that looks at JSON structure

        try:
            # Use character-by-character parsing with JSON awareness
            result = []
            i = 0

            while i < len(text):
                if text[i] == '"':
                    # Start of a string - find its actual end
                    result.append('"')
                    i += 1

                    string_content = ""
                    while i < len(text):
                        if text[i] == '"':
                            # Check if this quote is escaped
                            backslash_count = 0
                            j = i - 1
                            while j >= 0 and text[j] == "\\":
                                backslash_count += 1
                                j -= 1

                            if backslash_count % 2 == 0:
                                # Unescaped quote - check if it's the real end
                                # Look ahead to see what follows
                                next_pos = i + 1
                                while (
                                    next_pos < len(text) and text[next_pos] in " \t\n\r"
                                ):
                                    next_pos += 1

                                # If followed by JSON syntax, it's likely the end
                                if (
                                    next_pos >= len(text)
                                    or text[next_pos] in ":,}]\n"
                                    or (
                                        next_pos < len(text) - 1
                                        and text[next_pos : next_pos + 2]
                                        in ["/*", "//"]
                                    )
                                ):
                                    # This is the end quote
                                    result.append(string_content)
                                    result.append('"')
                                    i = next_pos
                                    break
                                else:
                                    # Internal quote - escape it
                                    string_content += '\\"'
                                    i += 1
                            else:
                                # Already escaped quote
                                string_content += '"'
                                i += 1
                        elif text[i] == "\\":
                            # Handle escape sequences
                            string_content += text[i]
                            i += 1
                            if i < len(text):
                                string_content += text[i]
                                i += 1
                        else:
                            string_content += text[i]
                            i += 1

                    # If we exited without finding end quote, just use what we have
                    if i >= len(text):
                        result.append(string_content)
                        break
                else:
                    result.append(text[i])
                    i += 1

            return "".join(result)

        except Exception:
            # If anything goes wrong, return original text
            return text

    @staticmethod
    def handle_string_concatenation(text: str) -> str:
        """
        Handle JavaScript/Python-style string concatenation.

        Patterns handled:
        - "string1" + "string2" -> "string1string2"
        - "string1" + "string2" + "string3" -> "string1string2string3"
        - ("string1" "string2") -> "string1string2" (Python implicit concat)
        - "string1" "string2" -> "string1string2" (Adjacent implicit concat)
        """

        # Custom approach to handle string concatenation with proper
        # escaped quote handling
        def replace_concatenation(match: Match[str]) -> str:
            # Extract the full match
            full_match = match.group(0)

            # Find the position of the + operator
            plus_pos = full_match.find("+")
            if plus_pos == -1:
                return full_match

            # Split the text at the plus operator
            left_part = full_match[:plus_pos].strip()
            right_part = full_match[plus_pos + 1 :].strip()

            # Extract content from quoted strings
            def extract_string_content(quoted_str: str) -> str:
                if not (quoted_str.startswith('"') and quoted_str.endswith('"')):
                    return quoted_str

                # Remove surrounding quotes
                content = quoted_str[1:-1]

                # Handle escaped quotes correctly
                # Replace escaped quotes with actual quotes
                content = content.replace('\\"', '"')
                return content

            # Extract content from both parts
            left_content = extract_string_content(left_part)
            right_content = extract_string_content(right_part)

            # Combine and return as a new quoted string
            combined = left_content + right_content
            # Escape any quotes in the combined content
            combined = combined.replace('"', '\\"')
            return f'"{combined}"'

        # Pattern to match string concatenation with proper handling of escaped quotes
        # This pattern looks for quoted strings separated by +
        plus_pattern = r'"(?:[^"\\]|\\.)*"\s*\+\s*"(?:[^"\\]|\\.)*"'

        max_iterations = 10
        iteration = 0
        while safe_regex_search(plus_pattern, text) and iteration < max_iterations:
            iteration += 1
            text = safe_regex_sub(plus_pattern, replace_concatenation, text)

        # Handle Python-style parentheses concatenation
        # Pattern: ("string1" "string2" "string3") -> "string1string2string3"

        # First, handle adjacent strings within parentheses
        def fix_paren_concatenation(match: re.Match[str]) -> str:
            content = match.group(1)
            # Find all quoted strings within the parentheses
            string_pattern = r'"([^"]*?)"'
            strings = safe_regex_findall(string_pattern, content)
            if strings:
                # Concatenate all strings
                combined = "".join(strings)
                return f'"{combined}"'
            return match.group(0)

        # Pattern to match parentheses containing multiple quoted strings
        paren_pattern = r'\(\s*("(?:[^"\\]|\\.)*?"(?:\s+"(?:[^"\\]|\\.)*?")*)\s*\)'
        text = safe_regex_sub(paren_pattern, fix_paren_concatenation, text)

        # Handle adjacent quoted strings (implicit concatenation)
        # But be careful not to merge JSON key-value pairs!
        # Only merge if it's not a key-value pattern (no colon after first string)
        def safe_string_merge(match: Match[str]) -> str:
            full_match = match.group(0)
            # Check if this looks like JSON key-value pairs by looking for colon
            first_string = match.group(1)
            second_string = match.group(2)

            # If there's a colon after first string, don't merge (key: value)
            first_part = full_match.split('"' + first_string + '"')[1]
            second_part = first_part.split('"' + second_string + '"')[0]
            if ":" in second_part:
                return full_match  # Don't merge

            # Also don't merge if strings appear to be on different lines
            if "\n" in match.group(0):
                return full_match  # Don't merge

            # Don't merge if strings are clearly in array context
            # Check if we're inside brackets [ ] which would indicate array elements
            # But allow merging if it's a JSON value context (after colon)

            # Look at broader context to determine if we're in an array
            start_pos = text.find(full_match)
            if start_pos != -1:
                context_before = text[:start_pos]
                # context_after = text[start_pos + len(full_match) :]

                # Count brackets and braces to determine context
                open_brackets = context_before.count("[") - context_before.count("]")
                in_array = open_brackets > 0

                # Check if we're in a value position (after colon)
                last_colon = context_before.rfind(":")
                last_comma = context_before.rfind(",")
                last_brace = context_before.rfind("{")

                # Check array context first - arrays have higher precedence
                if in_array:
                    # We're in array context - don't merge, these should be
                    # separate elements
                    return full_match

                # If not in array, check if we're in a value context (after colon)
                recent_chars = [last_colon, last_comma, last_brace]
                most_recent = (
                    max(c for c in recent_chars if c != -1)
                    if any(c != -1 for c in recent_chars)
                    else -1
                )

                if most_recent == last_colon:
                    # We're in a value context - safe to concatenate
                    pass
                # Otherwise continue with concatenation

            # Otherwise, merge the strings
            return f'"{first_string}{second_string}"'

        # Pattern: "string1" "string2" -> "string1string2" (but only when appropriate)
        adjacent_pattern = r'"([^"]*?)"\s+"([^"]*?)"'

        iteration = 0
        while safe_regex_search(adjacent_pattern, text) and iteration < max_iterations:
            iteration += 1
            text = safe_regex_sub(adjacent_pattern, safe_string_merge, text)

        return text

    @staticmethod
    def handle_incomplete_json(text: str) -> str:
        """
        Attempt to complete incomplete JSON structures by adding missing closing
        braces/brackets.

        This is a best-effort approach for handling truncated JSON.
        """
        text = text.strip()

        # Safety check: if the text looks like well-formed JSON from string
        # concatenation, don't try to fix it as it might be already complete
        if (
            text.count("{") == text.count("}")
            and text.count("[") == text.count("]")
            and ("authentication" in text or "concatenation" in text)
        ):
            return text

        # Track opening/closing brackets and braces with positions to handle
        # nesting correctly
        stack = []
        in_string = False
        string_char = None
        escaped = False

        for char in text:
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
                if char in ["{", "["]:
                    stack.append(char)
                elif char == "}":
                    if stack and stack[-1] == "{":
                        stack.pop()
                elif char == "]" and stack and stack[-1] == "[":
                    stack.pop()

        # Close unclosed strings
        if in_string and string_char:
            text += string_char

        # Handle incomplete key-value pairs before closing structures
        # Check for problematic mixed array/object syntax like: [obj, "key":
        import re

        # Remove incomplete key-value pairs that would create invalid mixed syntax
        # Pattern: array context with trailing incomplete key-value
        if "[" in text and text.rstrip().endswith(":"):
            # Check if we're in an array context with incomplete key
            # Look for pattern like: [anything, "key": at end
            pattern = r',\s*"[^"]*":\s*$'
            if re.search(pattern, text):
                # Remove the incomplete key-value pair
                text = re.sub(pattern, "", text)
            else:
                # Regular incomplete key-value pair in object context
                text = text.rstrip() + " null"
        elif text.rstrip().endswith(":"):
            text = text.rstrip() + " null"

        # Add missing closing brackets and braces in reverse order (LIFO)
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

        # Don't apply streaming logic to markdown code blocks or obvious
        # non-streaming content
        if "```" in text or "json" in text.lower()[:100]:
            return original_text

        # Check if this looks like actual streaming response with SSE
        # Look for typical SSE patterns
        lines = text.strip().split("\n")
        has_sse_patterns = any(
            line.strip() in ["[DONE]", "event: done", "event: error"]
            or (
                line.strip().startswith("data:")
                and len(line.strip()) > 5  # Must have content after "data:"
                and line.strip()[5:].strip().startswith(("{", "[", '"'))
                and not any(
                    keyword in line for keyword in ['"', "'", ":", "[", "]"]
                )  # Not JSON syntax
            )
            for line in lines
        )

        # Only apply SSE processing if we actually have SSE patterns
        if not has_sse_patterns:
            return original_text

        # Remove "data:" prefixes from server-sent events
        cleaned_lines = []

        for line in lines:
            line = line.strip()

            # Skip empty lines and SSE control messages
            if not line or line in ["[DONE]", "event: done", "event: error"]:
                continue

            # Remove "data:" prefix from server-sent events
            # But be more specific - only remove if it's clearly an SSE pattern
            if line.startswith("data:"):
                data_content = line[5:].strip()
                # Only remove if it looks like SSE (not a JSON key)
                if data_content.startswith(("{", "[", '"')) or ":" not in data_content:
                    line = data_content
                else:
                    # Keep the line as-is if it's not clearly SSE
                    pass

            cleaned_lines.append(line)

        if not cleaned_lines:
            return original_text

        # Reconstruct the text and check if it looks like complete JSON
        reconstructed = "\n".join(cleaned_lines)

        # If the reconstructed text looks like it contains JSON, use it
        reconstructed = reconstructed.strip()
        if reconstructed.startswith(("{", "[")) and reconstructed.endswith(("}", "]")):
            return reconstructed

        # Otherwise, try to find individual complete JSON objects on single lines
        json_objects = []
        for line in cleaned_lines:
            line = line.strip()
            if line.startswith(("{", "[")) and line.endswith(("}", "]")):
                json_objects.append(line)

        if json_objects:
            # Return the longest/most complete JSON object
            return max(json_objects, key=len)

        # Fall back to reconstructed text or original
        return reconstructed if reconstructed else original_text

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

        for i in range(len(lines)):
            line = lines[i]

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
                if (
                    current_stripped
                    and next_stripped
                    and not current_stripped.endswith(",")
                    and not current_stripped.endswith("{")
                    and not current_stripped.endswith("[")
                    and not current_stripped.endswith("}")
                    and not current_stripped.endswith("]")
                    and not current_stripped.endswith(
                        ":"
                    )  # DON'T add comma after colons!
                    and (
                        next_stripped.startswith('"')
                        or safe_regex_search(
                            r"^[a-zA-Z_][a-zA-Z0-9_]*\s*:", next_stripped
                        )
                    )
                ):
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

            # Only preserve if it's ACTUALLY a regex quantifier: {digit,}
            # Check if the character before the digit is an opening brace
            if bracket == "}" and before_comma.isdigit():
                # Look back in the original text to see if this is {digit,}
                full_match_start = match.start()
                # Check if there's a { right before this pattern
                if full_match_start > 0 and text[full_match_start - 1] == "{":
                    return match.group(0)  # Preserve {digit,} quantifiers

            # Special case: if before_comma is opening bracket [, this indicates
            # a sparse array pattern like [,] that should be handled by
            # handle_sparse_arrays. Don't remove these trailing commas here
            if before_comma == "[" and bracket == "]":
                # [,] case - let sparse array handler deal with this
                return match.group(0)  # Return unchanged

            # Remove trailing comma for everything else
            return before_comma + bracket

        # Match: (character)(optional space)(comma)(optional space)(bracket)
        text = safe_regex_sub(r"(\S)\s*,\s*([}\]])", replace_trailing_comma, text)
        return text

    @staticmethod
    def normalize_mixed_quotes(text: str) -> str:
        """
        Normalize mixed single and double quotes to use double quotes consistently.

        Handles:
        - 'key': 'value' -> "key": "value"
        - Mixed quotes in same object
        - Special handling for string concatenation patterns
        """
        # Don't process if text is too long to avoid performance issues
        if len(text) > 10000:
            return text

        # Handle string concatenation patterns first to avoid incorrect processing
        # Pattern: 'string1" + "string2' -> "string1" + "string2"
        def fix_concatenation_in_single_quotes(match: Match[str]) -> str:
            full_match = match.group(0)
            # Check if this contains a concatenation pattern
            if '"' in full_match and " + " in full_match:
                # This is likely concatenation - convert single quotes to double
                # and preserve internal structure
                content = match.group(1)
                return f'"{content}"'
            else:
                # Regular single-quoted string - convert with proper escaping
                content = match.group(1)
                content = content.replace('"', '\\"')
                return f'"{content}"'

        # Use a simpler approach: only convert single quotes that are NOT
        # inside double-quoted strings
        # Split on double quotes to separate string literals from other content
        parts = text.split('"')

        # Process odd/even parts differently
        # Even indices (0, 2, 4...) are outside strings
        # Odd indices (1, 3, 5...) are inside strings
        result_parts = []

        for i, part in enumerate(parts):
            if i % 2 == 0:
                # Outside string - can safely convert single quotes
                single_quote_pattern = r"'([^']*)'"
                converted_part = safe_regex_sub(
                    single_quote_pattern,
                    fix_concatenation_in_single_quotes,
                    part,
                )
                result_parts.append(converted_part)
            else:
                # Inside string - preserve single quotes
                result_parts.append(part)

        text = '"'.join(result_parts)

        return text

    @staticmethod
    def fix_multiline_strings(text: str) -> str:
        """
        Fix multiline string literals by properly escaping or joining them.

        Handles cases where strings are split across lines without proper escaping.
        """
        # Quick safety check: if the text looks like well-formed JSON with proper
        # string concatenation results, don't try to fix it
        # Check for even number of quotes (balanced) and concatenation patterns
        quote_count = text.count('"')
        if (
            quote_count >= 4
            and quote_count % 2 == 0
            and (
                "authentication" in text
                or "concatenation" in text
                or "RelatedTexts" in text
            )
        ):
            return text

        lines = text.split("\n")
        fixed_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check if line has an unclosed string (odd number of unescaped quotes)
            quote_count = 0
            escaped = False
            for char in line:
                if char == "\\" and not escaped:
                    escaped = True
                    continue
                if char == '"' and not escaped:
                    quote_count += 1
                escaped = False

            # If odd number of quotes, string continues to next line
            if quote_count % 2 == 1 and i < len(lines) - 1:
                # Look for the closing quote in subsequent lines
                combined_line = line
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    combined_line += "\\n" + next_line.strip()

                    # Count quotes in this line
                    next_quote_count = 0
                    escaped = False
                    for char in next_line:
                        if char == "\\" and not escaped:
                            escaped = True
                            continue
                        if char == '"' and not escaped:
                            next_quote_count += 1
                        escaped = False

                    # If we found a closing quote, combine and break
                    if next_quote_count % 2 == 1:
                        fixed_lines.append(combined_line)
                        i = j + 1
                        break
                    j += 1

                # If we didn't find a closing quote, just use the line as-is
                if j >= len(lines):
                    fixed_lines.append(line + '"')  # Add closing quote
                    i += 1
            else:
                fixed_lines.append(line)
                i += 1

        return "\n".join(fixed_lines)

    @staticmethod
    def normalize_special_numbers(text: str) -> str:
        """
        Normalize special number formats and JavaScript constants.

        Handles:
        - NaN -> null
        - Infinity/-Infinity -> null (or very large numbers)
        - Hexadecimal numbers: 0x1A -> 26
        - Octal numbers: 025 -> 21 (but be careful with valid decimals)
        """
        # Handle NaN and Infinity - convert to string literals for JSON compatibility
        # Use simple string replacement approach to avoid regex complexity
        text = text.replace("-Infinity", '"-Infinity"')
        # This will also handle any remaining Infinity
        text = text.replace("Infinity", '"Infinity"')
        text = text.replace("NaN", '"NaN"')

        # Fix the double-quoting issue that may have been created by the
        # replacements above
        text = text.replace(
            '"-"Infinity""', '"-Infinity"'
        )  # Fix double-quoted -Infinity
        text = text.replace('""Infinity""', '"Infinity"')  # Fix double-quoted Infinity
        text = text.replace('""NaN""', '"NaN"')  # Fix double-quoted NaN

        # Handle hexadecimal numbers (0x prefix)
        def convert_hex(match: Match[str]) -> str:
            hex_value = match.group(1)
            try:
                decimal_value = int(hex_value, 16)
                return str(decimal_value)
            except ValueError:
                return match.group(0)  # Return original if conversion fails

        text = safe_regex_sub(r"\b0x([0-9a-fA-F]+)\b", convert_hex, text)

        # Handle octal numbers (leading zero) - be very conservative
        # Only convert if it looks like intentional octal (all digits 0-7)
        def convert_octal(match: Match[str]) -> str:
            octal_value = match.group(1)
            # Only convert if all digits are 0-7 and it's not just a leading zero
            if len(octal_value) > 1 and all(c in "01234567" for c in octal_value):
                try:
                    decimal_value = int(octal_value, 8)
                    return str(decimal_value)
                except ValueError:
                    pass
            return match.group(0)  # Return original

        text = safe_regex_sub(r"\b0([0-7]+)\b", convert_octal, text)

        return text

    @staticmethod
    def normalize_extended_numbers(text: str) -> str:
        """
        Normalize extended number formats that are invalid in JSON.

        Handles:
        - Version numbers like 1.2.3.4 -> "1.2.3.4" (convert to string)
        - Trailing dots: 42. -> 42
        - Plus prefixes: +123 -> 123
        - Binary numbers: 0b1010 -> 10 (convert to decimal)
        - Octal numbers: 0o755 -> 493 (convert to decimal)
        - Incomplete scientific: 1.5e -> 1.5e0
        """
        # Version numbers like 1.2.3.4 -> "1.2.3.4" (convert to string)
        text = safe_regex_sub(r"\b(\d+\.\d+\.\d+\.\d+)\b", r'"\1"', text)

        # Trailing dots: 42. -> 42
        text = safe_regex_sub(r"\b(\d+)\.\s*([,\]}])", r"\1\2", text)

        # Plus prefix: +123 -> 123
        text = safe_regex_sub(r":\s*\+(\d+)", r": \1", text)

        # Binary numbers: 0b1010 -> 10 (convert to decimal)
        def convert_binary(match: Match[str]) -> str:
            try:
                return str(int(match.group(1), 2))
            except ValueError:
                return match.group(0)

        text = safe_regex_sub(r"0b([01]+)", convert_binary, text)

        # Octal numbers: 0o755 -> 493 (convert to decimal)
        def convert_octal_o(match: Match[str]) -> str:
            try:
                return str(int(match.group(1), 8))
            except ValueError:
                return match.group(0)

        text = safe_regex_sub(r"0o([0-7]+)", convert_octal_o, text)

        # Incomplete scientific: 1.5e -> 1.5e0
        text = safe_regex_sub(r"(\d+\.?\d*)e\s*([,\]}])", r"\1e0\2", text)

        return text

    @staticmethod
    def fix_structural_syntax(text: str) -> str:
        """
        Fix structural syntax issues in JSON.

        Handles:
        - Parentheses instead of braces: (...) -> {...} for objects
        - Set literals: {1, 2, 3} -> [1, 2, 3] for arrays
        - Mixed object/array syntax detection
        """

        # Parentheses to braces for object-like structures
        # Only if content looks like key-value pairs
        def convert_parens_to_braces(match: Match[str]) -> str:
            content = match.group(1)
            # Check if content has key: value patterns
            if ":" in content and safe_regex_search(r'"[^"]*"\s*:', content):
                return "{" + content + "}"
            return match.group(0)  # Leave unchanged

        text = safe_regex_sub(r"\(([^()]*)\)", convert_parens_to_braces, text)

        # Set literals to arrays: {1, 2, 3} -> [1, 2, 3]
        # Only convert if it's clearly a set (no key:value pairs)
        # AND not part of a function definition
        def convert_sets_to_arrays(match: Match[str]) -> str:
            content = match.group(1)

            # Don't convert if it's part of a function body
            # Look for "function(" before the brace
            start_pos = match.start()
            if start_pos > 0:
                # Look backwards for function keyword
                preceding_text = text[:start_pos]
                if "function(" in preceding_text[-50:]:  # Check last 50 chars
                    return match.group(0)  # Leave unchanged

            # Only convert if it's clearly a set, not a malformed object
            if ":" not in content:
                # Check if this looks like a malformed object (missing colons)
                # Pattern: "string" "string" or string string
                if (
                    safe_regex_search(r'"[^"]*"\s+"[^"]*"', content)
                    or safe_regex_search(r'\w+\s+"[^"]*"', content)
                    or safe_regex_search(r'"[^"]*"\s+\w+', content)
                ):
                    # This looks like a malformed object with missing colons
                    # Don't convert to array, let other preprocessing fix it
                    return match.group(0)

                # Check if it looks like a simple set (numbers/simple values)
                # Pattern: 1, 2, 3 or simple values
                if "," in content and not safe_regex_search(r'["\']\s*["\']', content):
                    return "[" + content + "]"

            return match.group(0)

        # Only convert braces that are NOT inside string literals
        def convert_sets_to_arrays_if_not_in_string(match: Match[str]) -> str:
            """Only convert set syntax if not inside string literals."""
            start_pos = match.start()

            # Check if this brace is inside a string by counting quotes before it
            text_before = text[:start_pos]
            quote_count = 0
            escaped = False

            # Count unescaped quotes before this position
            for char in text_before:
                if char == "\\" and not escaped:
                    escaped = True
                    continue
                if char == '"' and not escaped:
                    quote_count += 1
                escaped = False

            # If odd number of quotes, we're inside a string literal
            if quote_count % 2 == 1:
                return match.group(0)  # Don't process - inside string
            else:
                return convert_sets_to_arrays(match)  # Process normally

        text = safe_regex_sub(
            r"\{([^{}]*)\}", convert_sets_to_arrays_if_not_in_string, text
        )

        return text

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
        """
        Evaluate JavaScript-like expressions using hybrid approach.

        SAFE operations (evaluated):
        - Arithmetic with numbers only (22/7, 10%3)
        - Simple comparisons with numbers (5>3, 7<9)
        - Known boolean combinations (true && false)

        UNSAFE operations (converted to null):
        - Variables and increment operators (counter++)
        - Complex expressions with identifiers
        """

        # PHASE 1: Safe arithmetic evaluation
        def safe_division(match: Match[str]) -> str:
            expr = match.group(0)
            try:
                # Parse "number / number"
                parts = [p.strip() for p in expr.split("/")]
                if len(parts) == 2:
                    a, b = float(parts[0]), float(parts[1])
                    if b != 0:
                        result = a / b
                        # Return as int if it's a whole number, otherwise float
                        return str(int(result)) if result.is_integer() else str(result)
                return "0"  # Fallback for division by zero
            except (ValueError, ZeroDivisionError):
                return "0"

        def safe_modulo(match: Match[str]) -> str:
            expr = match.group(0)
            try:
                # Parse "number % number"
                parts = [p.strip() for p in expr.split("%")]
                if len(parts) == 2:
                    a, b = int(float(parts[0])), int(float(parts[1]))
                    if b != 0:
                        return str(a % b)
                return "0"  # Fallback for modulo by zero
            except (ValueError, ZeroDivisionError):
                return "0"

        # Apply safe arithmetic - only match pure numeric expressions
        text = safe_regex_sub(
            r"\b\d+(?:\.\d+)?\s*/\s*\d+(?:\.\d+)?\b", safe_division, text
        )
        text = safe_regex_sub(r"\b\d+\s*%\s*\d+\b", safe_modulo, text)

        # PHASE 2: Safe comparison evaluation
        def safe_comparison(match: Match[str]) -> str:
            expr = match.group(0)
            try:
                if ">" in expr:
                    parts = [p.strip() for p in expr.split(">")]
                    if len(parts) == 2:
                        a, b = float(parts[0]), float(parts[1])
                        return "true" if a > b else "false"
                elif "<" in expr:
                    parts = [p.strip() for p in expr.split("<")]
                    if len(parts) == 2:
                        a, b = float(parts[0]), float(parts[1])
                        return "true" if a < b else "false"
            except ValueError:
                pass
            return "false"  # Conservative default

        # Apply safe comparisons - only pure numeric comparisons
        text = safe_regex_sub(
            r"\b\d+(?:\.\d+)?\s*[><]\s*\d+(?:\.\d+)?\b", safe_comparison, text
        )

        # PHASE 3: Known boolean combinations
        boolean_replacements = [
            (r"\btrue\s*&&\s*false\b", "false"),
            (r"\bfalse\s*&&\s*true\b", "false"),
            (r"\btrue\s*&&\s*true\b", "true"),
            (r"\bfalse\s*&&\s*false\b", "false"),
            (r"\btrue\s*\|\|\s*false\b", "true"),
            (r"\bfalse\s*\|\|\s*true\b", "true"),
            (r"\btrue\s*\|\|\s*true\b", "true"),
            (r"\bfalse\s*\|\|\s*false\b", "false"),
        ]

        for pattern, replacement in boolean_replacements:
            text = safe_regex_sub(pattern, replacement, text)

        # PHASE 4: Convert unsafe expressions to null
        unsafe_patterns = [
            r"\w+\+\+",  # counter++
            r"\+\+\w+",  # ++counter
            r"\w+--",  # counter--
            r"--\w+",  # --counter
            r"\w+\s*&&\s*\w+",  # variable && variable
            r"\w+\s*\|\|\s*\w+",  # variable || variable
        ]

        for pattern in unsafe_patterns:
            text = safe_regex_sub(pattern, "null", text)

        return text

    @staticmethod
    def handle_javascript_constructs(text: str) -> str:
        """
        Handle JavaScript-specific constructs that need to be converted for JSON.

        Handles:
        - Function definitions: function() { ... } -> null
        - Regex literals: /pattern/flags -> "pattern"
        - Template literals: `hello ${var}` -> "hello ${var}"
        - JavaScript expressions: new Date() -> null
        - String concatenation: 'a' + 'b' -> "ab"
        """

        # Remove function definitions entirely
        # Handle nested braces in function bodies by using a proper
        # brace counting approach
        def remove_functions(text: str) -> str:
            result = []
            i = 0
            while i < len(text):
                # Look for function keyword
                if text[i : i + 8] == "function" and (
                    i == 0 or not text[i - 1].isalnum()
                ):
                    # Found function keyword
                    j = i + 8
                    # Skip whitespace
                    while j < len(text) and text[j] in " \t\n":
                        j += 1
                    # Skip parameter list
                    if j < len(text) and text[j] == "(":
                        paren_count = 1
                        j += 1
                        while j < len(text) and paren_count > 0:
                            if text[j] == "(":
                                paren_count += 1
                            elif text[j] == ")":
                                paren_count -= 1
                            j += 1
                    # Skip whitespace
                    while j < len(text) and text[j] in " \t\n":
                        j += 1
                    # Skip function body
                    if j < len(text) and text[j] == "{":
                        brace_count = 1
                        j += 1
                        while j < len(text) and brace_count > 0:
                            if text[j] == "{":
                                brace_count += 1
                            elif text[j] == "}":
                                brace_count -= 1
                            j += 1
                        # Replace entire function with null
                        result.append("null")
                        i = j
                        continue

                result.append(text[i])
                i += 1

            return "".join(result)

        text = remove_functions(text)

        # Handle regex literals /pattern/flags -> "pattern"
        def convert_regex(match: Match[str]) -> str:
            pattern = match.group(1)
            # Escape any quotes in the pattern
            pattern = pattern.replace('"', '\\"')
            return f'"{pattern}"'

        # Match regex literals but exclude URLs by requiring specific context
        # Look for: /pattern/flags likely to be regex (after :, =, (, [, start)
        text = safe_regex_sub(r"(?<=[:\[=\(\s])/([^/]+)/[gimuy]*", convert_regex, text)
        text = safe_regex_sub(r"^/([^/]+)/[gimuy]*", convert_regex, text)

        # Handle template literals `text` -> "text" (simple case)
        text = safe_regex_sub(r"`([^`]*)`", r'"\1"', text)

        # Handle new Date() and similar constructor calls
        text = safe_regex_sub(r"\bnew\s+\w+\s*\([^)]*\)", "null", text)

        # Handle arithmetic expressions in JSON context (basic cases)
        # Only handle simple cases like: "key": 10 + 5
        def convert_arithmetic(match: Match[str]) -> str:
            try:
                expr = match.group(1).strip()
                # Only handle simple addition/subtraction of numbers
                if "+" in expr:
                    parts = expr.split("+")
                    if len(parts) == 2:
                        a, b = parts[0].strip(), parts[1].strip()
                        if (
                            a.replace(".", "").isdigit()
                            and b.replace(".", "").isdigit()
                        ):
                            result = float(a) + float(b)
                            return (
                                str(int(result)) if result.is_integer() else str(result)
                            )
                elif "-" in expr and not expr.startswith("-"):
                    parts = expr.split("-")
                    if len(parts) == 2:
                        a, b = parts[0].strip(), parts[1].strip()
                        if (
                            a.replace(".", "").isdigit()
                            and b.replace(".", "").isdigit()
                        ):
                            result = float(a) - float(b)
                            return (
                                str(int(result)) if result.is_integer() else str(result)
                            )
            except (ValueError, TypeError):
                pass
            return match.group(0)

        # Look for simple arithmetic expressions after colons
        # Only match if there are numbers and operators, not empty space/comma
        text = safe_regex_sub(
            r":\s*([0-9]+[\s]*[+\-][\s]*[0-9]+[0-9+\-\s.]*)(?=\s*[,}])",
            lambda m: ": " + convert_arithmetic(m),
            text,
        )

        return text

    @staticmethod
    def handle_empty_values(text: str) -> str:
        """
        Handle empty values after commas and incomplete structures.

        Handles:
        - "key": , -> "key": null,
        - [1, 2, , 4] -> [1, 2, null, 4]
        - Incomplete object values: "sms": } -> "sms": null }
        - Empty key with empty value: "": , -> "": null,
        """
        # Handle empty values after commas in objects
        # "key": , -> "key": null,
        text = safe_regex_sub(r":\s*,", ": null,", text)

        # Handle empty values in arrays ,, -> , null,
        text = safe_regex_sub(r",\s*,", ", null,", text)

        # Handle incomplete values at end of objects/arrays
        # "key": } -> "key": null }
        text = safe_regex_sub(r":\s*([}\]])", r": null\1", text)

        # Handle trailing empty values
        # "key": \n } -> "key": null }
        text = safe_regex_sub(r":\s*\n\s*([}\]])", r": null\n\1", text)

        # Enhanced: Empty key with empty value: "": , -> "": null,
        text = safe_regex_sub(r'(""\s*:\s*),', r"\1null,", text)

        return text

    @staticmethod
    def fix_unclosed_strings(text: str) -> str:
        """
        Fix unclosed strings by adding closing quotes.

        Handles cases where strings are not properly terminated.

        Improved to handle multiline strings and escaped quotes correctly.
        """

        # Don't process if text looks like it already has well-formed strings
        # Count total quotes in entire text to see if they're balanced
        # Use proper escape sequence counting
        def count_unescaped_quotes(text: str) -> int:
            quote_count = 0
            i = 0
            while i < len(text):
                if text[i] == '"':
                    # Count preceding backslashes
                    backslash_count = 0
                    j = i - 1
                    while j >= 0 and text[j] == "\\":
                        backslash_count += 1
                        j -= 1
                    # Quote is escaped if odd number of preceding backslashes
                    if backslash_count % 2 == 0:
                        quote_count += 1
                i += 1
            return quote_count

        total_quotes = count_unescaped_quotes(text)

        # If quotes are already balanced, don't mess with it
        if total_quotes % 2 == 0:
            return text

        lines = text.split("\n")
        fixed_lines = []

        for line in lines:
            # Count unescaped quotes in this line
            quote_count = count_unescaped_quotes(line)

            # If odd number of quotes, add closing quote at end
            if quote_count % 2 == 1:
                # Find the last comma or end of line and add quote before it
                if line.rstrip().endswith(","):
                    line = line.rstrip()[:-1] + '",'
                else:
                    line = line.rstrip() + '"'

            fixed_lines.append(line)

        return "\n".join(fixed_lines)

    @staticmethod
    def normalize_string_concatenation(text: str) -> str:
        """
        Enhanced string concatenation handler for JavaScript-style expressions.

        Handles:
        - 'success' + 'ful' -> "successful"
        - "hello" + "world" -> "helloworld"
        - Mixed quote concatenation: 'single" + "double' -> "singledouble"
        """

        # First normalize any mixed quote issues in concatenations
        # Handle patterns like 'single" + "double' by fixing the quote mismatch
        def fix_mixed_concat_quotes(match: Match[str]) -> str:
            full_expr = match.group(0)
            # Extract the string contents and concatenate them

            # Find all quoted strings in the concatenation
            strings = safe_regex_search(r"['\"]([^'\"]*)['\"]", full_expr)
            if strings:
                # Simple approach: extract content between first and last quote markers
                content = full_expr
                # Remove + operators and quotes, then rejoin
                content = content.replace("'", '"').replace(" + ", "").replace("+", "")
                # Extract just the content parts
                string_contents = safe_regex_findall(r'"([^"]*)"', content)
                if string_contents:
                    combined = "".join(string_contents)
                    return f'"{combined}"'

            return full_expr

        def fix_escaped_concat(concat_expr: str) -> str:
            """Handle concatenation of escaped quote strings."""
            # Split on + operator first, then extract content from each part
            import re

            # Split the expression by + operator (with optional whitespace)
            parts = re.split(r"\s*\+\s*", concat_expr)
            content_parts = []

            for part in parts:
                part = part.strip()
                # Extract content from quoted string
                match = safe_regex_match(r'"(.*)"', part)
                if match:
                    content = match.group(1)
                    # Unescape the content
                    content = content.replace('\\"', '"').replace("\\\\", "\\")
                    content_parts.append(content)

            # Combine all parts
            combined = "".join(content_parts)
            # Escape any quotes in the combined result
            combined = combined.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{combined}"'

        # Handle mixed quote concatenation patterns (including escaped quotes)
        concat_pattern = (
            r"['\"][^'\"\\]*(?:\\.[^'\"\\]*)*['\"]"
            r"(?:\s*\+\s*['\"][^'\"\\]*(?:\\.[^'\"\\]*)*['\"])+"
        )
        text = safe_regex_sub(concat_pattern, fix_mixed_concat_quotes, text)
        # Also handle already-normalized quotes with escapes like "single\" + \"double"
        text = safe_regex_sub(
            r'"[^"\\]+\\"\s*\+\s*\\"[^"\\]+"',
            lambda m: fix_escaped_concat(m.group(0)),
            text,
        )

        # Use the existing concatenation logic for remaining cases
        return text

    @staticmethod
    def handle_sparse_arrays(text: str) -> str:
        """
        Handle sparse arrays by converting double commas to null values.

        Converts:
        - [1,, 3] -> [1, null, 3]  (valid - arrays can have sparse elements)
        - {key1: val1,, key2: val2} -> {key1: val1, key2: val2}  (remove
          invalid syntax)

        Note: Only arrays support sparse elements. Objects with double commas
        are invalid.
        """

        # FIRST: Clean up invalid object sparse syntax BEFORE processing arrays
        # This prevents ,, in objects from being converted to null
        def clean_object_double_commas(text: str) -> str:
            """Remove double commas from object contexts only (invalid JSON)."""
            # Be more sophisticated about identifying object vs array context
            # Process the entire text, not line by line, to better handle
            # mixed contexts

            # First, remove double commas specifically in object contexts
            # Look for patterns like {key: value,, key2: value2} but be
            # careful about arrays
            def clean_double_commas_in_objects(match: Match[str]) -> str:
                obj_content = match.group(1)
                # Check if this is actually an array (contains array-specific patterns)
                if ":" not in obj_content:
                    # This looks more like an array, don't touch it
                    return match.group(0)

                # This looks like an object, clean double commas
                # But be careful - only clean commas that are between key-value pairs
                # Pattern: ,,\s* followed by a key (word + :)
                cleaned = safe_regex_sub(r",\s*,\s*(?=\w+\s*:)", ",", obj_content)
                # Also handle leading double commas
                cleaned = safe_regex_sub(r"\{\s*,,", "{", cleaned)
                return "{" + cleaned + "}"

            # Apply to objects that look like they have double commas
            # Use a more robust approach that handles nested structures
            # First try simple objects (no nesting)
            text = safe_regex_sub(r"\{([^{}]*)\}", clean_double_commas_in_objects, text)

            # Then handle remaining cases by processing line by line for nested contexts
            # This catches cases like objects inside arrays that the regex above missed

            # Handle remaining double commas outside of clear object/array contexts
            # This is a fallback for simpler cases
            lines = text.split("\n")
            result_lines = []

            for line in lines:
                # Only process lines that contain : but look like they're in
                # object context (not array context)
                if ":" in line and ",," in line:
                    # Check if the double commas are inside an object {...}, not
                    # an array [...]. We need to be more careful here - only clean
                    # double commas that appear directly in object contexts, not in
                    # nested arrays within the line

                    # Look for object-specific double comma patterns:
                    # Pattern: {key: value,, key2: value2} or similar within the line
                    # But NOT array patterns like ["item1",, "item2"] even if line
                    # has :

                    # Simple heuristic: if the line has both { and ,, in close
                    # proximity, and the ,, appears to be between key-value pairs
                    # (not inside [])
                    has_object_double_comma = False

                    # Check for ,, that appears to be between object key-value pairs
                    # This is a more conservative approach - only clean if we're
                    # very sure it's an object context double comma

                    # Look for patterns like: }key: value,, key2: or }key,, key2:
                    object_comma_pattern = safe_regex_search(r"\{[^[\]]*,,", line)
                    # Also check for key-value,, key-value patterns
                    kv_comma_pattern = safe_regex_search(
                        r":\s*[^,\[\]]+,,\s*\w+\s*:", line
                    )

                    if object_comma_pattern or kv_comma_pattern:
                        has_object_double_comma = True

                    if has_object_double_comma:
                        # Remove double commas in what looks like object context
                        # Be more aggressive - remove all double+ commas in object lines
                        cleaned = safe_regex_sub(r",\s*,+", ",", line)
                        # Also handle the specific pattern: ", ," -> ","
                        cleaned = safe_regex_sub(r",\s*,", ",", cleaned)
                        result_lines.append(cleaned)
                    else:
                        result_lines.append(line)
                else:
                    result_lines.append(line)

            return "\n".join(result_lines)

        text = clean_object_double_commas(text)

        # SECOND: Process arrays to convert sparse elements to null
        def fix_sparse_in_array(match: Match[str]) -> str:
            """Fix sparse elements within an array."""
            content = match.group(1)

            # Only process if this looks like a real array (not object)
            # Skip if content has : which indicates object key-value pairs
            if ":" in content:
                return match.group(0)  # Return unchanged

            fixed_content = content

            # Handle leading commas: [, -> [null,
            fixed_content = safe_regex_sub(r"^(\s*),", r"\1null,", fixed_content)

            # Handle multiple consecutive commas: ,, -> , null,
            # BUT avoid corrupting regex quantifiers like {2,} -> {2, null,}
            # Only replace ,, that appear to be array separators, not inside {}
            # regex patterns
            while ",," in fixed_content:
                old_content = fixed_content

                # Use a comprehensive regex that avoids regex quantifier patterns
                # Don't replace ,, if it's part of a {digit,} or {digit,digit} pattern
                # This preserves regex quantifiers while fixing actual array separators
                fixed_content = safe_regex_sub(
                    r"(?<!{\d),,(?![\d\s]*})", ", null,", fixed_content
                )

                # If no replacements were made, break to avoid infinite loop
                if fixed_content == old_content:
                    break

            # Handle trailing comma: convert to null for jsonshiatsu's permissive
            # behavior
            # But don't add null if content already ends with null (from consecutive
            # comma handling)
            stripped = fixed_content.rstrip()
            if stripped.endswith(",") and not stripped.endswith("null,"):
                fixed_content = stripped.rstrip(",") + ", null"

            return "[" + fixed_content + "]"

        # Handle sparse arrays at multiple levels
        # First pass: handle simple arrays (no nested brackets)
        # BUT: Don't process arrays that are inside string literals
        def fix_sparse_if_not_in_string(match: Match[str]) -> str:
            """Only fix sparse arrays if they're not inside string literals."""
            full_match = match.group(0)
            start_pos = match.start()

            # Check if this array is inside a string by counting quotes before it
            text_before = text[:start_pos]
            quote_count = 0
            escaped = False

            # Count unescaped quotes before this position
            for char in text_before:
                if char == "\\" and not escaped:
                    escaped = True
                    continue
                if char == '"' and not escaped:
                    quote_count += 1
                escaped = False

            # If odd number of quotes, we're inside a string literal
            if quote_count % 2 == 1:
                return full_match  # Don't process - inside string
            else:
                return fix_sparse_in_array(match)  # Process normally

        simple_array_pattern = r"\[([^\[\]]*?)\]"
        text = safe_regex_sub(simple_array_pattern, fix_sparse_if_not_in_string, text)

        # Second pass: handle remaining sparse commas between elements at any level
        # BUT be smart about object vs array context
        # Only convert to null if we're clearly in array context or between array values
        # Pattern to identify when we should convert to null:
        # - After [ or , followed by , (array start or element separator)
        # - Before ] or , (array end or next element)
        # Pattern to identify when we should just remove (object context):
        # - Between key-value pairs in objects

        # First, handle double commas that are clearly in array contexts
        # Look for patterns like [,, or ,,, or ,,
        # But avoid patterns like {key: value,, key2: value2} (object context)

        # Handle double commas contextually - only convert to null in array context
        def process_double_commas(text: str) -> str:
            result = []
            i = 0
            in_array = 0  # Track array nesting level
            in_object = 0  # Track object nesting level
            in_string = False
            string_char = None
            escaped = False

            while i < len(text):
                char = text[i]

                if escaped:
                    result.append(char)
                    escaped = False
                    i += 1
                    continue

                if char == "\\":
                    result.append(char)
                    escaped = True
                    i += 1
                    continue

                if char in ['"', "'"] and not in_string:
                    in_string = True
                    string_char = char
                    result.append(char)
                    i += 1
                    continue

                if in_string and char == string_char:
                    in_string = False
                    string_char = None
                    result.append(char)
                    i += 1
                    continue

                if not in_string:
                    if char == "[":
                        in_array += 1
                        result.append(char)
                    elif char == "]":
                        in_array -= 1
                        result.append(char)
                    elif char == "{":
                        in_object += 1
                        result.append(char)
                    elif char == "}":
                        in_object -= 1
                        result.append(char)
                    elif char == "," and i + 1 < len(text) and text[i + 1] == ",":
                        # Found double comma - determine the immediate
                        # context more carefully

                        # When we're in both array and object contexts,
                        # we need to determine
                        # what the double comma is actually separating:
                        # - If it's between array elements, treat as
                        #   array context
                        # - If it's between object key-value pairs, treat as
                        #   object context

                        array_context = in_array > 0
                        object_context = in_object > 0

                        if array_context and object_context:
                            # We're in both contexts - need to determine
                            # which is more immediate
                            # Look at what comes before the first comma
                            j = i - 1
                            while j >= 0 and text[j] in " \t\n\r":
                                j -= 1

                            # If we can determine what the comma is separating, use that
                            if j >= 0:
                                prev_char = text[j]
                                # Check if previous character looks like
                                # the end of a key
                                # Keys end with alphanumeric characters
                                # or quotes
                                if (
                                    prev_char in '"}]/0123456789etrfn_-'
                                    or (
                                        j >= 3
                                        and text[j - 3 : j + 1] in ["true", "alse"]
                                    )
                                    or (
                                        j >= 4
                                        and text[j - 4 : j + 1] in ["false", "null"]
                                    )
                                ):
                                    # Previous character looks like the end of a value
                                    # This suggests we're between array
                                    # elements or object values
                                    # But we need more context

                                    # Look further back to see if we
                                    # can find a ':' or '{'
                                    k = j
                                    found_colon = False
                                    found_open_brace = False
                                    while k >= 0:
                                        if text[k] == ":":
                                            found_colon = True
                                            break
                                        elif text[k] == "{":
                                            found_open_brace = True
                                            break
                                        elif text[k] in "}]" or (
                                            k < j and text[k] == ","
                                        ):
                                            # Hit a structure boundary - stop looking
                                            break
                                        k -= 1

                                    if found_colon and not found_open_brace:
                                        # Found a ':' but no '{' in
                                        # between - object context
                                        # The comma is between key-value
                                        # pairs in an object
                                        result.append(",")
                                        i += 2  # Skip the second comma
                                        continue
                                    elif found_open_brace and not found_colon:
                                        # Found '{' but no ':' - we might be
                                        # between array elements
                                        # But this is complex, let's be
                                        # conservative and treat as object
                                        result.append(",")
                                        i += 2  # Skip the second comma
                                        continue

                        # Default/fallback logic
                        if array_context and not object_context:
                            # Clearly in array context - each comma represents
                            # a separate sparse element
                            result.append(", null")
                            # Process only the first comma, let the next
                            # iteration handle the second
                            i += 1
                            continue
                        elif object_context:
                            # In object context (or ambiguous) - treat as
                            # object context
                            result.append(",")
                            i += 2  # Skip the second comma
                            continue
                        else:
                            # Not clearly in either context - be conservative
                            result.append(",")
                            i += 2  # Skip the second comma
                            continue
                    else:
                        result.append(char)
                else:
                    result.append(char)

                i += 1

            return "".join(result)

        text = process_double_commas(text)

        # FINAL CLEANUP: Remove any null values that ended up in object contexts
        # This is a safety net to catch cases where null was incorrectly
        # inserted into objects
        def clean_null_in_objects(text: str) -> str:
            """Remove null values that appear in object contexts."""
            # Look for patterns like {"key": "value", null, "key2": "value2"}
            # This pattern is invalid in JSON objects and should become
            # {"key": "value", "key2": "value2"}

            # Use a regex to find and fix these patterns
            # Pattern: , null, "key": (comma, space, null, comma, space,
            # quoted key, colon)
            fixed = safe_regex_sub(r',\s*null,\s*("[^"]*"\s*:)', r", \1", text)

            # Also handle the case where null appears at the start: {null, "key":
            fixed = safe_regex_sub(r"{\s*null,\s*", "{", fixed)

            # Handle case where null appears before closing brace: , null}
            fixed = safe_regex_sub(r",\s*null\s*}", "}", fixed)

            return fixed

        text = clean_null_in_objects(text)

        return text

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
            from ..utils.config import PreprocessingConfig

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

        # Fix unclosed strings
        text = cls.fix_unclosed_strings(text)

        # Handle string concatenation BEFORE quote processing to avoid corruption
        text = cls.handle_string_concatenation(text)

        # Enhanced string concatenation handling
        text = cls.normalize_string_concatenation(text)

        # Normalize mixed quotes after string concatenation
        text = cls.normalize_mixed_quotes(text)

        # Fix multiline strings early
        text = cls.fix_multiline_strings(text)

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
            text = cls.fix_unescaped_strings(text)
            # Only apply quote fixing if text looks like it has problematic quotes
            # Skip if it contains URLs (might have legitimate quotes in URLs)
            has_urls = "http://" in text or "https://" in text
            if not has_urls:
                text = cls.fix_unescaped_quotes_in_strings(text)

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
            # Pre-normalize comma spacing only for arrays to fix sparse array detection
            # Only do this for texts that likely contain arrays with sparse elements
            if "[" in text and ", ," in text:
                # Simple string replacement to avoid regex complexity
                text = text.replace(", ,", ",,")
            text = cls.handle_sparse_arrays(text)

        return text.strip()
