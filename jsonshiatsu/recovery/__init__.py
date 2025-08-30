"""
jsonshiatsu Error Recovery System.

This module provides partial error parsing and recovery capabilities.
"""

from . import _exports
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
    *_exports.RECOVERY_EXPORTS,
    "PartialParser",
    "ErrorSeverity",
    "PartialParseError",
    "PartialParseResult",
    "RecoveryAction",
    "RecoveryLevel",
]
