"""
Error tracking and recovery state management.

This module manages error collection, recovery statistics, and parser state
during partial parsing operations with reduced instance attributes.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from ...core.error_handling import RecoveryStats


@dataclass
class PartialParseError:
    """Represents a parsing error with recovery context."""

    message: str
    position: int = 0
    line: int = 1
    column: int = 1
    context: str = ""
    severity: str = "error"
    path: str = ""
    attempted_recovery: bool = False
    recovery_action: Optional[str] = None


@dataclass
class RecoveryState:
    """Consolidated recovery state with minimal attributes."""

    errors: list[PartialParseError] = field(default_factory=list)
    recovered_data: dict[str, Any] = field(default_factory=dict)
    current_path: str = ""
    stats: RecoveryStats = field(default_factory=RecoveryStats)


class ErrorTracker:
    """
    Manages error collection and recovery state.

    This class reduces the instance attributes of PartialParser by consolidating
    error tracking functionality into a single cohesive component.
    """

    def __init__(self, max_errors: int = 1000):
        self.state = RecoveryState()
        self.max_errors = max_errors

    def add_error(self, error: PartialParseError) -> None:
        """Add an error to the collection."""
        if len(self.state.errors) < self.max_errors:
            error.path = self.state.current_path
            self.state.errors.append(error)

    def can_continue(self) -> bool:
        """Check if recovery should continue based on error count."""
        return len(self.state.errors) < self.max_errors

    def record_recovery_attempt(self, action: str) -> None:
        """Record a recovery attempt."""
        self.state.stats.attempted_recoveries += 1
        if self.state.errors:
            self.state.errors[-1].attempted_recovery = True
            self.state.errors[-1].recovery_action = action

    def record_recovery_success(self) -> None:
        """Record a successful recovery."""
        self.state.stats.successful_recoveries += 1

    def record_skipped_value(self) -> None:
        """Record a skipped value."""
        self.state.stats.skipped_values += 1

    def push_path(self, segment: str) -> None:
        """Push a path segment for error context."""
        if self.state.current_path:
            self.state.current_path += f".{segment}"
        else:
            self.state.current_path = segment

    def pop_path(self) -> None:
        """Pop the last path segment."""
        if "." in self.state.current_path:
            self.state.current_path = self.state.current_path.rsplit(".", 1)[0]
        else:
            self.state.current_path = ""

    def create_error(
        self, message: str, position: int = 0, severity: str = "error"
    ) -> PartialParseError:
        """Create a new error with current context."""
        # Calculate line and column from position would go here
        # For now, simplified implementation
        return PartialParseError(
            message=message,
            position=position,
            severity=severity,
            path=self.state.current_path,
        )

    def get_error_summary(self) -> dict[str, Any]:
        """Get a summary of errors and recovery statistics."""
        return {
            "total_errors": len(self.state.errors),
            "recovery_stats": self.state.stats,
            "error_types": self._categorize_errors(),
            "most_common_errors": self._get_common_errors(),
        }

    def _categorize_errors(self) -> dict[str, int]:
        """Categorize errors by type."""
        categories: dict[str, int] = {}
        for error in self.state.errors:
            category = self._determine_error_category(error.message)
            categories[category] = categories.get(category, 0) + 1
        return categories

    def _determine_error_category(self, message: str) -> str:
        """Determine error category from message."""
        if "quote" in message.lower():
            return "quote_issues"
        elif "comma" in message.lower():
            return "comma_issues"
        elif "bracket" in message.lower() or "brace" in message.lower():
            return "structure_issues"
        elif "string" in message.lower():
            return "string_issues"
        else:
            return "other"

    def _get_common_errors(self, limit: int = 5) -> list[str]:
        """Get the most common error messages."""
        error_counts: dict[str, int] = {}
        for error in self.state.errors:
            msg = error.message
            error_counts[msg] = error_counts.get(msg, 0) + 1

        # Sort by frequency and return top N
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        return [msg for msg, count in sorted_errors[:limit]]
