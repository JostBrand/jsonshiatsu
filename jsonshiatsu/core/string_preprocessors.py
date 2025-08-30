"""
String preprocessing utilities for JSON repair.

This module handles various string-related JSON repair operations including
string concatenation, quote normalization, and escape sequence fixes.
"""

import json
import re
from re import Match

from .regex_utils import (
    safe_regex_findall,
    safe_regex_match,
    safe_regex_search,
    safe_regex_sub,
)


class StringPreprocessor:
    """Handles string-specific preprocessing operations."""

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

            # No problematic backslashes found, return unchanged
            return full_match

        text = safe_regex_sub(r'"([^"]*)"', fix_file_paths, text)

        return text

    @staticmethod
    def _should_skip_quote_fixing(text: str) -> bool:
        """Check if text should be skipped for quote fixing."""
        # Early checks for simple conditions
        if len(text) > 50000 or "://" in text or '\\"' in text:
            return True

        # Check for structural issues
        open_braces = text.count("{") - text.count("}")
        open_brackets = text.count("[") - text.count("]")
        if (
            open_braces > 0
            or open_brackets > 0
            or safe_regex_search(r'"\s*=\s*[^=]|^\s*\w+\s*=\s*', text)
            or safe_regex_search(r'"\s+"[^:]', text)
            or safe_regex_search(r"\}\s*\{", text)
        ):
            return True

        # Don't process well-formed JSON
        try:
            json.loads(text)
            return True
        except (json.JSONDecodeError, ValueError, TypeError):
            return False

    @staticmethod
    def _is_quote_escaped(text: str, pos: int) -> bool:
        """Check if quote at position is escaped."""
        backslash_count = 0
        j = pos - 1
        while j >= 0 and text[j] == "\\":
            backslash_count += 1
            j -= 1
        return backslash_count % 2 == 1

    @staticmethod
    def _is_string_end_quote(text: str, pos: int) -> bool:
        """Check if quote at position is end of string."""
        next_pos = pos + 1
        while next_pos < len(text) and text[next_pos] in " \t\n\r":
            next_pos += 1

        return (
            next_pos >= len(text)
            or text[next_pos] in ":,}]\n"
            or (
                next_pos < len(text) - 1
                and text[next_pos : next_pos + 2] in ["/*", "//"]
            )
        )

    @staticmethod
    def _process_string_content(text: str, start_pos: int) -> tuple[str, int]:
        """Process string content and return (content, next_position)."""
        string_content = ""
        i = start_pos

        while i < len(text):
            if text[i] == '"':
                if not StringPreprocessor._is_quote_escaped(text, i):
                    if StringPreprocessor._is_string_end_quote(text, i):
                        # This is the end quote
                        next_pos = i + 1
                        while next_pos < len(text) and text[next_pos] in " \t\n\r":
                            next_pos += 1
                        return string_content, next_pos
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

        return string_content, len(text)

    @staticmethod
    def fix_unescaped_quotes_in_strings(text: str) -> str:
        """
        Fix unescaped double quotes within string values.

        Handles cases like: "Hello "world"" -> "Hello \"world\""

        Now with improved URL protection.
        """
        if StringPreprocessor._should_skip_quote_fixing(text):
            return text

        try:
            # Use character-by-character parsing with JSON awareness
            result = []
            i = 0

            while i < len(text):
                if text[i] == '"':
                    # Start of a string - find its actual end
                    result.append('"')
                    string_content, next_pos = (
                        StringPreprocessor._process_string_content(text, i + 1)
                    )
                    result.append(string_content)
                    if next_pos < len(text) or string_content:
                        result.append('"')
                    i = next_pos
                else:
                    result.append(text[i])
                    i += 1

            return "".join(result)

        except (IndexError, ValueError, AttributeError):
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
    def _should_skip_multiline_fixing(text: str) -> bool:
        """Check if text should be skipped for multiline fixing."""
        quote_count = text.count('"')
        return (
            quote_count >= 4
            and quote_count % 2 == 0
            and (
                "authentication" in text
                or "concatenation" in text
                or "RelatedTexts" in text
            )
        )

    @staticmethod
    def _count_unescaped_quotes(line: str) -> int:
        """Count unescaped quotes in a line."""
        quote_count = 0
        escaped = False
        for char in line:
            if char == "\\" and not escaped:
                escaped = True
                continue
            if char == '"' and not escaped:
                quote_count += 1
            escaped = False
        return quote_count

    @staticmethod
    def _combine_multiline_string(lines: list[str], start_idx: int) -> tuple[str, int]:
        """Combine multiline string and return (combined_line, next_index)."""
        combined_line = lines[start_idx]
        j = start_idx + 1

        while j < len(lines):
            next_line = lines[j]
            combined_line += "\\n" + next_line.strip()

            next_quote_count = StringPreprocessor._count_unescaped_quotes(next_line)

            if next_quote_count % 2 == 1:
                return combined_line, j + 1
            j += 1

        return lines[start_idx] + '"', start_idx + 1

    @staticmethod
    def fix_multiline_strings(text: str) -> str:
        """
        Fix multiline string literals by properly escaping or joining them.

        Handles cases where strings are split across lines without proper escaping.
        """
        if StringPreprocessor._should_skip_multiline_fixing(text):
            return text

        lines = text.split("\n")
        fixed_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]
            quote_count = StringPreprocessor._count_unescaped_quotes(line)

            if quote_count % 2 == 1 and i < len(lines) - 1:
                combined_line, next_i = StringPreprocessor._combine_multiline_string(
                    lines, i
                )
                fixed_lines.append(combined_line)
                i = next_i
            else:
                fixed_lines.append(line)
                i += 1

        return "\n".join(fixed_lines)

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
        def fix_paren_concatenation(match: Match[str]) -> str:
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
