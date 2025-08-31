"""
Configuration and limits for jsonshiatsu parsing.

This module defines security limits and configuration options for safe JSON parsing.
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class SizeLimits:
    """Input and content size limits."""
    max_input_size: int = 10 * 1024 * 1024
    max_string_length: int = 1024 * 1024
    max_number_length: int = 100
    max_preprocessing_iterations: int = 10


@dataclass
class StructureLimits:
    """JSON structure complexity limits."""
    max_nesting_depth: int = 100
    max_object_keys: int = 10000
    max_array_items: int = 100000
    max_total_items: int = 1000000


@dataclass
class ParseLimits:
    """Security limits for JSON parsing to prevent abuse."""

    size_limits: Optional[SizeLimits] = None
    structure_limits: Optional[StructureLimits] = None

    def __init__(
        self,
        *,
        size_limits: Optional[SizeLimits] = None,
        structure_limits: Optional[StructureLimits] = None,
        **legacy_args: Any,  # Backward compatibility arguments
    ):
        if size_limits is not None:
            self.size_limits = size_limits
        elif any(arg in legacy_args for arg in [
            'max_input_size', 'max_string_length',
            'max_number_length', 'max_preprocessing_iterations'
        ]):
            self.size_limits = SizeLimits(
                max_input_size=legacy_args.get('max_input_size', 10 * 1024 * 1024),
                max_string_length=legacy_args.get('max_string_length', 1024 * 1024),
                max_number_length=legacy_args.get('max_number_length', 100),
                max_preprocessing_iterations=legacy_args.get('max_preprocessing_iterations', 10),
            )
        else:
            self.size_limits = SizeLimits()

        if structure_limits is not None:
            self.structure_limits = structure_limits
        elif any(arg in legacy_args for arg in [
            'max_nesting_depth', 'max_object_keys',
            'max_array_items', 'max_total_items'
        ]):
            self.structure_limits = StructureLimits(
                max_nesting_depth=legacy_args.get('max_nesting_depth', 100),
                max_object_keys=legacy_args.get('max_object_keys', 10000),
                max_array_items=legacy_args.get('max_array_items', 100000),
                max_total_items=legacy_args.get('max_total_items', 1000000),
            )
        else:
            self.structure_limits = StructureLimits()

        if self.size_limits.max_input_size <= 0:
            raise ValueError("max_input_size must be positive")
        if self.structure_limits.max_nesting_depth <= 0:
            raise ValueError("max_nesting_depth must be positive")

    # Backward compatibility properties
    @property
    def max_input_size(self) -> int:
        """Maximum input size in bytes."""
        assert self.size_limits is not None
        return self.size_limits.max_input_size

    @property
    def max_string_length(self) -> int:
        """Maximum length for individual strings."""
        assert self.size_limits is not None
        return self.size_limits.max_string_length

    @property
    def max_number_length(self) -> int:
        """Maximum length for number strings."""
        assert self.size_limits is not None
        return self.size_limits.max_number_length

    @property
    def max_preprocessing_iterations(self) -> int:
        """Maximum preprocessing iterations allowed."""
        assert self.size_limits is not None
        return self.size_limits.max_preprocessing_iterations

    @property
    def max_nesting_depth(self) -> int:
        """Maximum nesting depth for JSON structures."""
        assert self.structure_limits is not None
        return self.structure_limits.max_nesting_depth

    @property
    def max_object_keys(self) -> int:
        """Maximum number of keys in an object."""
        assert self.structure_limits is not None
        return self.structure_limits.max_object_keys

    @property
    def max_array_items(self) -> int:
        """Maximum number of items in an array."""
        assert self.structure_limits is not None
        return self.structure_limits.max_array_items

    @property
    def max_total_items(self) -> int:
        """Maximum total items across all structures."""
        assert self.structure_limits is not None
        return self.structure_limits.max_total_items


@dataclass
class ExtractionSettings:
    """Settings for content extraction preprocessing."""
    extract_from_markdown: bool = True
    remove_comments: bool = True
    unwrap_function_calls: bool = True
    extract_first_json: bool = True
    remove_trailing_text: bool = True


@dataclass
class NormalizationSettings:
    """Settings for content normalization."""
    normalize_quotes: bool = True
    normalize_boolean_null: bool = True


@dataclass
class RepairSettings:
    """Settings for malformed JSON repair."""
    fix_unescaped_strings: bool = True
    handle_incomplete_json: bool = True
    handle_sparse_arrays: bool = True


@dataclass
class PreprocessingConfig:
    """Granular control over preprocessing steps."""

    extraction: Optional[ExtractionSettings] = None
    normalization: Optional[NormalizationSettings] = None
    repair: Optional[RepairSettings] = None

    def __post_init__(self) -> None:
        if self.extraction is None:
            self.extraction = ExtractionSettings()
        if self.normalization is None:
            self.normalization = NormalizationSettings()
        if self.repair is None:
            self.repair = RepairSettings()

    # Backward compatibility properties
    @property
    def extract_from_markdown(self) -> bool:
        """Whether to extract JSON from markdown code blocks."""
        assert self.extraction is not None
        return self.extraction.extract_from_markdown

    @property
    def remove_comments(self) -> bool:
        """Whether to remove comments from JSON."""
        assert self.extraction is not None
        return self.extraction.remove_comments

    @property
    def unwrap_function_calls(self) -> bool:
        """Whether to unwrap function calls in JSON."""
        assert self.extraction is not None
        return self.extraction.unwrap_function_calls

    @property
    def extract_first_json(self) -> bool:
        """Whether to extract only the first JSON object."""
        assert self.extraction is not None
        return self.extraction.extract_first_json

    @property
    def remove_trailing_text(self) -> bool:
        """Whether to remove trailing text after JSON."""
        assert self.extraction is not None
        return self.extraction.remove_trailing_text

    @property
    def normalize_quotes(self) -> bool:
        """Whether to normalize quote types."""
        assert self.normalization is not None
        return self.normalization.normalize_quotes

    @property
    def normalize_boolean_null(self) -> bool:
        """Whether to normalize boolean and null values."""
        assert self.normalization is not None
        return self.normalization.normalize_boolean_null

    @property
    def fix_unescaped_strings(self) -> bool:
        """Whether to fix unescaped strings."""
        assert self.repair is not None
        return self.repair.fix_unescaped_strings

    @property
    def handle_incomplete_json(self) -> bool:
        """Whether to handle incomplete JSON structures."""
        assert self.repair is not None
        return self.repair.handle_incomplete_json

    @property
    def handle_sparse_arrays(self) -> bool:
        """Whether to handle sparse arrays."""
        assert self.repair is not None
        return self.repair.handle_sparse_arrays

    @classmethod
    def conservative(cls) -> "PreprocessingConfig":
        """Create a conservative preprocessing configuration."""
        return cls(
            extraction=ExtractionSettings(),
            normalization=NormalizationSettings(),
            repair=RepairSettings(
                fix_unescaped_strings=False,
                handle_incomplete_json=False,
                handle_sparse_arrays=False,
            )
        )

    @classmethod
    def aggressive(cls) -> "PreprocessingConfig":
        """Create an aggressive preprocessing configuration."""
        return cls()

    @classmethod
    def from_features(cls, enabled_features: set[str]) -> "PreprocessingConfig":
        """Create configuration from a set of enabled feature names."""
        # Start with all features disabled
        config = cls(
            extraction=ExtractionSettings(
                extract_from_markdown=False,
                remove_comments=False,
                unwrap_function_calls=False,
                extract_first_json=False,
                remove_trailing_text=False,
            ),
            normalization=NormalizationSettings(
                normalize_quotes=False,
                normalize_boolean_null=False,
            ),
            repair=RepairSettings(
                fix_unescaped_strings=False,
                handle_incomplete_json=False,
                handle_sparse_arrays=False,
            )
        )

        # Map old field names to new nested structure
        field_mapping = {
            'extract_from_markdown': ('extraction', 'extract_from_markdown'),
            'remove_comments': ('extraction', 'remove_comments'),
            'unwrap_function_calls': ('extraction', 'unwrap_function_calls'),
            'extract_first_json': ('extraction', 'extract_first_json'),
            'remove_trailing_text': ('extraction', 'remove_trailing_text'),
            'normalize_quotes': ('normalization', 'normalize_quotes'),
            'normalize_boolean_null': ('normalization', 'normalize_boolean_null'),
            'fix_unescaped_strings': ('repair', 'fix_unescaped_strings'),
            'handle_incomplete_json': ('repair', 'handle_incomplete_json'),
            'handle_sparse_arrays': ('repair', 'handle_sparse_arrays'),
        }

        # Enable only the specified features
        for feature_name in enabled_features:
            if feature_name in field_mapping:
                group_name, attr_name = field_mapping[feature_name]
                group = getattr(config, group_name)
                setattr(group, attr_name, True)

        return config


@dataclass
class ParsingBehavior:
    """Core parsing behavior settings."""
    fallback: bool = True
    duplicate_keys: bool = False
    aggressive: bool = False


@dataclass
class ErrorReporting:
    """Error reporting and context settings."""
    include_position: bool = True
    include_context: bool = True
    max_error_context: int = 50


@dataclass
class StreamingConfig:
    """Streaming and performance settings."""
    streaming_threshold: int = 1024 * 1024


@dataclass
class ParseConfig:
    """Configuration options for jsonshiatsu parsing."""

    limits: Optional[ParseLimits] = None
    behavior: Optional[ParsingBehavior] = None
    error_reporting: Optional[ErrorReporting] = None
    streaming: Optional[StreamingConfig] = None
    preprocessing_config: Optional[PreprocessingConfig] = None
    _original_text: Optional[str] = None

    def __init__(
        self,
        *,
        limits: Optional[ParseLimits] = None,
        behavior: Optional[ParsingBehavior] = None,
        error_reporting: Optional[ErrorReporting] = None,
        streaming: Optional[StreamingConfig] = None,
        **config_options: Any,  # preprocessing_config and backward compatibility
    ):
        self.limits = limits or ParseLimits()
        self._original_text = None

        # Handle old-style arguments or new structured arguments
        if behavior is not None:
            self.behavior = behavior
        else:
            self.behavior = ParsingBehavior(
                fallback=config_options.get('fallback', True),
                duplicate_keys=config_options.get('duplicate_keys', False),
                aggressive=config_options.get('aggressive', False),
            )

        if error_reporting is not None:
            self.error_reporting = error_reporting
        else:
            self.error_reporting = ErrorReporting(
                include_position=config_options.get('include_position', True),
                include_context=config_options.get('include_context', True),
                max_error_context=config_options.get('max_error_context', 50),
            )

        if streaming is not None:
            self.streaming = streaming
        else:
            self.streaming = StreamingConfig(
                streaming_threshold=config_options.get('streaming_threshold', 1024 * 1024),
            )

        preprocessing_config = config_options.get('preprocessing_config')
        if preprocessing_config is not None:
            self.preprocessing_config = preprocessing_config
        elif self.behavior.aggressive:
            self.preprocessing_config = PreprocessingConfig.aggressive()
        else:
            self.preprocessing_config = PreprocessingConfig.aggressive()

    # Backward compatibility properties
    @property
    def fallback(self) -> bool:
        """Whether to use fallback parsing for malformed JSON."""
        assert self.behavior is not None
        return self.behavior.fallback

    @fallback.setter
    def fallback(self, value: bool) -> None:
        """Set fallback parsing behavior."""
        assert self.behavior is not None
        self.behavior.fallback = value

    @property
    def duplicate_keys(self) -> bool:
        """Whether to allow duplicate keys in objects."""
        assert self.behavior is not None
        return self.behavior.duplicate_keys

    @duplicate_keys.setter
    def duplicate_keys(self, value: bool) -> None:
        """Set duplicate keys behavior."""
        assert self.behavior is not None
        self.behavior.duplicate_keys = value

    @property
    def aggressive(self) -> bool:
        """Whether to use aggressive parsing mode."""
        assert self.behavior is not None
        return self.behavior.aggressive

    @aggressive.setter
    def aggressive(self, value: bool) -> None:
        """Set aggressive parsing mode."""
        assert self.behavior is not None
        self.behavior.aggressive = value

    @property
    def include_position(self) -> bool:
        """Whether to include position information in errors."""
        assert self.error_reporting is not None
        return self.error_reporting.include_position

    @include_position.setter
    def include_position(self, value: bool) -> None:
        """Set position information inclusion."""
        assert self.error_reporting is not None
        self.error_reporting.include_position = value

    @property
    def include_context(self) -> bool:
        """Whether to include context information in errors."""
        assert self.error_reporting is not None
        return self.error_reporting.include_context

    @include_context.setter
    def include_context(self, value: bool) -> None:
        """Set context information inclusion."""
        assert self.error_reporting is not None
        self.error_reporting.include_context = value

    @property
    def max_error_context(self) -> int:
        """Maximum characters of context to include in errors."""
        assert self.error_reporting is not None
        return self.error_reporting.max_error_context

    @max_error_context.setter
    def max_error_context(self, value: int) -> None:
        """Set maximum error context length."""
        assert self.error_reporting is not None
        self.error_reporting.max_error_context = value

    @property
    def streaming_threshold(self) -> int:
        """Threshold for switching to streaming parsing."""
        assert self.streaming is not None
        return self.streaming.streaming_threshold

    @streaming_threshold.setter
    def streaming_threshold(self, value: int) -> None:
        """Set streaming parsing threshold."""
        assert self.streaming is not None
        self.streaming.streaming_threshold = value

    def set_original_text(self, text: str) -> None:
        """Set the original text for error reporting."""
        self._original_text = text
