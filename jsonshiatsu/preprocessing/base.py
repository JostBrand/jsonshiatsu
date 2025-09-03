"""
Base classes for preprocessing steps.

This module contains the base classes and interfaces used by preprocessing steps
to ensure they can be properly composed in a pipeline.
"""

from ..utils.config import PreprocessingConfig


class PreprocessingStepBase:
    """Base class for preprocessing steps with common functionality."""

    def should_apply(self, _config: PreprocessingConfig) -> bool:
        """Default implementation - always apply. Override in subclasses."""
        return True

    def process(self, text: str, _config: PreprocessingConfig) -> str:
        """Process the text. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement process()")
