"""
Test cases for preprocessing configuration.

Tests focus on ensuring configuration presets work correctly for different use cases.
"""

import unittest

from jsonshiatsu.utils.config import ParseConfig, PreprocessingConfig


class TestConfigurationPresets(unittest.TestCase):
    """Test configuration presets and their behavior."""

    def test_conservative_vs_aggressive_presets(self):
        """Test that conservative and aggressive presets have expected differences."""
        conservative = PreprocessingConfig.conservative()
        aggressive = PreprocessingConfig.aggressive()

        # Conservative should be more restrictive than aggressive
        # Key differences should be in potentially risky features
        self.assertFalse(conservative.fix_unescaped_strings)
        self.assertTrue(aggressive.fix_unescaped_strings)

        self.assertFalse(conservative.handle_incomplete_json)
        self.assertTrue(aggressive.handle_incomplete_json)

        # Both should support safe operations
        self.assertTrue(conservative.remove_comments)
        self.assertTrue(aggressive.remove_comments)

        self.assertTrue(conservative.extract_from_markdown)
        self.assertTrue(aggressive.extract_from_markdown)

    def test_from_features_method(self):
        """Test selective feature enabling."""
        # Enable only specific safe features
        features = ["remove_comments", "extract_from_markdown"]
        config = PreprocessingConfig.from_features(features)

        self.assertTrue(config.remove_comments)
        self.assertTrue(config.extract_from_markdown)
        self.assertFalse(config.fix_unescaped_strings)
        self.assertFalse(config.handle_incomplete_json)

    def test_parse_config_integration(self):
        """Test that ParseConfig properly integrates with PreprocessingConfig."""
        # Test with different preprocessing configurations
        parse_config_conservative = ParseConfig(
            preprocessing_config=PreprocessingConfig.conservative()
        )

        parse_config_aggressive = ParseConfig(
            preprocessing_config=PreprocessingConfig.aggressive()
        )

        # Should maintain the preprocessing config
        self.assertFalse(
            parse_config_conservative.preprocessing_config.fix_unescaped_strings
        )
        self.assertTrue(
            parse_config_aggressive.preprocessing_config.fix_unescaped_strings
        )

    def test_config_attributes_exist(self):
        """Test that all expected configuration attributes exist."""
        config = PreprocessingConfig()

        required_attributes = [
            "extract_from_markdown",
            "remove_comments",
            "normalize_quotes",
            "normalize_boolean_null",
            "fix_unescaped_strings",
            "handle_incomplete_json",
        ]

        for attr in required_attributes:
            self.assertTrue(hasattr(config, attr), f"Missing attribute: {attr}")
            self.assertIsInstance(
                getattr(config, attr), bool, f"Attribute {attr} should be boolean"
            )


if __name__ == "__main__":
    unittest.main()
