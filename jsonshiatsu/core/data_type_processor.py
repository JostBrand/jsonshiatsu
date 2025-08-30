"""
Data type processing utilities for JSON repair.

This module handles normalization and processing of various data types
including booleans, null values, special numbers, and empty values.
"""

import re
from re import Match

from .regex_utils import safe_regex_sub


class DataTypeProcessor:
    """Handles data type normalization and processing operations."""

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
