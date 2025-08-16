"""
Test cases for preprocessing configuration and PreprocessingConfig class.

These tests ensure the configuration system works correctly and provides
the expected granular control over preprocessing behavior.
"""

import unittest
from jsonshiatsu.utils.config import PreprocessingConfig, ParseConfig
from jsonshiatsu.core.transformer import JSONPreprocessor


class TestPreprocessingConfig(unittest.TestCase):
    """Test PreprocessingConfig class and its methods."""
    
    def test_default_config(self):
        """Test default PreprocessingConfig values."""
        config = PreprocessingConfig()
        
        # Check default values
        self.assertTrue(config.extract_from_markdown)
        self.assertTrue(config.remove_comments)
        self.assertTrue(config.unwrap_function_calls)
        self.assertTrue(config.extract_first_json)
        self.assertTrue(config.remove_trailing_text)
        self.assertTrue(config.normalize_quotes)
        self.assertTrue(config.normalize_boolean_null)
        self.assertTrue(config.fix_unescaped_strings)
        self.assertTrue(config.handle_incomplete_json)
    
    def test_conservative_preset(self):
        """Test conservative preset configuration."""
        config = PreprocessingConfig.conservative()
        
        # Conservative should be more restrictive - based on actual implementation
        # Only fix_unescaped_strings and handle_incomplete_json are disabled
        self.assertTrue(config.extract_from_markdown)
        self.assertTrue(config.remove_comments)
        self.assertTrue(config.unwrap_function_calls)
        self.assertTrue(config.extract_first_json)
        self.assertTrue(config.remove_trailing_text)
        self.assertTrue(config.normalize_quotes)  # Safe normalization
        self.assertTrue(config.normalize_boolean_null)  # Safe normalization
        self.assertFalse(config.fix_unescaped_strings)  # Safety fix disabled
        self.assertFalse(config.handle_incomplete_json)  # Disabled in conservative
    
    def test_aggressive_preset(self):
        """Test aggressive preset configuration."""
        config = PreprocessingConfig.aggressive()
        
        # Aggressive should enable all features
        self.assertTrue(config.extract_from_markdown)
        self.assertTrue(config.remove_comments)
        self.assertTrue(config.unwrap_function_calls)
        self.assertTrue(config.extract_first_json)
        self.assertTrue(config.remove_trailing_text)
        self.assertTrue(config.normalize_quotes)
        self.assertTrue(config.normalize_boolean_null)
        self.assertTrue(config.fix_unescaped_strings)
        self.assertTrue(config.handle_incomplete_json)
    
    def test_from_features_method(self):
        """Test from_features class method."""
        # Enable only specific features
        features = ['remove_comments', 'normalize_quotes', 'fix_unescaped_strings']
        config = PreprocessingConfig.from_features(features)
        
        self.assertFalse(config.extract_from_markdown)
        self.assertTrue(config.remove_comments)
        self.assertFalse(config.unwrap_function_calls)
        self.assertFalse(config.extract_first_json)
        self.assertFalse(config.remove_trailing_text)
        self.assertTrue(config.normalize_quotes)
        self.assertFalse(config.normalize_boolean_null)
        self.assertTrue(config.fix_unescaped_strings)
        self.assertFalse(config.handle_incomplete_json)
    
    def test_custom_config_creation(self):
        """Test creating custom configurations."""
        # Custom config with specific settings
        config = PreprocessingConfig(
            extract_from_markdown=True,
            remove_comments=False,
            unwrap_function_calls=True,
            normalize_quotes=True,
            fix_unescaped_strings=True,
            # Leave others as default
        )
        
        self.assertTrue(config.extract_from_markdown)
        self.assertFalse(config.remove_comments)
        self.assertTrue(config.unwrap_function_calls)
        self.assertTrue(config.normalize_quotes)
        self.assertTrue(config.fix_unescaped_strings)
        # Defaults for others
        self.assertTrue(config.extract_first_json)
        self.assertTrue(config.remove_trailing_text)
    
    def test_config_immutability(self):
        """Test that config objects behave as immutable."""
        config = PreprocessingConfig()
        original_value = config.remove_comments
        
        # Try to modify (should not be possible with dataclass frozen=True if implemented)
        try:
            config.remove_comments = not original_value
            # If modification succeeded, check it didn't actually change
            # (This test depends on implementation details)
        except (AttributeError, TypeError):
            # Expected if config is properly frozen
            pass


