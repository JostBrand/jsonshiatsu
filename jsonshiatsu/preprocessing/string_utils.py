"""
Utility functions for string processing that are commonly used across preprocessing modules.

This module contains shared logic for string state tracking and manipulation
to reduce code duplication.
"""

from collections.abc import Callable, Generator
from typing import Optional

# Type aliases for cleaner annotations
ProcessorFunction = Callable[[str, int, str], Optional[tuple[str, int]]]
ProcessorFactory = Callable[[str, ProcessorFunction, Optional[ProcessorFunction]], str]


class StringStateTracker:
    """Helper class to track string state during text processing."""

    def __init__(self) -> None:
        self.in_string = False
        self.string_char: Optional[str] = None

    def update_state(self, char: str, prev_char: Optional[str] = None) -> bool:
        """
        Update string state based on current character.

        Args:
            char: Current character
            prev_char: Previous character (for escape detection)

        Returns:
            True if currently inside a string
        """
        if not self.in_string and char in ['"', "'"]:
            self.in_string = True
            self.string_char = char
        elif self.in_string and char == self.string_char and prev_char != "\\":
            self.in_string = False
            self.string_char = None

        return self.in_string

    def reset(self) -> None:
        """Reset string state tracking."""
        self.in_string = False
        self.string_char = None


def iterate_with_string_tracking(
    text: str,
) -> Generator[tuple[int, str, bool], None, None]:
    """
    Iterate through text with string state tracking.

    Yields:
        Tuple of (index, character, in_string_state)
    """
    tracker = StringStateTracker()

    for i, char in enumerate(text):
        prev_char = text[i - 1] if i > 0 else None
        in_string = tracker.update_state(char, prev_char)
        yield i, char, in_string


def find_string_end_simple(text: str, start: int) -> int:
    """
    Find the end of a quoted string starting at position start.

    Args:
        text: The text to search in
        start: Starting position (should point to opening quote)

    Returns:
        Index of closing quote, or -1 if not found
    """
    if start >= len(text) or text[start] not in ['"', "'"]:
        return -1

    quote_char = text[start]
    i = start + 1

    while i < len(text):
        if text[i] == quote_char and (i == start + 1 or text[i - 1] != "\\"):
            return i
        if text[i] == "\\" and i + 1 < len(text):
            i += 2  # Skip escaped character
        else:
            i += 1

    return -1


def process_text_with_string_awareness(
    text: str, processor_func: Callable[[str, int, bool], Optional[str]]
) -> str:
    """
    Process text while being aware of string boundaries.

    Args:
        text: The text to process
        processor_func: Function that takes (char, index, in_string)
                        and returns processed character(s)

    Returns:
        Processed text
    """
    result = []
    tracker = StringStateTracker()

    for i, char in enumerate(text):
        prev_char = text[i - 1] if i > 0 else None
        in_string = tracker.update_state(char, prev_char)
        processed = processor_func(char, i, in_string)
        if processed is not None:
            result.append(processed)
        else:
            result.append(char)

    return "".join(result)


def find_closing_quote(text: str, start: int) -> int:
    """
    Find closing quote for a string starting at start position.
    Handles escape sequences properly.

    Args:
        text: Text to search in
        start: Position of opening quote

    Returns:
        Position of closing quote or -1 if not found
    """
    if start >= len(text) or text[start] not in ['"', "'"]:
        return -1

    quote_char = text[start]
    i = start + 1
    while i < len(text):
        if text[i] == quote_char and (i == start + 1 or text[i - 1] != "\\"):
            return i
        if text[i] == "\\" and i + 1 < len(text):
            i += 2  # Skip escaped character
        else:
            i += 1

    return -1


def create_string_aware_processor() -> ProcessorFactory:
    """
    Create a reusable string-aware text processor.

    Returns:
        A function that can be used to process text with string state tracking
    """

    def processor(
        text: str,
        process_outside_strings: ProcessorFunction,
        process_inside_strings: Optional[ProcessorFunction] = None,
    ) -> str:
        """
        Process text with string awareness.

        Args:
            text: Text to process
            process_outside_strings: Function to call for characters outside strings
            process_inside_strings: Function to call for characters inside strings (optional)

        Returns:
            Processed text
        """
        result = []
        i = 0
        in_string = False
        string_char = None

        while i < len(text):
            char = text[i]
            # Track string state
            if not in_string and char in ['"', "'"]:
                in_string = True
                string_char = char
                result.append(char)
                i += 1
                continue
            if in_string and char == string_char and (i == 0 or text[i - 1] != "\\"):
                in_string = False
                string_char = None
                result.append(char)
                i += 1
                continue

            # Process character based on string state
            if in_string:
                if process_inside_strings:
                    processed = process_inside_strings(text, i, char)
                    if processed is not None:
                        result.append(processed[0])
                        i = processed[1]
                        continue
                result.append(char)
                i += 1
            else:
                processed = process_outside_strings(text, i, char)
                if processed is not None:
                    result.append(processed[0])
                    i = processed[1]
                    continue
                result.append(char)
                i += 1

        return "".join(result)

    return processor
