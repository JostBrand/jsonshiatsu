"""
Preprocessing pipeline for composable JSON preprocessing steps.

This module implements the pipeline pattern to allow flexible composition
of preprocessing steps based on configuration.
"""

from typing import Optional

from ..core.interfaces import PreprocessingStep
from ..utils.config import PreprocessingConfig


class PreprocessingPipeline:
    """Manages a sequence of preprocessing steps applied to JSON text."""

    def __init__(self, steps: Optional[list[PreprocessingStep]] = None):
        self.steps = steps or []

    def add_step(self, step: PreprocessingStep) -> None:
        """Add a preprocessing step to the pipeline."""
        self.steps.append(step)

    def process(self, text: str, config: Optional[PreprocessingConfig] = None) -> str:
        """Apply all applicable preprocessing steps to the text."""
        if config is None:
            config = PreprocessingConfig()

        result = text
        for step in self.steps:
            if step.should_apply(config):
                result = step.process(result, config)
        return result

    @classmethod
    def create_default_pipeline(cls) -> "PreprocessingPipeline":
        """Create a default preprocessing pipeline with standard steps."""
        from .extractors import ContentExtractor, MarkdownExtractor
        from .handlers import CommentHandler, JavaScriptHandler
        from .normalizers import QuoteNormalizer, WhitespaceNormalizer
        from .repairers import StringRepairer, StructureFixer

        pipeline = cls()

        # Content extraction steps
        pipeline.add_step(MarkdownExtractor())
        pipeline.add_step(ContentExtractor())

        # Cleanup steps
        pipeline.add_step(CommentHandler())
        pipeline.add_step(JavaScriptHandler())

        # Normalization steps
        pipeline.add_step(QuoteNormalizer())

        # Structure repair steps (fix structure first, then string content)
        pipeline.add_step(StructureFixer())
        pipeline.add_step(StringRepairer())

        # Final cleanup
        pipeline.add_step(WhitespaceNormalizer())

        return pipeline

    @classmethod
    def create_conservative_pipeline(cls) -> "PreprocessingPipeline":
        """Create a conservative preprocessing pipeline with minimal changes."""
        from .extractors import MarkdownExtractor
        from .handlers import CommentHandler
        from .normalizers import QuoteNormalizer

        pipeline = cls()
        pipeline.add_step(MarkdownExtractor())
        pipeline.add_step(CommentHandler())
        pipeline.add_step(QuoteNormalizer())

        return pipeline

    @classmethod
    def create_aggressive_pipeline(cls) -> "PreprocessingPipeline":
        """Create an aggressive preprocessing pipeline with all repair steps."""
        # Same as default for now, but could be extended
        return cls.create_default_pipeline()


class PreprocessingStepBase:
    """Base class for preprocessing steps with common functionality."""

    def should_apply(self, config: PreprocessingConfig) -> bool:
        """Default implementation - always apply. Override in subclasses."""
        return True

    def process(self, text: str, config: PreprocessingConfig) -> str:
        """Process the text. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement process()")
