"""
Special content handlers for preprocessing.

This module contains preprocessing steps that handle special content types
like comments and JavaScript constructs that need to be cleaned or transformed.
"""

import re

from ..utils.config import PreprocessingConfig
from .pipeline import PreprocessingStepBase


class CommentHandler(PreprocessingStepBase):
    """Removes comments from JSON text."""

    def should_apply(self, config: PreprocessingConfig) -> bool:
        """Apply if comment removal is enabled."""
        return config.remove_comments

    def process(self, text: str, config: PreprocessingConfig) -> str:
        """Remove comments from JSON text."""
        return self._remove_comments(text)

    @staticmethod
    def _remove_comments(text: str) -> str:
        """Remove single-line and multi-line comments from JSON."""
        result = []
        i = 0
        in_string = False
        string_char = None

        while i < len(text):
            char = text[i]
            next_char = text[i + 1] if i + 1 < len(text) else ""

            # Handle string state
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

            # Handle comments when not in strings
            if char == "/" and next_char == "/":
                # Single-line comment - skip to end of line
                while i < len(text) and text[i] != "\n":
                    i += 1
                # Keep the newline
                if i < len(text):
                    result.append(text[i])
                    i += 1
            elif char == "/" and next_char == "*":
                # Multi-line comment - skip to */
                i += 2
                while i < len(text) - 1:
                    if text[i] == "*" and text[i + 1] == "/":
                        i += 2
                        break
                    i += 1
                # Only add a space if there isn't already whitespace before or after
                has_space_before = result and result[-1].isspace()
                has_space_after = i < len(text) and text[i].isspace()

                if not has_space_before and not has_space_after:
                    result.append(" ")
                # If there's space before but not after, or vice versa, don't add extra space
            else:
                result.append(char)
                i += 1

        return "".join(result)


