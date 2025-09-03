"""
JSON preprocessing module.

This module provides a modular preprocessing pipeline for cleaning and normalizing
malformed JSON text before parsing. The preprocessing is broken down into focused,
single-responsibility components that can be composed into a pipeline.
"""

from .base import PreprocessingStepBase
from .extractors import ContentExtractor, MarkdownExtractor
from .handlers import CommentHandler, JavaScriptHandler
from .normalizers import QuoteNormalizer, WhitespaceNormalizer
from .pipeline import PreprocessingPipeline
from .repairers import StringRepairer, StructureFixer

__all__ = [
    "PreprocessingPipeline",
    "PreprocessingStepBase",
    "MarkdownExtractor",
    "ContentExtractor",
    "QuoteNormalizer",
    "WhitespaceNormalizer",
    "StructureFixer",
    "StringRepairer",
    "CommentHandler",
    "JavaScriptHandler",
]
