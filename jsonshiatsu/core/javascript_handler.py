"""
JavaScript-specific preprocessing utilities for JSON repair.

This module handles JavaScript constructs, comments, function calls,
and expressions that commonly appear in malformed JSON data.
"""

import json
import re
from re import Match

from .regex_utils import safe_regex_search, safe_regex_sub


class JavaScriptHandler:
    """Handles JavaScript-specific preprocessing operations."""

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

        # Handle JSON.parse() with special logic to parse the content
        def parse_json_content(match: Match[str]) -> str:
            json_str = match.group(1)
            try:
                # Try to parse the JSON string to get the actual object
                parsed = json.loads(json_str)
                # Convert back to JSON string with clean formatting
                return json.dumps(parsed, separators=(", ", ": "))
            except (json.JSONDecodeError, ValueError):
                # If parsing fails, just return the string content
                return json_str

        # Split long line for readability
        json_parse_pattern = r'\bJSON\.parse\s*\(\s*"((?:[^"\\]|\\.)*)"\s*\)'
        text = safe_regex_sub(
            json_parse_pattern, parse_json_content, text, flags=re.IGNORECASE
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
    def _remove_function_definitions(text: str) -> str:
        """Remove JavaScript function definitions entirely."""
        result = []
        i = 0
        while i < len(text):
            if JavaScriptHandler._is_function_keyword(text, i):
                j = JavaScriptHandler._skip_function_definition(text, i)
                if j > i:
                    result.append("null")
                    i = j
                    continue
            result.append(text[i])
            i += 1
        return "".join(result)

    @staticmethod
    def _is_function_keyword(text: str, i: int) -> bool:
        """Check if position i starts with 'function' keyword."""
        return (
            text[i : i + 8] == "function"
            and (i == 0 or not text[i - 1].isalnum())
        )

    @staticmethod
    def _skip_function_definition(text: str, i: int) -> int:
        """Skip entire function definition and return end position."""
        j = i + 8  # Skip 'function'
        j = JavaScriptHandler._skip_whitespace(text, j)
        j = JavaScriptHandler._skip_function_name(text, j)
        j = JavaScriptHandler._skip_whitespace(text, j)
        j = JavaScriptHandler._skip_parameter_list(text, j)
        j = JavaScriptHandler._skip_whitespace(text, j)
        j = JavaScriptHandler._skip_function_body(text, j)
        return j

    @staticmethod
    def _skip_whitespace(text: str, j: int) -> int:
        """Skip whitespace characters."""
        while j < len(text) and text[j] in " \t\n":
            j += 1
        return j

    @staticmethod
    def _skip_function_name(text: str, j: int) -> int:
        """Skip function name if present."""
        while j < len(text) and (text[j].isalnum() or text[j] == "_"):
            j += 1
        return j

    @staticmethod
    def _skip_parameter_list(text: str, j: int) -> int:
        """Skip parameter list enclosed in parentheses."""
        if j < len(text) and text[j] == "(":
            return JavaScriptHandler._skip_balanced_delimiters(text, j, "(", ")")
        return j

    @staticmethod
    def _skip_function_body(text: str, j: int) -> int:
        """Skip function body enclosed in braces."""
        if j < len(text) and text[j] == "{":
            return JavaScriptHandler._skip_balanced_delimiters(text, j, "{", "}")
        return j

    @staticmethod
    def _skip_balanced_delimiters(text: str, j: int, open_char: str, close_char: str) -> int:
        """Skip balanced delimiters (parentheses or braces)."""
        if j >= len(text) or text[j] != open_char:
            return j
        count = 1
        j += 1
        while j < len(text) and count > 0:
            if text[j] == open_char:
                count += 1
            elif text[j] == close_char:
                count -= 1
            j += 1
        return j

    @staticmethod
    def _convert_regex_literals(text: str) -> str:
        """Convert regex literals to strings."""

        def convert_regex(match: Match[str]) -> str:
            pattern = match.group(1)
            # Escape any quotes in the pattern
            pattern = pattern.replace('"', '\\"')
            return f'"{pattern}"'

        # Match regex literals but exclude URLs by requiring specific context
        # Look for: /pattern/flags likely to be regex (after :, =, (, [, start)
        text = safe_regex_sub(r"(?<=[:\[=\(\s])/([^/]+)/[gimuy]*", convert_regex, text)
        text = safe_regex_sub(r"^/([^/]+)/[gimuy]*", convert_regex, text)
        return text

    @staticmethod
    def _convert_arithmetic_expressions(text: str) -> str:
        """Convert simple arithmetic expressions in JSON context."""

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
        text = JavaScriptHandler._remove_function_definitions(text)

        # Handle regex literals /pattern/flags -> "pattern"
        text = JavaScriptHandler._convert_regex_literals(text)

        # Handle template literals `text` -> "text" (simple case)
        text = safe_regex_sub(r"`([^`]*)`", r'"\1"', text)

        # Handle new Date() and similar constructor calls
        text = safe_regex_sub(r"\bnew\s+\w+\s*\([^)]*\)", "null", text)

        # Handle arithmetic expressions in JSON context (basic cases)
        text = JavaScriptHandler._convert_arithmetic_expressions(text)

        return text