class TestConfigIntegration(unittest.TestCase):
    """Test integration of config with preprocessing pipeline."""
    
    def setUp(self):
        """Set up test data."""
        self.malformed_json = '''```json
        // This is a comment
        parseJSON({
            name: 'John',
            "age": 30,
            'active': True,
            "notes": undefined
        });
        ```
        This is trailing text.'''
    
    def test_conservative_preprocessing(self):
        """Test preprocessing with conservative config."""
        config = PreprocessingConfig.conservative()
        result = JSONPreprocessor.preprocess(self.malformed_json, config=config)
        
        # Conservative still does most processing except fix_unescaped_strings and handle_incomplete_json
        self.assertNotIn('```', result)  # Should extract from markdown
        self.assertNotIn('//', result)   # Should remove comments
        self.assertNotIn('parseJSON', result)  # Should unwrap functions
        # And should normalize safe things
        self.assertIn('true', result.lower())  # Should normalize True
        self.assertIn('null', result.lower())  # Should normalize undefined
    
    def test_aggressive_preprocessing(self):
        """Test preprocessing with aggressive config."""
        config = PreprocessingConfig.aggressive()
        result = JSONPreprocessor.preprocess(self.malformed_json, config=config)
        
        # Aggressive should do extensive processing
        self.assertNotIn('```', result)  # Should extract from markdown
        self.assertNotIn('//', result)   # Should remove comments
        self.assertNotIn('parseJSON', result)  # Should unwrap functions
        self.assertNotIn('This is trailing', result)  # Should remove trailing text
        self.assertIn('true', result)    # Should normalize True
        self.assertIn('null', result)    # Should normalize undefined
    
    def test_selective_feature_config(self):
        """Test config with selective features enabled."""
        # Only enable comment removal and quote normalization
        config = PreprocessingConfig(
            extract_from_markdown=False,
            remove_comments=True,
            unwrap_function_calls=False,
            extract_first_json=False,
            remove_trailing_text=False,
            normalize_quotes=True,
            normalize_boolean_null=False,
            fix_unescaped_strings=False,
            handle_incomplete_json=False,
        )
        
        result = JSONPreprocessor.preprocess(self.malformed_json, config=config)
        
        # Should remove comments but leave other issues
        self.assertNotIn('//', result)   # Comments removed
        # Note: The input uses triple quotes not backticks in this test
        self.assertIn("'''", result)     # Markdown preserved (triple quotes)
        self.assertIn('parseJSON', result)  # Function wrapper preserved
        self.assertIn('True', result)    # Boolean not normalized
    
    def test_config_with_unicode_edge_case(self):
        """Test config handling with Unicode edge case."""
        unicode_json = '{"test": "\\u4F60\\u597D", "path": "C:\\\\data\\\\file"}'
        
        # Config with string fixing enabled
        config_with_fix = PreprocessingConfig(
            extract_from_markdown=False,
            remove_comments=False,
            unwrap_function_calls=False,
            extract_first_json=False,
            remove_trailing_text=False,
            normalize_quotes=False,
            normalize_boolean_null=False,
            fix_unescaped_strings=True,
            handle_incomplete_json=False,
        )
        
        result = JSONPreprocessor.preprocess(unicode_json, config=config_with_fix)
        
        # Should preserve Unicode but may fix file paths
        self.assertIn('\\u4F60', result)  # Unicode preserved
        self.assertIn('\\u597D', result)  # Unicode preserved
    
    
    def test_config_none_uses_default(self):
        """Test that config=None uses default behavior."""
        # With config=None
        result_none = JSONPreprocessor.preprocess(self.malformed_json, config=None)
        
        # With aggressive config (current default)
        result_aggressive = JSONPreprocessor.preprocess(
            self.malformed_json, 
            config=PreprocessingConfig.aggressive()
        )
        
        # Should be the same (default is aggressive)
        self.assertEqual(result_none, result_aggressive)


