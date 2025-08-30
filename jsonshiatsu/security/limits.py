"""
Security limits and validation for jsonshiatsu.
This module provides security validation to prevent resource exhaustion attacks.
"""

from typing import Optional

from ..utils.config import ParseLimits
from .exceptions import SecurityError


class LimitValidator:
    """Validates parsing limits to prevent resource exhaustion attacks."""

    def __init__(self, limits: ParseLimits):
        self.limits = limits
        self.nesting_depth = 0
        self.total_items = 0

    def validate_input_size(self, text: str) -> None:
        """Validate that input text size is within limits."""
        if len(text) > self.limits.max_input_size:
            raise SecurityError(
                f"Input size {len(text)} exceeds limit {self.limits.max_input_size}"
            )

    def validate_string_length(
        self, string: str, position: Optional[str] = None
    ) -> None:
        """Validate that string length is within limits."""
        if len(string) > self.limits.max_string_length:
            pos_info = f" at {position}" if position else ""
            raise SecurityError(
                f"String length {len(string)} exceeds limit "
                f"{self.limits.max_string_length}{pos_info}"
            )

    def validate_number_length(
        self, number_str: str, position: Optional[str] = None
    ) -> None:
        """Validate that number string length is within limits."""
        if len(number_str) > self.limits.max_number_length:
            pos_info = f" at {position}" if position else ""
            raise SecurityError(
                f"Number length {len(number_str)} exceeds limit "
                f"{self.limits.max_number_length}{pos_info}"
            )

    def enter_structure(self) -> None:
        """Track entering a nested structure and validate depth."""
        self.nesting_depth += 1
        if self.nesting_depth > self.limits.max_nesting_depth:
            raise SecurityError(
                f"Nesting depth {self.nesting_depth} exceeds limit "
                f"{self.limits.max_nesting_depth}"
            )

    def exit_structure(self) -> None:
        """Track exiting a nested structure."""
        if self.nesting_depth > 0:
            self.nesting_depth -= 1

    def validate_object_keys(self, key_count: int) -> None:
        """Validate that object key count is within limits."""
        if key_count > self.limits.max_object_keys:
            raise SecurityError(
                f"Object key count {key_count} exceeds limit "
                f"{self.limits.max_object_keys}"
            )

    def validate_array_items(self, item_count: int) -> None:
        """Validate that array item count is within limits."""
        if item_count > self.limits.max_array_items:
            raise SecurityError(
                f"Array item count {item_count} exceeds limit "
                f"{self.limits.max_array_items}"
            )

    def count_item(self) -> None:
        """Track total items parsed and validate count."""
        self.total_items += 1
        if self.total_items > self.limits.max_total_items:
            raise SecurityError(
                f"Total item count {self.total_items} exceeds limit "
                f"{self.limits.max_total_items}"
            )

    def reset(self) -> None:
        """Reset validator state for reuse."""
        self.nesting_depth = 0
        self.total_items = 0
