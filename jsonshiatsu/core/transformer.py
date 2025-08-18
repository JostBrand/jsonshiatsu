"""
JSON Preprocessor - Handles common malformed JSON patterns.

This module provides preprocessing functions to clean and extract JSON from
various malformed formats commonly found in real-world data.
"""

import re
from typing import Any, Match, Optional


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
        match = re.search(json_block_pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        inline_pattern = r"`([^`]*[{[].*?[}\]][^`]*)`"
        match = re.search(inline_pattern, text, re.DOTALL)
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
        - // line comments
        - /* block comments */
        """
        text = re.sub(r"//.*?(?=\n|$)", "", text, flags=re.MULTILINE)

        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)

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
            '"': '"',  # U+201D Right double quotation mark
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
        """

        def fix_quotes(match: Match[str]) -> str:
            content = match.group(1)

            # If no internal quotes, return as-is
            if '"' not in content:
                return match.group(0)

            # Simple heuristic: if we have unescaped quotes in the middle,
            # escape them. We'll be conservative and only fix obvious cases.
            # Pattern: text"word"text -> text\"word\"text

            # Find unescaped quotes (not preceded by \)
            result = []
            i = 0
            while i < len(content):
                if content[i] == '"':
                    # Check if this quote is already escaped
                    escaped = False
                    backslash_count = 0
                    j = i - 1
                    while j >= 0 and content[j] == "\\":
                        backslash_count += 1
                        j -= 1

                    # Even number of backslashes means the quote is not escaped
                    escaped = backslash_count % 2 == 1

                    if not escaped:
                        result.append('\\"')
                    else:
                        result.append('"')
                else:
                    result.append(content[i])
                i += 1

            return f'"{"".join(result)}"'

        # Apply to double-quoted strings only (be conservative)
        # Use a pattern that matches the outermost quotes
        # This is tricky - we need to handle nested quotes properly

        # Simple approach: find strings that contain unescaped internal quotes
        # Pattern: "text"word"text" where the middle quotes aren't escaped

        # We need a more sophisticated approach for strings with unescaped quotes
        # Let's use a different strategy - find problem patterns specifically

        # Safety check - don't process very large texts to avoid performance issues
        if len(text) > 10000:
            return text

        # Use a character-by-character approach but with safeguards
        result = []
        i = 0
        max_iterations = len(text) * 2  # Safety limit
        iterations = 0

        while i < len(text) and iterations < max_iterations:
            iterations += 1

            if text[i] == '"':
                # Found start of a string - process it carefully
                result.append('"')
                i += 1

                # Process the string content until we find the real closing quote
                while i < len(text) and iterations < max_iterations:
                    iterations += 1

                    if text[i] == '"':
                        # Found a potential closing quote
                        # Check if it's escaped
                        backslash_count = 0
                        j = len(result) - 1
                        while j >= 0 and result[j] == "\\":
                            backslash_count += 1
                            j -= 1

                        if backslash_count % 2 == 0:
                            # This quote is not escaped
                            # Check if this looks like the real end of the string
                            next_idx = i + 1

                            # For a quote to be the real end, it should be followed by
                            # JSON syntax characters, not more string content
                            is_real_end = False
                            if next_idx >= len(text):
                                is_real_end = True
                            elif text[next_idx] in ":,}]":
                                is_real_end = True
                            elif text[next_idx] in "\n\r\t ":
                                # Check if after whitespace we have JSON syntax
                                k = next_idx
                                while k < len(text) and text[k] in "\n\r\t ":
                                    k += 1
                                if k >= len(text) or text[k] in ":,}]":
                                    is_real_end = True

                            if is_real_end:
                                # This is the closing quote
                                result.append('"')
                                i += 1
                                break
                            else:
                                # This is an internal quote that needs escaping
                                result.append('\\"')
                                i += 1
                        else:
                            # Already escaped quote - keep as is
                            result.append('"')
                            i += 1
                    else:
                        result.append(text[i])
                        i += 1
            else:
                result.append(text[i])
                i += 1

        text = "".join(result)
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
            # Re-enable quote fixing for LLM responses with nested quotes
            text = cls.fix_unescaped_quotes_in_strings(text)

        if config.handle_incomplete_json:
            text = cls.handle_incomplete_json(text)

        # Handle sparse arrays as final step
        if config.handle_sparse_arrays:
            text = cls.handle_sparse_arrays(text)

        # Final LLM optimization - normalize whitespace
        text = cls.normalize_whitespace(text)

        return text.strip()
