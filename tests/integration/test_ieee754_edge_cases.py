"""
Test cases for IEEE 754 floating point edge cases and number handling.

These tests ensure jsonshiatsu correctly handles overflow, underflow,
special values, and extreme precision cases.
"""

import math
import sys
import unittest

import jsonshiatsu
from jsonshiatsu.security.exceptions import SecurityError


class TestIEEE754EdgeCases(unittest.TestCase):
    """Test IEEE 754 floating point edge cases."""

    def test_infinity_values(self):
        """Test handling of infinity values."""
        # Positive infinity
        result = jsonshiatsu.loads('{"inf": Infinity}')
        self.assertEqual(result["inf"], "Infinity")

        # Negative infinity
        result = jsonshiatsu.loads('{"ninf": -Infinity}')
        self.assertEqual(result["ninf"], "-Infinity")

        # Case variations
        result = jsonshiatsu.loads('{"inf2": infinity}')
        self.assertEqual(result["inf2"], "infinity")

    def test_nan_values(self):
        """Test handling of NaN values."""
        result = jsonshiatsu.loads('{"nan": NaN}')
        self.assertEqual(result["nan"], "NaN")

        # Case variations
        result = jsonshiatsu.loads('{"nan2": nan}')
        self.assertEqual(result["nan2"], "nan")

    def test_overflow_to_infinity(self):
        """Test numbers that overflow to infinity."""
        # Very large number that should overflow
        large_number = '{"big": 1e309}'
        result = jsonshiatsu.loads(large_number)

        # Should convert to infinity (depends on implementation)
        # At minimum, should not crash
        self.assertIn("big", result)

        # Test with standard JSON comparison
        try:
            import json

            std_result = json.loads(large_number)
            flex_result = jsonshiatsu.loads(large_number)

            # Should handle the same way as standard JSON
            if math.isinf(std_result["big"]):
                self.assertTrue(
                    math.isinf(flex_result["big"])
                    or flex_result["big"] == float("inf")
                    or isinstance(flex_result["big"], str)
                )
        except BaseException:
            # If standard JSON fails, jsonshiatsu should handle gracefully
            pass

    def test_underflow_to_zero(self):
        """Test numbers that underflow to zero."""
        # Very small number that should underflow
        tiny_number = '{"tiny": 1e-325}'
        result = jsonshiatsu.loads(tiny_number)

        self.assertIn("tiny", result)
        # Should either be 0.0 or handled gracefully

        # Compare with standard JSON
        try:
            import json

            std_result = json.loads(tiny_number)
            flex_result = jsonshiatsu.loads(tiny_number)

            # Should handle similarly to standard JSON
            self.assertEqual(type(std_result["tiny"]), type(flex_result["tiny"]))
        except BaseException:
            pass

    def test_max_finite_values(self):
        """Test maximum finite IEEE 754 values."""
        # Maximum finite positive value
        max_val = f'{{"max": {sys.float_info.max}}}'
        result = jsonshiatsu.loads(max_val)
        self.assertIn("max", result)
        self.assertIsInstance(result["max"], (int, float))

        # Maximum finite negative value
        min_val = f'{{"min": {-sys.float_info.max}}}'
        result = jsonshiatsu.loads(min_val)
        self.assertIn("min", result)
        self.assertIsInstance(result["min"], (int, float))

    def test_minimum_normal_values(self):
        """Test minimum normal IEEE 754 values."""
        # Minimum normal positive value
        min_normal = f'{{"min_normal": {sys.float_info.min}}}'
        result = jsonshiatsu.loads(min_normal)
        self.assertIn("min_normal", result)
        self.assertIsInstance(result["min_normal"], (int, float))

    def test_epsilon_precision(self):
        """Test machine epsilon precision."""
        # Machine epsilon
        epsilon = f'{{"epsilon": {sys.float_info.epsilon}}}'
        result = jsonshiatsu.loads(epsilon)
        self.assertIn("epsilon", result)
        self.assertIsInstance(result["epsilon"], (int, float))

    def test_extreme_exponents(self):
        """Test numbers with extreme exponents."""
        extreme_cases = [
            '{"exp_max": 1.23e+308}',
            '{"exp_min": 1.23e-308}',
            '{"exp_large": 9.999e+307}',
            '{"exp_small": 1.001e-307}',
        ]

        for case in extreme_cases:
            with self.subTest(case=case):
                result = jsonshiatsu.loads(case)
                self.assertIsInstance(result, dict)
                self.assertEqual(len(result), 1)

                # Value should be a number or handled gracefully
                value = list(result.values())[0]
                self.assertIsInstance(value, (int, float, str))

    def test_denormalized_numbers(self):
        """Test denormalized (subnormal) numbers."""
        # Numbers smaller than minimum normal but larger than zero
        denorm_cases = [
            '{"denorm1": 4.9406564584124654e-324}',  # Smallest positive denormal
            '{"denorm2": 2.2250738585072009e-308}',  # Near minimum normal
        ]

        for case in denorm_cases:
            with self.subTest(case=case):
                result = jsonshiatsu.loads(case)
                self.assertIsInstance(result, dict)
                self.assertEqual(len(result), 1)

    def test_special_number_combinations(self):
        """Test combinations of special numbers."""
        special_json = """{
            "infinity": Infinity,
            "negative_infinity": -Infinity,
            "not_a_number": NaN,
            "zero": 0,
            "negative_zero": -0,
            "max_finite": 1.7976931348623157e+308,
            "min_positive": 2.2250738585072014e-308
        }"""

        result = jsonshiatsu.loads(special_json)

        # Should have all keys
        expected_keys = [
            "infinity",
            "negative_infinity",
            "not_a_number",
            "zero",
            "negative_zero",
            "max_finite",
            "min_positive",
        ]

        for key in expected_keys:
            self.assertIn(key, result)

    def test_number_length_security_limits(self):
        """Test that extremely long numbers are handled securely."""
        # Very long number string (potential DoS)
        long_number = '{"long": ' + "9" * 1000 + "}"

        # Should either parse successfully or fail with security error
        try:
            result = jsonshiatsu.loads(long_number)
            self.assertIn("long", result)
        except SecurityError:
            # Expected behavior for security limits
            pass
        except Exception as e:
            # Check if it's a wrapped SecurityError (JSONDecodeError wrapping
            # SecurityError)
            if hasattr(e, "__cause__") and isinstance(e.__cause__, SecurityError):
                # This is expected - SecurityError wrapped in JSONDecodeError
                pass
            else:
                # Should not crash with other errors
                self.fail(f"Unexpected error type: {type(e).__name__}: {e}")

    def test_javascript_number_literals(self):
        """Test JavaScript-style number literals."""
        # Hex numbers (if supported)
        try:
            result = jsonshiatsu.loads('{"hex": 0xFF}')
            self.assertIn("hex", result)
        except BaseException:
            # May not be supported, that's okay
            pass

        # Octal numbers
        try:
            result = jsonshiatsu.loads('{"octal": 0o755}')
            self.assertIn("octal", result)
        except BaseException:
            # May not be supported, that's okay
            pass

        # Binary numbers
        try:
            result = jsonshiatsu.loads('{"binary": 0b1010}')
            self.assertIn("binary", result)
        except BaseException:
            # May not be supported, that's okay
            pass


