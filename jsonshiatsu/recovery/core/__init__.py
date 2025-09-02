"""
Recovery core module.

This module contains the internal implementation components for error recovery
during JSON parsing. The main recovery strategies and public API remain in
the parent recovery module.
"""

from .tracker import ErrorTracker, RecoveryState

__all__ = ["ErrorTracker", "RecoveryState"]
