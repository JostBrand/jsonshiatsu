"""
Optimized preprocessor for jsonshiatsu with improved regex performance.

Key optimizations:
- Pre-compiled regex patterns to avoid repeated compilation
- Optimized pattern matching order based on frequency
- Fast-path detection for common cases
- Reduced regex complexity where possible
"""

import re
from functools import lru_cache
from typing import Any, Optional, Tuple


class OptimizedJSONPreprocessor:
    """High-performance preprocessor with compiled regex patterns."""

    # Pre-compiled regex patterns for better performance
    _json_block_pattern = re.compile(
        r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL | re.IGNORECASE
    )
    _inline_pattern = re.compile(r"`([^`]*[{[].*?[}\]][^`]*)`", re.DOTALL)
    _single_comment_pattern = re.compile(r"//.*?(?=\n|$)", re.MULTILINE)
    _block_comment_pattern = re.compile(r"/\*.*?\*/", re.DOTALL)
    _func_pattern = re.compile(
        r"^[a-zA-Z_][a-zA-Z0-9_.]*\s*\(\s*(.*)\s*\)\s*;?\s*$", re.DOTALL
    )
    _return_pattern = re.compile(r"^return\s+(.*?)\s*;?\s*$", re.DOTALL | re.IGNORECASE)
    _var_pattern = re.compile(
        r"^(?:const|let|var)\s+\w+\s*=\s*(.*?)\s*;?\s*$", re.DOTALL | re.IGNORECASE
    )
    _unescaped_backslash = re.compile(r'\\(?![\\"/bfnrtux])')

    # Boolean/null replacement patterns
    _boolean_patterns = [
        (re.compile(r"\bTrue\b"), "true"),
        (re.compile(r"\bFalse\b"), "false"),
        (re.compile(r"\bNone\b"), "null"),
        (re.compile(r"\byes\b", re.IGNORECASE), "true"),
        (re.compile(r"\bno\b", re.IGNORECASE), "false"),
        (re.compile(r"\bundefined\b", re.IGNORECASE), "null"),
    ]

    # Quote normalization dictionary for fast lookup
    _quote_replacements = {
        '"': '"',
        '"': '"',
        "„": '"',  # Smart double quotes
        """: "'", """: "'",
        "‚": "'",  # Smart single quotes
        "«": '"',
        "»": '"',  # Guillemets
        "‹": "'",
        "›": "'",  # Single guillemets
        "`": "'",
        "´": "'",  # Backticks and accents
        "「": '"',
        "」": '"',  # CJK quotes
        "『": '"',
        "』": '"',  # CJK double quotes
    }

    @classmethod
    @lru_cache(maxsize=128)
    def _detect_patterns(cls, text_preview: str) -> Tuple[bool, bool, bool, bool, bool]:
        """Detect which preprocessing patterns are needed (cached for performance)."""
        has_markdown = "```" in text_preview
        has_comments = "//" in text_preview or "/*" in text_preview
        has_wrappers = "return " in text_preview or "(" in text_preview
        has_special_quotes = any(
            char in text_preview for char in cls._quote_replacements
        )
        has_python_bools = (
            "True" in text_preview or "False" in text_preview or "None" in text_preview
        )

        return (
            has_markdown,
            has_comments,
            has_wrappers,
            has_special_quotes,
            has_python_bools,
        )

    @classmethod
    def extract_from_markdown(cls, text: str) -> str:
        """Extract JSON from markdown with optimized regex."""
        # Fast path: check if markdown patterns exist
        if "```" not in text and "`" not in text:
            return text

        # Try fenced code blocks first (most common)
        match = cls._json_block_pattern.search(text)
        if match:
            return match.group(1).strip()

        # Try inline code blocks
        match = cls._inline_pattern.search(text)
        if match:
            return match.group(1).strip()

        return text

    @classmethod
    def remove_trailing_text(cls, text: str) -> str:
        """Remove trailing text with optimized structure detection."""
        text = text.strip()

        # Fast path: if text doesn't end with }, ], or quote, likely no trailing text
        if not text or text[-1] not in "}\"'elE":
            return text

        # Optimized bracket/brace counting with early termination
        brace_count = 0
        bracket_count = 0
        in_string = False
        string_char = None
        escaped = False
        last_valid_pos = -1

        # Process in chunks for better performance on large strings
        chunk_size = 1000
        for chunk_start in range(0, len(text), chunk_size):
            chunk_end = min(chunk_start + chunk_size, len(text))
            chunk = text[chunk_start:chunk_end]

            for i, char in enumerate(chunk):
                actual_pos = chunk_start + i

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

                    # Check for complete structure
                    if brace_count == 0 and bracket_count == 0 and char in "}\"'elE":
                        last_valid_pos = actual_pos

        if last_valid_pos > -1:
            return text[: last_valid_pos + 1]

        return text

    @classmethod
    def remove_comments(cls, text: str) -> str:
        """Remove comments with optimized regex patterns."""
        # Fast path: check if comments exist
        if "//" not in text and "/*" not in text:
            return text

        # Remove single-line comments first (more common)
        if "//" in text:
            text = cls._single_comment_pattern.sub("", text)

        # Remove block comments
        if "/*" in text:
            text = cls._block_comment_pattern.sub("", text)

        return text

    @classmethod
    def extract_first_json(cls, text: str) -> str:
        """Extract first JSON with optimized bracket detection."""
        text = text.strip()

        # Fast path: if text starts with { or [, likely already clean
        if text and text[0] in "{[":
            return cls._extract_first_structure_fast(text)

        # Find first JSON structure start
        start_pos = -1
        for i, char in enumerate(text):
            if char in "{[":
                start_pos = i
                break

        if start_pos == -1:
            return text

        return cls._extract_first_structure_fast(text[start_pos:])

    @classmethod
    def _extract_first_structure_fast(cls, text: str) -> str:
        """Fast structure extraction for well-formed JSON."""
        if not text:
            return text

        brace_count = 0
        bracket_count = 0
        in_string = False
        string_char = None
        escaped = False

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

                # Complete structure found
                if brace_count == 0 and bracket_count == 0 and i > 0:
                    return text[: i + 1]

        return text

    @classmethod
    def unwrap_function_calls(cls, text: str) -> str:
        """Unwrap function calls with optimized pattern matching."""
        text = text.strip()

        # Fast path: check for common wrapper patterns
        if not ("(" in text or "return" in text or "=" in text):
            return text

        # Check patterns in order of likelihood
        for pattern in [cls._return_pattern, cls._func_pattern, cls._var_pattern]:
            match = pattern.match(text)
            if match:
                return match.group(1).strip()

        return text

    @classmethod
    def normalize_quotes(cls, text: str) -> str:
        """Normalize quotes with optimized character replacement."""
        # Fast path: check if special quotes exist
        if not any(char in cls._quote_replacements for char in text):
            return text

        # Replace special quotes
        for old_char, new_char in cls._quote_replacements.items():
            if old_char in text:
                text = text.replace(old_char, new_char)

        return text

    @classmethod
    def normalize_boolean_null(cls, text: str) -> str:
        """Normalize boolean/null values with optimized pattern matching."""
        # Fast path: check if patterns exist
        if not any(
            keyword in text
            for keyword in ["True", "False", "None", "yes", "no", "undefined"]
        ):
            return text

        # Apply replacements efficiently
        for pattern, replacement in cls._boolean_patterns:
            if pattern.pattern.lower().replace("\\b", "") in text.lower():
                text = pattern.sub(replacement, text)

        return text

    @classmethod
    def fix_unescaped_strings(cls, text: str) -> str:
        """Fix unescaped strings with intelligent path detection."""
        # Fast path: check if backslashes exist
        if "\\" not in text:
            return text

        # Use the same smart logic as the regular transformer
        from ..core.transformer import JSONPreprocessor

        return JSONPreprocessor.fix_unescaped_strings(text)

    @classmethod
    def handle_incomplete_json(cls, text: str) -> str:
        """Handle incomplete JSON with fast bracket counting."""
        text = text.strip()

        if not text:
            return text

        # Fast path: if text ends with proper closing, likely complete
        if text[-1] in "}\"'":
            return text

        # Track unclosed structures efficiently
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
                elif char == "}" and stack and stack[-1] == "{":
                    stack.pop()
                elif char == "]" and stack and stack[-1] == "[":
                    stack.pop()

        # Close unclosed strings
        if in_string and string_char:
            text += string_char

        # Close unclosed structures
        closing_map = {"{": "}", "[": "]"}
        while stack:
            opener = stack.pop()
            text += closing_map[opener]

        return text

    @classmethod
    def preprocess(
        cls, text: str, aggressive: bool = False, config: Optional[Any] = None
    ) -> str:
        """Optimized preprocessing with pattern detection and granular control."""
        if not text or not text.strip():
            return text

        # Handle backward compatibility
        if config is None:
            from ..utils.config import PreprocessingConfig

            if aggressive:
                config = PreprocessingConfig.aggressive()
            else:
                config = PreprocessingConfig.aggressive()  # New default

        # Detect patterns needed (cached for repeated similar inputs)
        text_preview = text[:500]  # Sample for pattern detection
        (
            has_markdown,
            has_comments,
            has_wrappers,
            has_special_quotes,
            has_python_bools,
        ) = cls._detect_patterns(text_preview)

        # Apply transformations based on both pattern detection and config
        if config.extract_from_markdown and has_markdown:
            text = cls.extract_from_markdown(text)

        if config.remove_comments and has_comments:
            text = cls.remove_comments(text)

        if has_wrappers:
            if config.unwrap_function_calls:
                text = cls.unwrap_function_calls(text)
            if config.extract_first_json:
                text = cls.extract_first_json(text)
            if config.remove_trailing_text:
                text = cls.remove_trailing_text(text)

        if config.normalize_quotes and has_special_quotes:
            text = cls.normalize_quotes(text)

        if config.normalize_boolean_null and has_python_bools:
            text = cls.normalize_boolean_null(text)

        if config.fix_unescaped_strings:
            text = cls.fix_unescaped_strings(text)

        if config.handle_incomplete_json:
            text = cls.handle_incomplete_json(text)

        return text.strip()
