"""
Optimized preprocessor for jsonshiatsu with improved regex performance.

Key optimizations:
- Pre-compiled regex patterns to avoid repeated compilation
- Optimized pattern matching order based on frequency
- Fast-path detection for common cases
- Reduced regex complexity where possible
"""

import re
import signal
from functools import lru_cache
from typing import Any, Match, Optional, Pattern, Tuple


class RegexTimeout(Exception):
    pass


def timeout_handler(signum: int, frame: Any) -> None:
    raise RegexTimeout("Regex operation timed out")


def safe_pattern_search(
    pattern: Pattern[str], string: str, timeout: int = 5
) -> Optional[Match[str]]:
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        result = pattern.search(string)
        signal.alarm(0)
        return result
    except RegexTimeout:
        return None
    except Exception:
        return None


def safe_pattern_sub(
    pattern: Pattern[str], repl: str, string: str, timeout: int = 5
) -> str:
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        result = pattern.sub(repl, string)
        signal.alarm(0)
        return result
    except RegexTimeout:
        return string
    except Exception:
        return string


def safe_pattern_match(
    pattern: Pattern[str], string: str, timeout: int = 5
) -> Optional[Match[str]]:
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        result = pattern.match(string)
        signal.alarm(0)
        return result
    except RegexTimeout:
        return None
    except Exception:
        return None


class OptimizedJSONPreprocessor:

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

    _boolean_patterns = [
        (re.compile(r"\bTrue\b"), "true"),
        (re.compile(r"\bFalse\b"), "false"),
        (re.compile(r"\bNone\b"), "null"),
        (re.compile(r"\byes\b", re.IGNORECASE), "true"),
        (re.compile(r"\bno\b", re.IGNORECASE), "false"),
        (re.compile(r"\bundefined\b", re.IGNORECASE), "null"),
    ]

    _quote_replacements = {
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
        if "```" not in text and "`" not in text:
            return text

        match = safe_pattern_search(cls._json_block_pattern, text)
        if match:
            return match.group(1).strip()

        match = safe_pattern_search(cls._inline_pattern, text)
        if match:
            return match.group(1).strip()

        return text

    @classmethod
    def remove_trailing_text(cls, text: str) -> str:
        text = text.strip()

        if not text or text[-1] not in "}\"'elE":
            return text

        brace_count = 0
        bracket_count = 0
        in_string = False
        string_char = None
        escaped = False
        last_valid_pos = -1

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

                    if brace_count == 0 and bracket_count == 0 and char in "}\"'elE":
                        last_valid_pos = actual_pos

        if last_valid_pos > -1:
            return text[: last_valid_pos + 1]

        return text

    @classmethod
    def remove_comments(cls, text: str) -> str:
        if "//" not in text and "/*" not in text:
            return text

        if "//" in text:
            text = safe_pattern_sub(cls._single_comment_pattern, "", text)

        if "/*" in text:
            text = safe_pattern_sub(cls._block_comment_pattern, "", text)

        return text

    @classmethod
    def extract_first_json(cls, text: str) -> str:
        text = text.strip()

        if text and text[0] in "{[":
            return cls._extract_first_structure_fast(text)

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

                if brace_count == 0 and bracket_count == 0 and i > 0:
                    return text[: i + 1]

        return text

    @classmethod
    def unwrap_function_calls(cls, text: str) -> str:
        text = text.strip()

        if not ("(" in text or "return" in text or "=" in text):
            return text

        for pattern in [cls._return_pattern, cls._func_pattern, cls._var_pattern]:
            match = safe_pattern_match(pattern, text)
            if match:
                return match.group(1).strip()

        return text

    @classmethod
    def normalize_quotes(cls, text: str) -> str:
        if not any(char in cls._quote_replacements for char in text):
            return text

        for old_char, new_char in cls._quote_replacements.items():
            if old_char in text:
                text = text.replace(old_char, new_char)

        return text

    @classmethod
    def normalize_boolean_null(cls, text: str) -> str:
        if not any(
            keyword in text
            for keyword in ["True", "False", "None", "yes", "no", "undefined"]
        ):
            return text

        for pattern, replacement in cls._boolean_patterns:
            if pattern.pattern.lower().replace("\\b", "") in text.lower():
                text = safe_pattern_sub(pattern, replacement, text)

        return text

    @classmethod
    def fix_unescaped_strings(cls, text: str) -> str:
        if "\\" not in text:
            return text

        from ..core.transformer import JSONPreprocessor

        return JSONPreprocessor.fix_unescaped_strings(text)

    @classmethod
    def handle_incomplete_json(cls, text: str) -> str:
        text = text.strip()

        if not text:
            return text

        if text[-1] in "}\"'":
            return text

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

        if in_string and string_char:
            text += string_char

        closing_map = {"{": "}", "[": "]"}
        while stack:
            opener = stack.pop()
            text += closing_map[opener]

        return text

    @classmethod
    def preprocess(
        cls, text: str, aggressive: bool = False, config: Optional[Any] = None
    ) -> str:
        if not text or not text.strip():
            return text

        if config is None:
            from ..utils.config import PreprocessingConfig

            if aggressive:
                config = PreprocessingConfig.aggressive()
            else:
                config = PreprocessingConfig.aggressive()

        text_preview = text[:500]
        (
            has_markdown,
            has_comments,
            has_wrappers,
            has_special_quotes,
            has_python_bools,
        ) = cls._detect_patterns(text_preview)

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