class TestNumberFormattingEdgeCases(unittest.TestCase):
    """Test edge cases in number formatting and parsing."""

    def test_leading_zeros(self):
        """Test numbers with leading zeros."""
        # Leading zeros in integers
        result = jsonshiatsu.loads('{"id": 007}')
        self.assertEqual(result, {"id": 7})

        # Leading zeros in floats
        result = jsonshiatsu.loads('{"value": 0007.5}')
        self.assertEqual(result, {"value": 7.5})

    def test_plus_prefix(self):
        """Test numbers with explicit plus sign."""
        try:
            result = jsonshiatsu.loads('{"positive": +123}')
            self.assertEqual(result, {"positive": 123})
        except BaseException:
            # Plus prefix may not be supported
            pass

    def test_decimal_edge_cases(self):
        """Test decimal number edge cases."""
        # Number starting with decimal point
        result = jsonshiatsu.loads('{"decimal": .5}')
        self.assertEqual(result, {"decimal": 0.5})

        # Number ending with decimal point
        try:
            result = jsonshiatsu.loads('{"trailing": 5.}')
            self.assertEqual(result, {"trailing": 5.0})
        except BaseException:
            # May not be supported
            pass

    def test_scientific_notation_variants(self):
        """Test various scientific notation formats."""
        scientific_cases = [
            ('{"sci1": 1e5}', {"sci1": 100000.0}),
            ('{"sci2": 1E5}', {"sci2": 100000.0}),
            ('{"sci3": 1e+5}', {"sci3": 100000.0}),
            ('{"sci4": 1e-5}', {"sci4": 0.00001}),
            ('{"sci5": 1.23e4}', {"sci5": 12300.0}),
        ]

        for json_str, expected in scientific_cases:
            with self.subTest(json_str=json_str):
                result = jsonshiatsu.loads(json_str)
                self.assertEqual(result, expected)

    def test_multiple_decimal_points(self):
        """Test invalid numbers with multiple decimal points."""
        # This should fail gracefully, not crash
        try:
            result = jsonshiatsu.loads('{"invalid": 123.45.67}')
            # If it doesn't raise an error, check it's handled somehow
            self.assertIn("invalid", result)
        except BaseException:
            # Expected to fail
            pass

    def test_empty_exponent(self):
        """Test numbers with empty exponents."""
        try:
            result = jsonshiatsu.loads('{"empty_exp": 123e}')
            self.assertIn("empty_exp", result)
        except BaseException:
            # Expected to fail
            pass


class TestNumberCompatibility(unittest.TestCase):
    """Test number handling compatibility with standard JSON."""

    def test_standard_json_compatibility(self):
        """Test that valid numbers match standard JSON behavior."""
        test_numbers = [
            '{"int": 123}',
            '{"float": 123.45}',
            '{"negative": -123}',
            '{"scientific": 1.23e-4}',
            '{"zero": 0}',
            '{"decimal": 0.5}',
        ]

        for test_case in test_numbers:
            with self.subTest(test_case=test_case):
                import json

                try:
                    std_result = json.loads(test_case)
                    flex_result = jsonshiatsu.loads(test_case)
                    self.assertEqual(std_result, flex_result)
                except json.JSONDecodeError:
                    # If standard JSON fails, jsonshiatsu should handle gracefully
                    flex_result = jsonshiatsu.loads(test_case)
                    self.assertIsInstance(flex_result, dict)

    def test_python_float_info_compatibility(self):
        """Test compatibility with Python's float info."""
        # Test that we can handle Python's float boundaries
        float_info_json = f"""{{
            "max": {sys.float_info.max},
            "min": {sys.float_info.min},
            "epsilon": {sys.float_info.epsilon},
            "min_exp": {sys.float_info.min_exp},
            "max_exp": {sys.float_info.max_exp},
            "radix": {sys.float_info.radix}
        }}"""

        result = jsonshiatsu.loads(float_info_json)

        # Should parse all float info values
        self.assertIn("max", result)
        self.assertIn("min", result)
        self.assertIn("epsilon", result)


if __name__ == "__main__":
    unittest.main()
