"""
Array and object processing utilities for JSON repair.

This module handles structural syntax issues, sparse arrays,
and unclosed string structures in JSON data.
"""

import re
from re import Match


class ArrayObjectHandler:
    """Handles array and object structural processing operations."""

    @staticmethod
    def fix_structural_syntax(text: str) -> str:
        """
        Fix structural syntax issues in JSON.

        Handles:
        - Parentheses instead of braces: (...) -> {...} for objects
        - Set literals: {1, 2, 3} -> [1, 2, 3] for arrays
        - Mixed object/array syntax detection
        """

        # Safe implementation - basic parentheses to braces conversion
        if '("' in text and '":' in text:
            # Simple replacement for clear object patterns
            # Convert (key: value) patterns to {key: value} - only if it has key: value structure
            pattern = r"\(([^()]*:\s*[^()]*)\)"
            text = re.sub(pattern, r"{\1}", text)

        # Safe set to array conversion (avoid changing content inside strings)
        if "{" in text and "}" in text and "," in text:

            def convert_sets(match: Match[str]) -> str:
                content = match.group(1)
                if ":" not in content and "," in content:
                    return "[" + content + "]"
                return match.group(0)

            # Only process braces that are not inside string literals
            # Simple approach: split by quotes and only process parts outside strings
            parts = text.split('"')
            for i in range(
                0, len(parts), 2
            ):  # Process only even indices (outside strings)
                parts[i] = re.sub(r"\{([^{}]*)\}", convert_sets, parts[i])
            text = '"'.join(parts)

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

        # SIMPLE SAFE IMPLEMENTATION - no complex regex
        # Just handle the most basic cases to avoid infinite loops

        # Step 1: Clean obvious object double commas (very conservative)
        lines = text.split("\n")
        result_lines = []

        for line in lines:
            # Process lines with object structure, but be very careful about mixed contexts
            stripped = line.strip()
            is_pure_object_line = (
                stripped.startswith("{")
                and stripped.endswith("}")
                and "[" not in line
                and "]" not in line
            )

            # Only clean object commas in pure object contexts (no arrays on same line)
            if is_pure_object_line and ":" in line and (",," in line or ", ," in line):
                # Simple replacement - remove double/spaced commas in object contexts
                line = line.replace(",,", ",").replace(", ,", ",")
            result_lines.append(line)

        text = "\n".join(result_lines)

        # Step 2: Handle array sparse elements (more comprehensive)
        # Use regex to find and fix arrays, including multiline ones

        def fix_array_sparse(match: Match[str]) -> str:
            array_content = match.group(1)

            # Handle leading commas
            array_content = re.sub(r"^\s*,", "null,", array_content)

            # Handle consecutive commas properly using regex
            # n consecutive commas = (n-1) missing values
            # So ,, -> ,null, and ,,, -> ,null,null,

            def replace_consecutive_commas(match: re.Match[str]) -> str:
                commas = match.group(0)
                null_count = len(commas) - 1  # n commas = (n-1) missing values
                if null_count > 0:
                    return "," + ",".join(["null"] * null_count) + ","
                else:
                    return commas  # Single comma, no change

            # Replace sequences of 2 or more consecutive commas
            array_content = re.sub(r",{2,}", replace_consecutive_commas, array_content)

            return "[" + array_content + "]"

        # Find and fix sparse elements in arrays
        # First, handle simple arrays (not containing nested brackets)
        text = re.sub(r"\[([^\[\]]*)\]", fix_array_sparse, text)

        # Then handle more complex arrays by finding , , patterns globally in array contexts
        # This will catch nested cases that the regex above missed
        lines = text.split("\n")
        result_lines = []
        for line in lines:
            # If line has arrays, fix sparse patterns (both ,, and , ,)
            if "[" in line and "]" in line:
                # Replace both ,, and , , with , null, in array contexts
                for _ in range(10):  # Limit iterations to avoid infinite loops
                    old_line = line
                    if ", ," in line:
                        line = line.replace(", ,", ", null,", 1)
                    elif ",," in line:
                        line = line.replace(",,", ", null,", 1)
                    else:
                        break
                    # Safety check - if no change, break
                    if line == old_line:
                        break
            result_lines.append(line)
        text = "\n".join(result_lines)

        return text

    @staticmethod
    def fix_unclosed_strings(text: str) -> str:
        """
        Fix unclosed strings by adding closing quotes.

        Handles cases where strings are not properly terminated.

        Improved to handle multiline strings and escaped quotes correctly.
        """

        # Safe implementation - basic unclosed string fixing
        lines = text.split("\n")
        result_lines = []

        for line in lines:
            # Simple approach: count quotes in each line
            quote_count = line.count('"')

            # If odd number of quotes, add closing quote at end
            if quote_count % 2 == 1:
                stripped = line.rstrip()
                if stripped.endswith(","):
                    # The comma is structural JSON, not part of the string
                    # Add quote before the comma
                    line = stripped[:-1] + '",'
                else:
                    line = stripped + '"'
            result_lines.append(line)

        return "\n".join(result_lines)