class JavaScriptHandler(PreprocessingStepBase):
    """Handles JavaScript constructs in JSON text."""

    def should_apply(self, config: PreprocessingConfig) -> bool:
        """Apply if JavaScript handling is enabled."""
        return config.unwrap_function_calls

    def process(self, text: str, config: PreprocessingConfig) -> str:
        """Handle JavaScript constructs in JSON text."""
        result = text
        result = self._remove_function_definitions(result)
        result = self._handle_javascript_constructs(result)
        return result

    @staticmethod
    def _remove_function_definitions(text: str) -> str:
        """Remove JavaScript function definitions."""
        # Handle function keyword
        result = []
        i = 0

        while i < len(text):
            if JavaScriptHandler._is_function_keyword(text, i):
                # Skip function definition
                j = JavaScriptHandler._skip_function_definition(text, i)
                if j > i:
                    result.append("null")
                    i = j
                    continue

            result.append(text[i])
            i += 1

        return "".join(result)

    @staticmethod
    def _is_function_keyword(text: str, pos: int) -> bool:
        """Check if position starts with 'function' keyword."""
        return text[pos : pos + 8] == "function" and (
            pos + 8 >= len(text) or not text[pos + 8].isalnum()
        )

    @staticmethod
    def _skip_function_definition(text: str, start: int) -> int:
        """Skip a complete function definition."""
        i = start + 8  # Skip 'function'

        # Skip whitespace and optional function name
        while i < len(text) and (
            text[i].isspace() or text[i].isalnum() or text[i] == "_"
        ):
            i += 1

        # Expect opening parenthesis
        if i >= len(text) or text[i] != "(":
            return start

        # Skip parameter list
        paren_count = 1
        i += 1
        while i < len(text) and paren_count > 0:
            if text[i] == "(":
                paren_count += 1
            elif text[i] == ")":
                paren_count -= 1
            i += 1

        # Skip whitespace
        while i < len(text) and text[i].isspace():
            i += 1

        # Expect opening brace
        if i >= len(text) or text[i] != "{":
            return start

        # Skip function body
        brace_count = 1
        i += 1
        while i < len(text) and brace_count > 0:
            if text[i] == "{":
                brace_count += 1
            elif text[i] == "}":
                brace_count -= 1
            i += 1

        return i

    @staticmethod
    def _handle_javascript_constructs(text: str) -> str:
        """Handle various JavaScript constructs."""
        # Handle special values first
        # NaN and Infinity should become strings when used as identifiers
        text = re.sub(r"\bNaN\b", '"NaN"', text)
        # Handle -Infinity as a complete unit first, then regular Infinity
        text = re.sub(r"-\bInfinity\b", '"-Infinity"', text)  # Handle negative first
        # Only handle Infinity if not already quoted
        text = re.sub(
            r'(?<!")Infinity(?!")', '"Infinity"', text
        )  # Then positive, but not if already quoted

        # Replace undefined with null
        text = re.sub(r"\bundefined\b", "null", text)

        # Handle new Date() and similar constructors FIRST (before individual function patterns)
        text = re.sub(r"\bnew\s+\w+\([^)]*\)", "null", text)

        # Handle function calls by extracting their content
        # Date("2025-08-01") -> "2025-08-01"
        # ObjectId("507f1f77bcf86cd799439011") -> "507f1f77bcf86cd799439011"
        function_patterns = [
            (r"\bDate\(([^)]+)\)", r"\1"),
            (r"\bObjectId\(([^)]+)\)", r"\1"),
            (r"\bISODate\(([^)]+)\)", r"\1"),
            (r"\bUUID\(([^)]+)\)", r"\1"),
            (r"\bRegExp\(([^)]+)\)", r"\1"),
            # Handle specific parsing functions first (more specific patterns)
            (r"\bJSON\.parse\(([^)]+)\)", r"\1"),
            (r"\bparseJSON\(([^)]+)\)", r"\1"),
            # Generic parsing functions (but not when preceded by a dot to avoid JSON.parse)
            (r"(?<!\w\.)parse\(([^)]+)\)", r"\1"),
            # Handle functions with empty parameters -> empty string
            (r"\bDate\(\s*\)", '""'),
            (r"\bObjectId\(\s*\)", '""'),
            (r"\bISODate\(\s*\)", '""'),
            (r"\bUUID\(\s*\)", '""'),
            (r"\bRegExp\(\s*\)", '""'),
            (r"\bJSON\.parse\(\s*\)", '""'),
            (r"\bparseJSON\(\s*\)", '""'),
            (r"(?<!\w\.)parse\(\s*\)", '""'),
        ]

        for pattern, replacement in function_patterns:
            text = re.sub(pattern, replacement, text)

        # Handle JavaScript statements that contain JSON
        # return {"key": "value"}; -> {"key": "value"}
        text = re.sub(r"\breturn\s+(\{[^;]*\});?", r"\1", text)
        # const/let/var data = {"key": "value"}; -> {"key": "value"}
        text = re.sub(r"\b(?:const|let|var)\s+\w+\s*=\s*(\{[^;]*\});?", r"\1", text)

        # Handle hexadecimal numbers
        text = re.sub(r"\b0x([0-9a-fA-F]+)\b", lambda m: str(int(m.group(1), 16)), text)

        # Handle octal numbers (leading zeros) - very conservative approach
        def safe_octal(match: re.Match[str]) -> str:
            # Get wider context to make better decisions
            start = max(0, match.start() - 10)
            end = min(len(match.string), match.end() + 10)
            context = match.string[start:end]

            # Check if the number itself is inside quotes by looking at immediate context
            before_match = match.string[max(0, match.start() - 1) : match.start()]
            after_match = match.string[
                match.end() : min(len(match.string), match.end() + 1)
            ]

            # Skip if the number is directly inside quoted strings
            if (
                before_match.endswith('"')
                or before_match.endswith("'")
                or after_match.startswith('"')
                or after_match.startswith("'")
            ):
                return match.group(0)

            # Skip if it looks like a date, time, or version number
            if any(char in context for char in ["-", "T", "+", "Z", "."]):
                return match.group(0)

            # Only convert if it's clearly a standalone number in a JSON context
            # Look for patterns like ": 025," or ": 025}"
            if ":" in context and ("," in context or "}" in context):
                return str(int(match.group(1), 8))

            # Conservative default: don't convert
            return match.group(0)

        text = re.sub(r"\b0([0-7]+)\b", safe_octal, text)

        # Handle regex literals (but not inside strings)
        # Use a more sophisticated approach to avoid processing URLs inside quoted strings
        def replace_regex_literals(match_obj: re.Match[str]) -> str:
            full_match = match_obj.group(0)
            # Check if we're inside a quoted string by examining the context
            start_pos = match_obj.start()
            text_before = text[:start_pos]

            # Count unescaped quotes before this position
            quote_count = 0
            i = 0
            while i < len(text_before):
                if text_before[i] == '"' and (i == 0 or text_before[i - 1] != "\\"):
                    quote_count += 1
                i += 1

            # If quote count is odd, we're inside a string - don't modify
            if quote_count % 2 == 1:
                return full_match

            # We're outside strings, safe to convert regex literal
            pattern_content = match_obj.group(1)
            return f'"{pattern_content}"'

        text = re.sub(r"/([^/\n]+)/[gimuy]*", replace_regex_literals, text)

        # Handle string values that look like line comments (convert to empty strings)
        # This handles cases where a string value is just a comment: "comment": "// text"
        text = re.sub(r':\s*"//[^"]*"', ': ""', text)

        # Handle template literals (basic case)
        text = re.sub(r"`([^`]*)`", r'"\1"', text)

        # Handle string concatenation (both explicit with + and implicit adjacent strings)
        for _ in range(50):  # Handle up to 50 chained concatenations
            old_text = text
            # Explicit concatenation with + (including multiline)
            text = re.sub(
                r'"([^"]*)"\s*\+\s*"([^"]*)"', r'"\1\2"', text, flags=re.DOTALL
            )
            text = re.sub(
                r"'([^']*)'\s*\+\s*'([^']*)'", r'"\1\2"', text, flags=re.DOTALL
            )
            # Mixed quote concatenation
            text = re.sub(
                r"'([^']*)'\s*\+\s*\"([^\"]*)\"", r'"\1\2"', text, flags=re.DOTALL
            )  # 'str1' + "str2"
            text = re.sub(
                r'"([^"]*)"\s*\+\s*\'([^\']*)\'', r'"\1\2"', text, flags=re.DOTALL
            )  # "str1" + 'str2'

            # Implicit concatenation (adjacent strings) - be context-aware
            # Python-style parentheses concatenation - handle multiple strings
            def handle_paren_concatenation(match: re.Match[str]) -> str:
                content = match.group(1)
                # Extract all quoted strings and concatenate them
                import re

                strings = re.findall(r'"([^"]*)"', content)
                if strings:
                    combined = "".join(strings)
                    return f'"{combined}"'
                return match.group(0)  # Return original if no strings found

            # Pattern to match parentheses containing multiple quoted strings
            text = re.sub(
                r'\(\s*((?:"[^"]*"\s*)+)\s*\)', handle_paren_concatenation, text
            )

            # Adjacent strings, but not inside arrays
            text = JavaScriptHandler._concatenate_adjacent_strings_safe(text)
            # Handle parentheses around single concatenated strings
            text = re.sub(r'\("([^"]*)"\)', r'"\1"', text)  # ("string") -> "string"
            if text == old_text:  # No more changes
                break

        # Handle arithmetic expressions (simple cases, but avoid dates and version numbers)
        # Only process arithmetic when not in quotes and not looking like dates/versions
        def safe_arithmetic_add(match: re.Match[str]) -> str:
            full_match = match.group(0)
            # Skip if it looks like a date or version (contains dashes around)
            if "-" in match.string[max(0, match.start() - 10) : match.end() + 10]:
                return full_match
            return str(int(match.group(1)) + int(match.group(2)))

        def safe_arithmetic_sub(match: re.Match[str]) -> str:
            full_match = match.group(0)
            match_text = match.string
            start_pos = match.start()
            end_pos = match.end()

            # Check if we're inside a quoted string by counting quotes before this position
            # Count unescaped quotes before the match
            quote_count = 0
            i = 0
            while i < start_pos:
                if match_text[i] == '"' and (i == 0 or match_text[i - 1] != "\\"):
                    quote_count += 1
                i += 1

            # If quote count is odd, we're inside a string - don't process
            if quote_count % 2 == 1:
                return full_match

            # Skip if inside square brackets (regex character class)
            wider_context = match_text[max(0, start_pos - 10) : end_pos + 10]
            if "[" in wider_context and "]" in wider_context:
                return full_match

            # Skip if it looks like a date pattern
            if re.search(r"\d{4}-\d{2}-\d{2}", wider_context):
                return full_match

            return str(int(match.group(1)) - int(match.group(2)))

        text = re.sub(r"(\d+)\s*\+\s*(\d+)", safe_arithmetic_add, text)
        text = re.sub(r"(\d+)\s*-\s*(\d+)", safe_arithmetic_sub, text)

        return text

    @staticmethod
    def _concatenate_adjacent_strings_safe(text: str) -> str:
        """Safely concatenate adjacent strings, avoiding array contexts."""
        # Use a more sophisticated approach - only concatenate when strings
        # are clearly object values, not array elements

        # Pattern: : "string1" "string2" (after colon - object value context)
        # But not: , "string1" "string2" (after comma - could be array elements)
        # And not: [ "string1" "string2" (inside array)

        result = []
        i = 0

        while i < len(text):
            char = text[i]

            # Look for string concatenation opportunities
            if char == '"':
                # Found start of string - look for the pattern
                string1_start = i
                string1_end = JavaScriptHandler._find_string_end_simple(text, i)

                if string1_end != -1:
                    string1 = text[string1_start : string1_end + 1]

                    # Look ahead for adjacent string
                    j = string1_end + 1
                    while j < len(text) and text[j].isspace():
                        j += 1

                    if j < len(text) and text[j] == '"':
                        # Found adjacent string - check context
                        string2_end = JavaScriptHandler._find_string_end_simple(text, j)
                        if string2_end != -1:
                            string2 = text[j : string2_end + 1]

                            # Check context before string1 to decide if we should concatenate
                            context_start = max(0, string1_start - 20)
                            context = text[context_start:string1_start]

                            # Also check context after string2 - if there's a colon after string2,
                            # then string2 is likely a key, not a value to concatenate
                            context_after_start = string2_end + 1
                            context_after_end = min(len(text), context_after_start + 10)
                            context_after = text[
                                context_after_start:context_after_end
                            ].strip()

                            # Concatenate if:
                            # - After colon (object value): "key": "str1" "str2"
                            # - But NOT after comma (array element): , "str1" "str2"
                            # - And NOT after opening bracket: [ "str1" "str2"
                            # - And NOT if string2 is followed by colon (string2 is a key): "str1" "key":
                            if (
                                ":" in context
                                and not context.strip().endswith(",")
                                and not context.strip().endswith("[")
                                and not context_after.startswith(":")
                            ):
                                # Safe to concatenate - extract string contents
                                content1 = string1[1:-1]  # Remove quotes
                                content2 = string2[1:-1]  # Remove quotes
                                concatenated = f'"{content1}{content2}"'

                                result.append(concatenated)
                                i = string2_end + 1
                                continue

                    # Not concatenating - just add the string normally
                    result.append(string1)
                    i = string1_end + 1
                    continue
                else:
                    # Couldn't find string end - just add the character
                    result.append(char)
                    i += 1
            else:
                result.append(char)
                i += 1

        return "".join(result)

    @staticmethod
    def _find_string_end_simple(text: str, start: int) -> int:
        """Find the end of a quoted string starting at position start."""
        if start >= len(text) or text[start] != '"':
            return -1

        i = start + 1
        while i < len(text):
            if text[i] == '"' and (i == start + 1 or text[i - 1] != "\\"):
                return i
            elif text[i] == "\\" and i + 1 < len(text):
                i += 2  # Skip escaped character
            else:
                i += 1
        return -1
