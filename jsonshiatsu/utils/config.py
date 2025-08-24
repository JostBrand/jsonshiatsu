"""
Configuration and limits for jsonshiatsu parsing.

This module defines security limits and configuration options for safe JSON parsing.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ParseLimits:
    """Security limits for JSON parsing to prevent abuse."""

    # Input size limits
    max_input_size: int = 10 * 1024 * 1024
    max_string_length: int = 1024 * 1024
    max_number_length: int = 100

    # Structural limits
    max_nesting_depth: int = 100
    max_object_keys: int = 10000
    max_array_items: int = 100000
    max_total_items: int = 1000000

    # Processing limits
    max_preprocessing_iterations: int = 10

    def __post_init__(self) -> None:
        if self.max_input_size <= 0:
            raise ValueError("max_input_size must be positive")
        if self.max_nesting_depth <= 0:
            raise ValueError("max_nesting_depth must be positive")


@dataclass
class PreprocessingConfig:
    """Granular control over preprocessing steps."""

    extract_from_markdown: bool = True
    remove_comments: bool = True
    unwrap_function_calls: bool = True
    extract_first_json: bool = True
    remove_trailing_text: bool = True

    normalize_quotes: bool = True
    normalize_boolean_null: bool = True

    fix_unescaped_strings: bool = True
    handle_incomplete_json: bool = True
    handle_sparse_arrays: bool = True

    @classmethod
    def conservative(cls) -> "PreprocessingConfig":
        return cls(
            fix_unescaped_strings=False,
            handle_incomplete_json=False,
            handle_sparse_arrays=False,
        )

    @classmethod
    def aggressive(cls) -> "PreprocessingConfig":
        return cls()

    @classmethod
    def from_features(cls, enabled_features: set[str]) -> "PreprocessingConfig":
        config = cls()
        for field in config.__dataclass_fields__:
            setattr(config, field, field in enabled_features)
        return config


@dataclass
class ParseConfig:
    """Configuration options for jsonshiatsu parsing."""

    limits: Optional[ParseLimits] = None

    fallback: bool = True
    duplicate_keys: bool = False
    aggressive: bool = False
    preprocessing_config: Optional[PreprocessingConfig] = None

    include_position: bool = True
    include_context: bool = True
    max_error_context: int = 50

    streaming_threshold: int = 1024 * 1024

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

        if preprocessing_config is not None:
            self.preprocessing_config = preprocessing_config
        elif aggressive:
            self.preprocessing_config = PreprocessingConfig.aggressive()
        else:
            self.preprocessing_config = PreprocessingConfig.aggressive()

        self.include_position = include_position
        self.include_context = include_context
        self.max_error_context = max_error_context
        self.streaming_threshold = streaming_threshold
