"""
Safe regex utilities with timeout protection.

This module provides timeout-protected regex operations to prevent
infinite loops from catastrophic backtracking in complex patterns.
"""

import re
import signal
from re import Match
from typing import Any, Callable, Optional, Union


class RegexTimeout(Exception):
    """Exception raised when regex operation exceeds timeout."""


def timeout_handler(signum: int, frame: Any) -> None:
    """Signal handler for regex timeout."""
    raise RegexTimeout("Regex operation timed out")


def safe_regex_sub(
    pattern: str,
    repl: Union[str, Callable[[Match[str]], str]],
    string: str,
    flags: int = 0,
    timeout: int = 5,
) -> str:
    """
    Perform regex substitution with timeout protection.

    Args:
        pattern: Regular expression pattern
        repl: Replacement string or function
        string: Input string to process
        flags: Regex flags
        timeout: Timeout in seconds

    Returns:
        String with substitutions applied, or original string if timeout/error
    """
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        result = re.sub(pattern, repl, string, flags=flags)
        signal.alarm(0)
        return result
    except RegexTimeout:
        return string
    except (re.error, ValueError, TypeError):
        return string


def safe_regex_search(
    pattern: str, string: str, flags: int = 0, timeout: int = 5
) -> Optional[Match[str]]:
    """
    Perform regex search with timeout protection.

    Args:
        pattern: Regular expression pattern
        string: Input string to search
        flags: Regex flags
        timeout: Timeout in seconds

    Returns:
        Match object if found, None if no match or timeout/error
    """
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        result = re.search(pattern, string, flags=flags)
        signal.alarm(0)
        return result
    except RegexTimeout:
        return None
    except (re.error, ValueError, TypeError):
        return None


def safe_regex_findall(
    pattern: str, string: str, flags: int = 0, timeout: int = 5
) -> list[str]:
    """
    Perform regex findall with timeout protection.

    Args:
        pattern: Regular expression pattern
        string: Input string to search
        flags: Regex flags
        timeout: Timeout in seconds

    Returns:
        List of matches, empty list if timeout/error
    """
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        result = re.findall(pattern, string, flags=flags)
        signal.alarm(0)
        return result
    except RegexTimeout:
        return []
    except (re.error, ValueError, TypeError):
        return []


def safe_regex_match(
    pattern: str, string: str, flags: int = 0, timeout: int = 5
) -> Optional[Match[str]]:
    """
    Perform regex match with timeout protection.

    Args:
        pattern: Regular expression pattern
        string: Input string to match
        flags: Regex flags
        timeout: Timeout in seconds

    Returns:
        Match object if found, None if no match or timeout/error
    """
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        result = re.match(pattern, string, flags=flags)
        signal.alarm(0)
        return result
    except RegexTimeout:
        return None
    except (re.error, ValueError, TypeError):
        return None
