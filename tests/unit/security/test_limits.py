"""
Test cases for security limits and validation.

Tests focus on preventing resource exhaustion attacks and validating input constraints.
"""

import unittest
from jsonshiatsu.security.limits import LimitValidator
from jsonshiatsu.security.exceptions import SecurityError
from jsonshiatsu.utils.config import ParseLimits


class TestLimitValidator(unittest.TestCase):
    """Test LimitValidator functionality for security constraints."""
    
    def setUp(self):
        """Set up test validator with custom limits."""
        self.limits = ParseLimits(
            max_input_size=1000,
            max_string_length=50,
            max_number_length=20,
            max_nesting_depth=5,
            max_array_items=10,
            max_object_keys=10
        )
        self.validator = LimitValidator(self.limits)

    def test_input_size_validation_pass(self):
        """Test input size validation within limits."""
        small_text = "x" * 500  # Within limit of 1000
        self.validator.validate_input_size(small_text)  # Should not raise

    def test_input_size_validation_fail(self):
        """Test input size validation exceeding limits."""
        large_text = "x" * 1001  # Exceeds limit of 1000
        with self.assertRaises(SecurityError) as cm:
            self.validator.validate_input_size(large_text)
        
        error = cm.exception
        self.assertIn("Input size 1001 exceeds limit 1000", str(error))

    def test_string_length_validation_pass(self):
        """Test string length validation within limits."""
        short_string = "x" * 30  # Within limit of 50
        self.validator.validate_string_length(short_string)  # Should not raise

    def test_string_length_validation_fail(self):
        """Test string length validation exceeding limits."""
        long_string = "x" * 51  # Exceeds limit of 50
        with self.assertRaises(SecurityError) as cm:
            self.validator.validate_string_length(long_string, "line 5")
        
        error = cm.exception
        self.assertIn("String length 51 exceeds limit 50", str(error))
        self.assertIn("at line 5", str(error))

    def test_string_length_validation_no_position(self):
        """Test string length validation without position info."""
        long_string = "x" * 51
        with self.assertRaises(SecurityError) as cm:
            self.validator.validate_string_length(long_string)
        
        error = cm.exception
        self.assertIn("String length 51 exceeds limit 50", str(error))
        self.assertNotIn(" at ", str(error))

    def test_number_length_validation_pass(self):
        """Test number length validation within limits."""
        short_number = "123.456789"  # Within limit of 20
        self.validator.validate_number_length(short_number)  # Should not raise

    def test_number_length_validation_fail(self):
        """Test number length validation exceeding limits."""
        long_number = "1" * 21  # Exceeds limit of 20
        with self.assertRaises(SecurityError) as cm:
            self.validator.validate_number_length(long_number, "column 15")
        
        error = cm.exception
        self.assertIn("Number length 21 exceeds limit 20", str(error))
        self.assertIn("at column 15", str(error))

    def test_nesting_depth_validation_pass(self):
        """Test nesting depth validation within limits."""
        # Enter structures within the limit (5)
        for i in range(5):
            self.validator.enter_structure()
        
        # Should be at max depth but not over
        self.assertEqual(self.validator.nesting_depth, 5)

    def test_nesting_depth_validation_fail(self):
        """Test nesting depth validation exceeding limits."""
        # Enter 5 structures to reach limit
        for i in range(5):
            self.validator.enter_structure()
        
        # Attempting to enter 6th structure should fail
        with self.assertRaises(SecurityError) as cm:
            self.validator.enter_structure()
        
        error = cm.exception
        self.assertIn("Nesting depth 6 exceeds limit 5", str(error))

    def test_nesting_depth_exit(self):
        """Test exiting nested structures."""
        # Enter and exit structures
        self.validator.enter_structure()
        self.validator.enter_structure()
        self.assertEqual(self.validator.nesting_depth, 2)
        
        self.validator.exit_structure()
        self.assertEqual(self.validator.nesting_depth, 1)
        
        self.validator.exit_structure()
        self.assertEqual(self.validator.nesting_depth, 0)

    def test_array_items_validation_pass(self):
        """Test array items validation within limits."""
        for i in range(10):  # Within limit of 10
            self.validator.validate_array_items(i + 1)

    def test_array_items_validation_fail(self):
        """Test array items validation exceeding limits."""
        with self.assertRaises(SecurityError) as cm:
            self.validator.validate_array_items(11)  # Exceeds limit of 10
        
        error = cm.exception
        self.assertIn("Array item count 11 exceeds limit 10", str(error))

    def test_object_items_validation_pass(self):
        """Test object keys validation within limits."""
        for i in range(10):  # Within limit of 10
            self.validator.validate_object_keys(i + 1)

    def test_object_items_validation_fail(self):
        """Test object keys validation exceeding limits."""
        with self.assertRaises(SecurityError) as cm:
            self.validator.validate_object_keys(11)  # Exceeds limit of 10
        
        error = cm.exception
        self.assertIn("Object key count 11 exceeds limit 10", str(error))

    def test_validator_state_isolation(self):
        """Test that validator state is properly isolated."""
        # Create two validators
        validator1 = LimitValidator(self.limits)
        validator2 = LimitValidator(self.limits)
        
        # Modify one validator's state
        validator1.enter_structure()
        validator1.enter_structure()
        
        # Other validator should be unaffected
        self.assertEqual(validator1.nesting_depth, 2)
        self.assertEqual(validator2.nesting_depth, 0)

    def test_item_counting(self):
        """Test item counting functionality."""
        # Test item counting with count_item method
        self.assertEqual(self.validator.total_items, 0)
        
        # Count some items
        self.validator.count_item()
        self.validator.count_item()
        self.assertEqual(self.validator.total_items, 2)


class TestParseConfigLimits(unittest.TestCase):
    """Test ParseLimits configuration integration."""
    
    def test_default_limits(self):
        """Test default limit values."""
        limits = ParseLimits()
        
        # Verify reasonable defaults exist
        self.assertGreater(limits.max_input_size, 0)
        self.assertGreater(limits.max_string_length, 0)
        self.assertGreater(limits.max_number_length, 0)
        self.assertGreater(limits.max_nesting_depth, 0)
        self.assertGreater(limits.max_array_items, 0)
        self.assertGreater(limits.max_object_keys, 0)

    def test_custom_limits(self):
        """Test custom limit configuration."""
        custom_limits = ParseLimits(
            max_input_size=2000,
            max_string_length=100,
            max_nesting_depth=10
        )
        
        self.assertEqual(custom_limits.max_input_size, 2000)
        self.assertEqual(custom_limits.max_string_length, 100)
        self.assertEqual(custom_limits.max_nesting_depth, 10)

    def test_validator_with_custom_limits(self):
        """Test validator using custom limits."""
        custom_limits = ParseLimits(max_nesting_depth=2)
        validator = LimitValidator(custom_limits)
        
        # Should allow up to 2 levels
        validator.enter_structure()
        validator.enter_structure()
        
        # Third level should fail
        with self.assertRaises(SecurityError):
            validator.enter_structure()


if __name__ == '__main__':
    unittest.main()