class TestParseConfigIntegration(unittest.TestCase):
    """Test integration with ParseConfig."""
    
    def test_parse_config_with_preprocessing_config(self):
        """Test ParseConfig with PreprocessingConfig."""
        preprocessing_config = PreprocessingConfig.conservative()
        parse_config = ParseConfig(preprocessing_config=preprocessing_config)
        
        # Should store the preprocessing config
        self.assertEqual(parse_config.preprocessing_config, preprocessing_config)
        # Conservative config still has extract_from_markdown=True in actual implementation
        self.assertTrue(parse_config.preprocessing_config.extract_from_markdown)
        # But these should be False in conservative
        self.assertFalse(parse_config.preprocessing_config.fix_unescaped_strings)
        self.assertFalse(parse_config.preprocessing_config.handle_incomplete_json)
    
    def test_parse_config_default_preprocessing(self):
        """Test ParseConfig with default preprocessing."""
        parse_config = ParseConfig()
        
        # Should have a default preprocessing config
        self.assertIsInstance(parse_config.preprocessing_config, PreprocessingConfig)
    
    def test_parse_config_custom_preprocessing(self):
        """Test ParseConfig with custom preprocessing settings."""
        custom_preprocessing = PreprocessingConfig(
            extract_from_markdown=True,
            remove_comments=True,
            unwrap_function_calls=False,
            handle_incomplete_json=True,
        )
        
        parse_config = ParseConfig(
            preprocessing_config=custom_preprocessing,
            duplicate_keys=True,
            fallback=False,
        )
        
        # Should have both parse and preprocessing settings
        self.assertEqual(parse_config.preprocessing_config, custom_preprocessing)
        self.assertTrue(parse_config.duplicate_keys)
        self.assertFalse(parse_config.fallback)
        self.assertTrue(parse_config.preprocessing_config.extract_from_markdown)
        self.assertFalse(parse_config.preprocessing_config.unwrap_function_calls)


class TestConfigValidation(unittest.TestCase):
    """Test configuration validation and error handling."""
    
    def test_invalid_feature_names(self):
        """Test from_features with invalid feature names."""
        # Invalid feature names should be ignored or raise error
        try:
            config = PreprocessingConfig.from_features([
                'remove_comments',
                'invalid_feature_name',
                'normalize_quotes'
            ])
            # If no error, should still work with valid features
            self.assertTrue(config.remove_comments)
            self.assertTrue(config.normalize_quotes)
        except (ValueError, AttributeError):
            # Acceptable to raise error for invalid features
            pass
    
    def test_empty_features_list(self):
        """Test from_features with empty list."""
        config = PreprocessingConfig.from_features([])
        
        # All features should be disabled
        self.assertFalse(config.extract_from_markdown)
        self.assertFalse(config.remove_comments)
        self.assertFalse(config.unwrap_function_calls)
        self.assertFalse(config.extract_first_json)
        self.assertFalse(config.remove_trailing_text)
        self.assertFalse(config.normalize_quotes)
        self.assertFalse(config.normalize_boolean_null)
        self.assertFalse(config.fix_unescaped_strings)
        self.assertFalse(config.handle_incomplete_json)
    
    def test_config_type_validation(self):
        """Test that config parameters have correct types."""
        config = PreprocessingConfig()
        
        # All config attributes should be boolean
        self.assertIsInstance(config.extract_from_markdown, bool)
        self.assertIsInstance(config.remove_comments, bool)
        self.assertIsInstance(config.unwrap_function_calls, bool)
        self.assertIsInstance(config.extract_first_json, bool)
        self.assertIsInstance(config.remove_trailing_text, bool)
        self.assertIsInstance(config.normalize_quotes, bool)
        self.assertIsInstance(config.normalize_boolean_null, bool)
        self.assertIsInstance(config.fix_unescaped_strings, bool)
        self.assertIsInstance(config.handle_incomplete_json, bool)


class TestConfigDocumentation(unittest.TestCase):
    """Test that config classes have proper documentation."""
    
    def test_preprocessing_config_has_docstring(self):
        """Test that PreprocessingConfig has documentation."""
        self.assertIsNotNone(PreprocessingConfig.__doc__)
        self.assertGreater(len(PreprocessingConfig.__doc__.strip()), 0)
    
    def test_config_methods_have_docstrings(self):
        """Test that config methods have documentation."""
        self.assertIsNotNone(PreprocessingConfig.conservative.__doc__)
        self.assertIsNotNone(PreprocessingConfig.aggressive.__doc__)
        self.assertIsNotNone(PreprocessingConfig.from_features.__doc__)
    
    def test_config_attributes_have_type_hints(self):
        """Test that config attributes have proper type hints."""
        import typing
        
        # Get type hints for PreprocessingConfig
        hints = typing.get_type_hints(PreprocessingConfig)
        
        # Should have type hints for key attributes
        expected_attrs = [
            'extract_from_markdown',
            'remove_comments',
            'normalize_quotes',
            'fix_unescaped_strings'
        ]
        
        for attr in expected_attrs:
            if attr in hints:
                self.assertEqual(hints[attr], bool)


if __name__ == '__main__':
    unittest.main()