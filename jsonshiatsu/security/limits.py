"""
Security limits and validation for jsonshiatsu.
This module provides security validation to prevent resource exhaustion attacks.
"""

from typing import Optional

from ..utils.config import ParseLimits
from .exceptions import SecurityError


class LimitValidator:
    def __init__(self, limits: ParseLimits):
        self.limits = limits
        self.nesting_depth = 0
        self.total_items = 0

    def validate_input_size(self, text: str) -> None:
        if len(text) > self.limits.max_input_size:
            raise SecurityError(
                f"Input size {len(text)} exceeds limit {self.limits.max_input_size}"
            )

    def validate_string_length(
        self, string: str, position: Optional[str] = None
    ) -> None:
        if len(string) > self.limits.max_string_length:
            pos_info = f" at {position}" if position else ""
            raise SecurityError(
                f"String length {len(string)} exceeds limit "
                f"{self.limits.max_string_length}{pos_info}"
            )

    def validate_number_length(
        self, number_str: str, position: Optional[str] = None
    ) -> None:
        if len(number_str) > self.limits.max_number_length:
            pos_info = f" at {position}" if position else ""
            raise SecurityError(
                f"Number length {len(number_str)} exceeds limit "
                f"{self.limits.max_number_length}{pos_info}"
            )

    def enter_structure(self) -> None:
        self.nesting_depth += 1
        if self.nesting_depth > self.limits.max_nesting_depth:
            raise SecurityError(
                f"Nesting depth {self.nesting_depth} exceeds limit "
                f"{self.limits.max_nesting_depth}"
            )

    def exit_structure(self) -> None:
        if self.nesting_depth > 0:
            self.nesting_depth -= 1

    def validate_object_keys(self, key_count: int) -> None:
        if key_count > self.limits.max_object_keys:
            raise SecurityError(
                f"Object key count {key_count} exceeds limit "
                f"{self.limits.max_object_keys}"
            )

    def validate_array_items(self, item_count: int) -> None:
        if item_count > self.limits.max_array_items:
            raise SecurityError(
                f"Array item count {item_count} exceeds limit "
                f"{self.limits.max_array_items}"
            )

    def count_item(self) -> None:
        self.total_items += 1
        if self.total_items > self.limits.max_total_items:
            raise SecurityError(
                f"Total item count {self.total_items} exceeds limit "
                f"{self.limits.max_total_items}"
            )

    def reset(self) -> None:
        self.nesting_depth = 0
        self.total_items = 0
