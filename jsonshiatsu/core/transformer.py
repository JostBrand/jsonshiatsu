"""
JSON Preprocessor - Handles common malformed JSON patterns.

This module provides preprocessing functions to clean and extract JSON from
various malformed formats commonly found in real-world data.
"""

import re
import signal
from typing import Any, Callable, Match, Optional, Union


class RegexTimeout(Exception):
    """Exception raised when regex operations timeout."""

    pass


def timeout_handler(signum: int, frame: Any) -> None:
    """Handler for regex timeout."""
    raise RegexTimeout("Regex operation timed out")


def safe_regex_sub(
    pattern: str,
    repl: Union[str, Callable[[Match[str]], str]],
    string: str,
    flags: int = 0,
    timeout: int = 5,
) -> str:
    """Safe regex substitution with timeout."""
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
    """Safe regex search with timeout."""
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

                # Check if we have a complete structure
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
        # Remove /* block comments */ first
        text = safe_regex_sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)

        # Remove // line comments but NOT if they're part of URLs (https:// http://)
        # Look for // that's not preceded by http: or https:
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

        # Remove function calls like parse_json(...), JSON.parse(...), etc.
        func_pattern = r"^[a-zA-Z_][a-zA-Z0-9_.]*\s*\(\s*(.*)\s*\)\s*;?\s*$"
        match = re.match(func_pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Remove return statements
        return_pattern = r"^return\s+(.*?)\s*;?\s*$"
        match = re.match(return_pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Remove variable assignments
        var_pattern = r"^(?:const|let|var)\s+\w+\s*=\s*(.*?)\s*;?\s*$"
        match = re.match(var_pattern, text, re.DOTALL | re.IGNORECASE)
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
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

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
            needs_quoting = bool(re.search(r"[-./:#@?&=+%]", value))

            # Also quote if it looks like a URL, version number, or complex identifier
            if any(
                pattern in value.lower()
                for pattern in ["http", "www.", "v1.", "v2.", "gpt-", "claude-"]
            ):
                needs_quoting = True

            # Quote any string value that's not a valid JSON literal
            # Don't quote simple boolean/null values or numbers
            if value.lower() in ["true", "false", "null"]:
                needs_quoting = False
            elif (
                value.replace(".", "")
                .replace("-", "")
                .replace("+", "")
                .replace("e", "")
                .replace("E", "")
                .isdigit()
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

        return re.sub(pattern, quote_value, text, flags=re.MULTILINE)

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

        return re.sub(pattern, quote_key, text)

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
        """
        # Handle Python-style booleans and None
        text = re.sub(r"\bTrue\b", "true", text)
        text = re.sub(r"\bFalse\b", "false", text)
        text = re.sub(r"\bNone\b", "null", text)

        # Handle yes/no
        text = re.sub(r"\byes\b", "true", text, flags=re.IGNORECASE)
        text = re.sub(r"\bno\b", "false", text, flags=re.IGNORECASE)

        # Handle undefined
        text = re.sub(r"\bundefined\b", "null", text, flags=re.IGNORECASE)

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
            has_json_escapes = re.search(r'\\[\\"/bfnrtu]|\\u[0-9a-fA-F]{4}', content)

            if has_json_escapes:
                # Only treat as file path if it has strong file path indicators
                looks_like_path = (
                    # Contains common path components
                    any(indicator in content_lower for indicator in file_indicators)
                    or
                    # Contains drive letters (C:, D:, etc.) - must be start of string or
                    # after space/slash
                    re.search(r"(?:^|[\s/\\])[a-zA-Z]:", content)
                )
            else:
                # No JSON escapes - use broader file path detection
                looks_like_path = (
                    # Contains common path components
                    any(indicator in content_lower for indicator in file_indicators)
                    or
                    # Contains drive letters (C:, D:, etc.) - must be start of string or
                    # after space/slash
                    re.search(r"(?:^|[\s/\\])[a-zA-Z]:", content)
                    or
                    # Contains actual path separators (not JSON escape sequences)
                    # Only consider it a path if there are backslashes that are NOT
                    # valid JSON escapes
                    (
                        content.count("\\") >= 2
                        and re.search(r'\\(?![\\"/bfnrtu]|u[0-9a-fA-F]{4})', content)
                    )
                    or
                    # Contains common file extensions (but not Unicode escapes)
                    # Must be a backslash followed by path components and an extension
                    re.search(r"\\[^u\\]+\.[a-zA-Z0-9]{1,4}$", content)
                    or
                    # Or a regular path with extension at the end
                    re.search(
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
                escaped_content = re.sub(
                    r'\\(?![\\"/bfnrtu]|u[0-9a-fA-F]{4})', r"\\\\", content
                )
                return f'"{escaped_content}"'

        # Apply to all quoted strings
        text = re.sub(r'"([^"]*)"', fix_file_paths, text)

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

        # Don't process if text contains URLs or looks like well-formed JSON
        if "://" in text or (text.count('":') > 2 and text.count("\n") > 1):
            return text

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
        - ("string1" "string2") -> "string1string2" (Python implicit concatenation)
        """
        # Handle + operator concatenation
        # Pattern: "string1" + "string2" with possible whitespace/newlines
        plus_pattern = r'"([^"]*?)"\s*\+\s*"([^"]*?)"'

        # Keep applying until no more matches (handles multiple concatenations)
        max_iterations = 10  # Safety limit
        iteration = 0
        while re.search(plus_pattern, text) and iteration < max_iterations:
            iteration += 1
            text = re.sub(plus_pattern, r'"\1\2"', text)

        # Handle Python-style parentheses concatenation
        # Pattern: ("string1" "string2" "string3") -> "string1string2string3"

        # First, handle adjacent strings within parentheses
        def fix_paren_concatenation(match: re.Match[str]) -> str:
            content = match.group(1)
            # Find all quoted strings within the parentheses
            string_pattern = r'"([^"]*?)"'
            strings = re.findall(string_pattern, content)
            if strings:
                # Concatenate all strings
                combined = "".join(strings)
                return f'"{combined}"'
            return match.group(0)

        # Pattern to match parentheses containing multiple quoted strings
        paren_pattern = r'\(\s*("(?:[^"\\]|\\.)*?"(?:\s+"(?:[^"\\]|\\.)*?")*)\s*\)'
        text = re.sub(paren_pattern, fix_paren_concatenation, text)

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

            # Don't merge if strings are in array context (no + operator)
            # This is likely array elements, not string concatenation
            operators = ["+", "(", ")"]
            if not any(op in full_match for op in operators):
                return full_match  # Don't merge - likely array elements

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
                elif char == "]":
                    if stack and stack[-1] == "[":
                        stack.pop()

        # Close unclosed strings
        if in_string and string_char:
            text += string_char

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

        # Remove "data:" prefixes from server-sent events
        lines = text.strip().split("\n")
        cleaned_lines = []

        for line in lines:
            line = line.strip()

            # Skip empty lines and SSE control messages
            if not line or line in ["[DONE]", "event: done", "event: error"]:
                continue

            # Remove "data:" prefix from server-sent events
            if line.startswith("data:"):
                line = line[5:].strip()

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
        text = re.sub(r'"\s*:\s*(?![0-9])', '": ', text)

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
        text = re.sub(r"{\s*\n\s*", "{\n    ", text)
        text = re.sub(r"\n\s*}", "\n}", text)

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
    def normalize_mixed_quotes(text: str) -> str:
        """
        Normalize mixed single and double quotes to use double quotes consistently.

        Handles:
        - 'key': 'value' -> "key": "value"
        - Mixed quotes in same object
        """
        # Don't process if text is too long to avoid performance issues
        if len(text) > 10000:
            return text

        # Convert single quotes to double quotes, but be careful about escaped quotes
        # Process character by character to handle nested quotes properly
        result = []
        i = 0
        while i < len(text):
            if text[i] == "'":
                # Found single quote - extract the content
                i += 1  # Skip opening quote
                content = ""
                while i < len(text) and text[i] != "'":
                    if text[i] == '"':
                        content += '\\"'  # Escape double quotes inside
                    elif text[i] == "\\" and i + 1 < len(text):
                        # Handle escape sequences
                        content += text[i : i + 2]
                        i += 1
                    else:
                        content += text[i]
                    i += 1

                if i < len(text):  # Found closing quote
                    result.append(f'"{content}"')
                    i += 1  # Skip closing quote
                else:
                    # No closing quote found
                    result.append("'" + content)
            else:
                result.append(text[i])
                i += 1

        return "".join(result)

    @staticmethod
    def fix_multiline_strings(text: str) -> str:
        """
        Fix multiline string literals by properly escaping or joining them.

        Handles cases where strings are split across lines without proper escaping.
        """
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
        # Handle NaN and Infinity
        text = safe_regex_sub(r"\bNaN\b", "null", text)
        text = safe_regex_sub(r"\bInfinity\b", "1e308", text)  # Very large number
        text = safe_regex_sub(r"-Infinity\b", "-1e308", text)

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
        text = safe_regex_sub(r"function\s*\([^)]*\)\s*\{[^}]*\}", "null", text)

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

        return text

    @staticmethod
    def fix_unclosed_strings(text: str) -> str:
        """
        Fix unclosed strings by adding closing quotes.

        Handles cases where strings are not properly terminated.

        Improved to handle multiline strings correctly.
        """
        # Don't process if text looks like it already has well-formed strings
        # Count total quotes in entire text to see if they're balanced
        total_quotes = 0
        i = 0
        while i < len(text):
            if text[i] == '"' and (i == 0 or text[i - 1] != "\\"):
                total_quotes += 1
            i += 1

        # If quotes are already balanced, don't mess with it
        if total_quotes % 2 == 0:
            return text

        lines = text.split("\n")
        fixed_lines = []

        for line in lines:
            # Count unescaped quotes
            quote_count = 0
            i = 0
            while i < len(line):
                if line[i] == '"' and (i == 0 or line[i - 1] != "\\"):
                    quote_count += 1
                i += 1

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
                import re

                string_contents = re.findall(r'"([^"]*)"', content)
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
                match = re.match(r'"(.*)"', part)
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
        import re

        # FIRST: Clean up invalid object sparse syntax BEFORE processing arrays
        # This prevents ,, in objects from being converted to null
        def clean_object_double_commas(text: str) -> str:
            """Remove double commas from object contexts only (invalid JSON)."""
            # Be very careful to only clean object contexts, not array contexts
            lines = text.split("\n")
            result_lines = []

            for line in lines:
                # Only clean lines that contain : (indicating object key-value pairs)
                # AND don't contain [ or ] (indicating array context)
                if ":" in line and "[" not in line and "]" not in line:
                    # Remove double commas in object context
                    cleaned = re.sub(r",\s*,+", ",", line)
                    result_lines.append(cleaned)
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
            fixed_content = re.sub(r"^(\s*),", r"\1null,", fixed_content)

            # Handle multiple consecutive commas: ,, -> , null,
            while ",," in fixed_content:
                fixed_content = fixed_content.replace(",,", ", null,")

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
        simple_array_pattern = r"\[([^\[\]]*?)\]"
        text = re.sub(simple_array_pattern, fix_sparse_in_array, text)

        # Second pass: handle remaining sparse commas between elements at any level
        # Convert ", ," patterns to ", null," at any level
        while ",," in text:
            text = text.replace(",,", ", null,")

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

        # Handle JavaScript constructs early
        text = cls.handle_javascript_constructs(text)

        # Normalize special numbers (hex, octal, NaN, Infinity)
        text = cls.normalize_special_numbers(text)

        # Handle empty values and incomplete structures
        text = cls.handle_empty_values(text)

        # Fix unclosed strings
        text = cls.fix_unclosed_strings(text)

        # Normalize mixed quotes early
        text = cls.normalize_mixed_quotes(text)

        # Enhanced string concatenation handling
        text = cls.normalize_string_concatenation(text)

        # Fix multiline strings early
        text = cls.fix_multiline_strings(text)

        # Normalize boolean/null BEFORE quoting so they're recognized as JSON literals
        if config.normalize_boolean_null:
            text = cls.normalize_boolean_null(text)

        # Quote unquoted values with special characters (before quote normalization)
        text = cls.quote_unquoted_values(text)

        # Handle string concatenation early, before quote processing
        text = cls.handle_string_concatenation(text)

        # Quote unquoted keys to ensure valid JSON
        text = cls.quote_unquoted_keys(text)

        if config.normalize_quotes:
            text = cls.normalize_quotes(text)

        if config.fix_unescaped_strings:
            text = cls.fix_unescaped_strings(text)
            # Only apply quote fixing if text looks like it has problematic quotes
            # Skip if it looks like normal multiline JSON OR contains URLs
            has_urls = "http://" in text or "https://" in text
            is_multiline_json = text.count("\n") > 2 and text.count('":') > 2
            if not (is_multiline_json or has_urls):
                text = cls.fix_unescaped_quotes_in_strings(text)

        # Fix missing commas after quote processing
        text = cls.fix_missing_commas(text)

        if config.handle_incomplete_json:
            text = cls.handle_incomplete_json(text)

        # Handle sparse arrays as final step
        if config.handle_sparse_arrays:
            text = cls.handle_sparse_arrays(text)

        # Final LLM optimization - normalize whitespace
        text = cls.normalize_whitespace(text)

        return text.strip()
