"""
jsonshiatsu Error Recovery System.

This module provides partial error parsing and recovery capabilities.
"""

from .strategies import (
    ErrorSeverity,
    PartialParseError,
    PartialParser,
    PartialParseResult,
    RecoveryAction,
    RecoveryLevel,
    extract_valid_data,
    parse_partial,
    parse_with_fallback,
)

__all__ = [
    "parse_partial",
    "extract_valid_data",
    "parse_with_fallback",
    "RecoveryLevel",
    "RecoveryAction",
    "ErrorSeverity",
    "PartialParseResult",
    "PartialParseError",
    "PartialParser",
]
