"""
Content extraction preprocessing steps.

This module contains preprocessing steps that extract JSON content from
various text formats like markdown code blocks and mixed content.
"""

import re

from ..utils.config import PreprocessingConfig
from .base import PreprocessingStepBase


class MarkdownExtractor(PreprocessingStepBase):
    """Extracts JSON from markdown code blocks."""

    def should_apply(self, config: PreprocessingConfig) -> bool:
        """Apply if markdown extraction is enabled."""
        return config.extract_from_markdown

    def process(self, text: str, config: PreprocessingConfig) -> str:
        """Extract JSON from markdown code blocks."""
        if not config.extract_from_markdown:
            return text
        return self._extract_from_code_blocks(text)

    @staticmethod
    def _extract_from_code_blocks(text: str) -> str:
        """Extract content from markdown code blocks."""
        # Try fenced code blocks first (```json ... ```)
        json_pattern = r"```(?:json|javascript|js)?\s*\n?(.*?)\n?```"
        match = re.search(json_pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Try inline code blocks (`...`)
        inline_pattern = r"`([^`]+)`"
        match = re.search(inline_pattern, text)
        if match:
            content = match.group(1).strip()
            # Only use if it looks like JSON
            if content.startswith(("{", "[")):
                return content

        return text


class ContentExtractor(PreprocessingStepBase):
    """Extracts the first JSON-like content and removes trailing text."""

    def should_apply(self, config: PreprocessingConfig) -> bool:
        """Apply if content extraction is enabled."""
        return config.extract_first_json or config.remove_trailing_text

    def process(self, text: str, config: PreprocessingConfig) -> str:
        """Extract JSON content and remove trailing text."""
        result = text

        if config.extract_first_json:
            result = self.extract_first_json(result)

        if config.remove_trailing_text:
            result = self.remove_trailing_text(result)

        return result

    @staticmethod
    def extract_first_json(text: str) -> str:
        """Extract the first JSON-like structure from text."""
        text = text.strip()
        if not text:
            return text

        # Find the start of JSON
        start_pos = -1
        for i, char in enumerate(text):
            if char in "{[":
                start_pos = i
                break

        if start_pos == -1:
            return text

        # Find the end by tracking brackets/braces
        stack = []
        in_string = False
        escape_next = False

        for i in range(start_pos, len(text)):
            char = text[i]

            if escape_next:
                escape_next = False
                continue

            if char == "\\" and in_string:
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if in_string:
                continue

            if char in "{[":
                stack.append(char)
            elif char in "}]":
                if not stack:
                    break

                expected = "{" if char == "}" else "["
                if stack[-1] == expected:
                    stack.pop()
                    if not stack:
                        return text[start_pos : i + 1]

        # If we didn't find a complete structure, return from start to end
        return text[start_pos:]

    @staticmethod
    def remove_trailing_text(text: str) -> str:
        """Remove trailing text after JSON content."""
        text = text.strip()
        if not text:
            return text

        # Use a simpler approach: find JSON ending and cut there
        # Track bracket/brace depth and find where it becomes balanced
        stack = []
        in_string = False
        escape_next = False
        last_json_pos = -1

        for i, char in enumerate(text):
            if escape_next:
                escape_next = False
                continue

            if char == "\\" and in_string:
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if in_string:
                continue

            if char in "{[":
                stack.append(char)
            elif char in "}]" and stack:
                expected = "{" if char == "}" else "["
                if stack[-1] == expected:
                    stack.pop()
                    if not stack:
                        # We've closed all brackets/braces
                        last_json_pos = i

        if last_json_pos != -1:
            return text[: last_json_pos + 1]
        return text
