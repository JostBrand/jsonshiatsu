"""
Configuration and limits for jsonshiatsu parsing.

This module defines security limits and configuration options for safe JSON parsing.
"""

from dataclasses import dataclass
from typing import Optional, Set


@dataclass
class ParseLimits:
    """Security limits for JSON parsing to prevent abuse."""

    # Input size limits
    max_input_size: int = 10 * 1024 * 1024  # 10MB default
    max_string_length: int = 1024 * 1024  # 1MB per string
    max_number_length: int = 100  # Max digits in a number

    # Structural limits
    max_nesting_depth: int = 100  # Max object/array nesting
    max_object_keys: int = 10000  # Max keys in a single object
    max_array_items: int = 100000  # Max items in a single array
    max_total_items: int = 1000000  # Max total parsed items

    # Processing limits
    max_preprocessing_iterations: int = 10  # Max preprocessing passes

    def __post_init__(self) -> None:
        """Validate limits after initialization."""
        if self.max_input_size <= 0:
            raise ValueError("max_input_size must be positive")
        if self.max_nesting_depth <= 0:
            raise ValueError("max_nesting_depth must be positive")


@dataclass
class PreprocessingConfig:
    """Granular control over preprocessing steps."""

    # Basic preprocessing (always safe)
    extract_from_markdown: bool = True
    remove_comments: bool = True
    unwrap_function_calls: bool = True
    extract_first_json: bool = True
    remove_trailing_text: bool = True

    # Quote and value normalization (generally safe)
    normalize_quotes: bool = True
    normalize_boolean_null: bool = True

    # Advanced preprocessing (potentially risky)
    fix_unescaped_strings: bool = True
    handle_incomplete_json: bool = True
    handle_sparse_arrays: bool = True

    @classmethod
    def conservative(cls) -> "PreprocessingConfig":
        """Conservative preset - only safe transformations."""
        return cls(
            fix_unescaped_strings=False,
            handle_incomplete_json=False,
            handle_sparse_arrays=False,
        )

    @classmethod
    def aggressive(cls) -> "PreprocessingConfig":
        """Aggressive preset - all transformations enabled."""
        return cls()  # All True by default

    @classmethod
    def from_features(cls, enabled_features: Set[str]) -> "PreprocessingConfig":
        """Create config from a set of enabled feature names."""
        config = cls()
        # Start with all disabled
        for field in config.__dataclass_fields__:
            setattr(config, field, field in enabled_features)
        return config


@dataclass
class ParseConfig:
    """Configuration options for jsonshiatsu parsing."""

    # Security limits
    limits: Optional[ParseLimits] = None

    # Parsing behavior
    fallback: bool = True
    duplicate_keys: bool = False
    aggressive: bool = False  # Deprecated - use preprocessing_config
    preprocessing_config: Optional[PreprocessingConfig] = None

    # Error reporting
    include_position: bool = True
    include_context: bool = True
    max_error_context: int = 50

    # Streaming
    streaming_threshold: int = 1024 * 1024  # 1MB

    def __init__(
        self,
        limits: Optional[ParseLimits] = None,
        fallback: bool = True,
        duplicate_keys: bool = False,
        aggressive: bool = False,
        preprocessing_config: Optional[PreprocessingConfig] = None,
        include_position: bool = True,
        include_context: bool = True,
        max_error_context: int = 50,
        streaming_threshold: int = 1024 * 1024,
    ):
        self.limits = limits or ParseLimits()
        self.fallback = fallback
        self.duplicate_keys = duplicate_keys
        self.aggressive = aggressive

        # Handle preprocessing config with backward compatibility
        if preprocessing_config is not None:
            self.preprocessing_config = preprocessing_config
        elif aggressive:
            self.preprocessing_config = PreprocessingConfig.aggressive()
        else:
            self.preprocessing_config = (
                PreprocessingConfig.aggressive()
            )  # New default: try all methods

        self.include_position = include_position
        self.include_context = include_context
        self.max_error_context = max_error_context
        self.streaming_threshold = streaming_threshold
