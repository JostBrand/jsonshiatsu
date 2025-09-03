"""
Legacy JSON preprocessor facade.

This module provides backward compatibility for the original JSONPreprocessor
while delegating to the new modular preprocessing pipeline.
"""

import re
import warnings
from typing import Any, Optional

from ..preprocessing import PreprocessingPipeline
from ..preprocessing.extractors import ContentExtractor, MarkdownExtractor
from ..preprocessing.handlers import CommentHandler, JavaScriptHandler
from ..preprocessing.normalizers import QuoteNormalizer, WhitespaceNormalizer
from ..preprocessing.repairers import StringRepairer, StructureFixer
from ..utils.config import PreprocessingConfig
from .array_object_handler import ArrayObjectHandler
from .string_preprocessors import StringPreprocessor


class JSONPreprocessor:
    """
    Legacy facade for JSON preprocessing.

    This class maintains backward compatibility while delegating to the new
    preprocessing pipeline architecture. New code should use PreprocessingPipeline directly.
    """

    def __init__(self) -> None:
        """Initialize with default preprocessing pipeline."""
        self.pipeline = PreprocessingPipeline.create_default_pipeline()

    @classmethod
    def preprocess(
        cls, text: str, aggressive: bool = False, config: Optional[Any] = None
    ) -> str:
        """
        Apply preprocessing steps to clean malformed JSON.

        Args:
            text: Raw text that may contain JSON
            aggressive: If True, apply aggressive cleaning (deprecated, use config)
            config: PreprocessingConfig object for granular control

        Returns:
            Cleaned JSON string
        """
        if config is None:
            config = (
                PreprocessingConfig.aggressive()
                if aggressive
                else PreprocessingConfig.conservative()
            )

        # Create processor and apply pipeline
        processor = cls()
        return processor.pipeline.process(text, config)

    # Legacy static methods with deprecation warnings

    @staticmethod
    def extract_from_markdown(text: str) -> str:
        """Legacy method. Use MarkdownExtractor instead."""
        warnings.warn(
            "JSONPreprocessor.extract_from_markdown is deprecated. "
            "Use preprocessing.MarkdownExtractor instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        extractor = MarkdownExtractor()
        config = PreprocessingConfig()
        return extractor.process(text, config)

    @staticmethod
    def remove_comments(text: str) -> str:
        """Legacy method. Use CommentHandler instead."""
        warnings.warn(
            "JSONPreprocessor.remove_comments is deprecated. "
            "Use preprocessing.CommentHandler instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        handler = CommentHandler()
        config = PreprocessingConfig()
        return handler.process(text, config)

    @staticmethod
    def normalize_quotes(text: str) -> str:
        """Legacy method. Use QuoteNormalizer instead."""
        warnings.warn(
            "JSONPreprocessor.normalize_quotes is deprecated. "
            "Use preprocessing.QuoteNormalizer instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        normalizer = QuoteNormalizer()
        config = PreprocessingConfig()
        return normalizer.process(text, config)

    @staticmethod
    def fix_missing_commas(text: str) -> str:
        """Legacy method. Use StructureFixer instead."""
        warnings.warn(
            "JSONPreprocessor.fix_missing_commas is deprecated. "
            "Use preprocessing.StructureFixer instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        fixer = StructureFixer()
        config = PreprocessingConfig()
        return fixer.process(text, config)

    @staticmethod
    def handle_incomplete_json(text: str) -> str:
        """Legacy method. Use StructureFixer instead."""
        warnings.warn(
            "JSONPreprocessor.handle_incomplete_json is deprecated. "
            "Use preprocessing.StructureFixer instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        fixer = StructureFixer()
        config = PreprocessingConfig()
        if config.repair is not None:
            config.repair.handle_incomplete_json = True
        return fixer.process(text, config)

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Legacy method. Use WhitespaceNormalizer instead."""
        warnings.warn(
            "JSONPreprocessor.normalize_whitespace is deprecated. "
            "Use preprocessing.WhitespaceNormalizer instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        normalizer = WhitespaceNormalizer()
        config = PreprocessingConfig()
        return normalizer.process(text, config)

    # Keep a few essential methods without deprecation for internal use

    @staticmethod
    def handle_streaming_responses(text: str) -> str:
        """Handle streaming response patterns."""
        # Basic streaming response handling - could be moved to a separate handler

        # Remove common streaming prefixes
        streaming_patterns = [
            r"^data:\s*",  # Server-sent events
            r"^\d+\s*\n",  # Chunked transfer encoding sizes
        ]

        result = text
        for pattern in streaming_patterns:
            result = re.sub(pattern, "", result, flags=re.MULTILINE)

        return result.strip()

    @staticmethod
    def handle_sparse_arrays(text: str) -> str:
        """Handle sparse arrays - delegates to ArrayObjectHandler."""
        return ArrayObjectHandler.handle_sparse_arrays(text)

    @staticmethod
    def extract_first_json(text: str) -> str:
        """Extract the first JSON structure from text."""
        extractor = ContentExtractor()
        return extractor.extract_first_json(text)

    @staticmethod
    def normalize_boolean_null(text: str) -> str:
        """Legacy method. Use StringRepairer instead."""
        warnings.warn(
            "JSONPreprocessor.normalize_boolean_null is deprecated. "
            "Use preprocessing.StringRepairer instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        repairer = StringRepairer()
        return repairer.normalize_boolean_null(text)

    @staticmethod
    def unwrap_function_calls(text: str) -> str:
        """Legacy method. Use JavaScriptHandler instead."""
        warnings.warn(
            "JSONPreprocessor.unwrap_function_calls is deprecated. "
            "Use preprocessing.JavaScriptHandler instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        handler = JavaScriptHandler()
        config = PreprocessingConfig()
        return handler.process(text, config)

    @staticmethod
    def fix_unescaped_strings(text: str) -> str:
        """Legacy method. Use StringPreprocessor instead."""
        warnings.warn(
            "JSONPreprocessor.fix_unescaped_strings is deprecated. "
            "Use preprocessing.StringPreprocessor instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return StringPreprocessor.fix_unescaped_strings(text)

    @staticmethod
    def remove_trailing_text(text: str) -> str:
        """Legacy method. Use ContentExtractor instead."""
        warnings.warn(
            "JSONPreprocessor.remove_trailing_text is deprecated. "
            "Use preprocessing.ContentExtractor instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        extractor = ContentExtractor()
        return extractor.remove_trailing_text(text)
