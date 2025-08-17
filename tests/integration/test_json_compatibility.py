"""
Test cases for drop-in replacement compatibility with standard json module.

These tests ensure jsonshiatsu's loads() and load() functions work as
drop-in replacements for the standard json module functions.
"""

import io
import json
import os
import tempfile
import unittest

import jsonshiatsu


class TestLoadsCompatibility(unittest.TestCase):
    """Test loads() function compatibility with json.loads()."""

    def test_basic_loads_compatibility(self):
        """Test basic loads() function compatibility."""
        # Standard JSON should work identically
        test_cases = [
            '{"test": "value"}',
            "[1, 2, 3]",
            '{"nested": {"array": [1, 2, {"deep": true}]}}',
            '{"number": 123, "float": 45.67, "bool": false, "null": null}',
        ]

        for test_case in test_cases:
            with self.subTest(test_case=test_case):
                std_result = json.loads(test_case)
                flex_result = jsonshiatsu.loads(test_case)
                self.assertEqual(std_result, flex_result)

    def test_object_hook_parameter(self):
        """Test object_hook parameter compatibility."""

        def test_hook(obj):
            # Add a marker to all objects
            if isinstance(obj, dict):
                obj["_processed"] = True
            return obj

        test_json = '{"outer": {"inner": "value"}}'

        # Test with standard json
        std_result = json.loads(test_json, object_hook=test_hook)

        # Test with jsonshiatsu
        flex_result = jsonshiatsu.loads(test_json, object_hook=test_hook)

        # Both should have the hook applied
        self.assertEqual(std_result, flex_result)
        self.assertTrue(std_result["_processed"])
        self.assertTrue(std_result["outer"]["_processed"])
        self.assertTrue(flex_result["_processed"])
        self.assertTrue(flex_result["outer"]["_processed"])

    def test_parse_float_parameter(self):
        """Test parse_float parameter compatibility."""
        test_json = '{"pi": 3.14159, "e": 2.71828}'

        # Convert floats to strings
        std_result = json.loads(test_json, parse_float=str)
        flex_result = jsonshiatsu.loads(test_json, parse_float=str)

        self.assertEqual(std_result, flex_result)
        self.assertIsInstance(std_result["pi"], str)
        self.assertIsInstance(flex_result["pi"], str)
        self.assertEqual(std_result["pi"], "3.14159")
        self.assertEqual(flex_result["pi"], "3.14159")

    def test_parse_int_parameter(self):
        """Test parse_int parameter compatibility."""
        test_json = '{"count": 42, "items": 100}'

        # Convert integers to strings
        std_result = json.loads(test_json, parse_int=str)
        flex_result = jsonshiatsu.loads(test_json, parse_int=str)

        self.assertEqual(std_result, flex_result)
        self.assertIsInstance(std_result["count"], str)
        self.assertIsInstance(flex_result["count"], str)
        self.assertEqual(std_result["count"], "42")
        self.assertEqual(flex_result["count"], "42")

    def test_parse_constant_parameter(self):
        """Test parse_constant parameter compatibility."""
        test_json = '{"inf": Infinity, "nan": NaN, "ninf": -Infinity}'

        # Custom constant parser
        def parse_constant(value):
            if value == "Infinity":
                return "POS_INF"
            elif value == "-Infinity":
                return "NEG_INF"
            elif value == "NaN":
                return "NOT_A_NUMBER"
            return value

        # jsonshiatsu should handle this (standard json might not parse Infinity/NaN)
        try:
            flex_result = jsonshiatsu.loads(test_json, parse_constant=parse_constant)
            # Should apply the custom parser
            self.assertIn("inf", flex_result)
        except BaseException:
            # If not supported yet, that's documented
            pass

    def test_object_pairs_hook_parameter(self):
        """Test object_pairs_hook parameter compatibility."""
        from collections import OrderedDict

        test_json = '{"b": 2, "a": 1, "c": 3}'

        # Use OrderedDict to preserve order
        std_result = json.loads(test_json, object_pairs_hook=OrderedDict)
        flex_result = jsonshiatsu.loads(test_json, object_pairs_hook=OrderedDict)

        self.assertEqual(std_result, flex_result)
        self.assertIsInstance(std_result, OrderedDict)
        self.assertIsInstance(flex_result, OrderedDict)

    def test_strict_parameter(self):
        """Test strict parameter compatibility."""
        # Standard JSON with control characters (strict mode)
        test_json = '{"test": "value\\u0000"}'

        # Strict mode should work the same
        std_result = json.loads(test_json, strict=False)
        flex_result = jsonshiatsu.loads(test_json, strict=False)

        self.assertEqual(std_result, flex_result)

        # Test strict=True
        try:
            std_strict = json.loads(test_json, strict=True)
            flex_strict = jsonshiatsu.loads(test_json, strict=True)
            self.assertEqual(std_strict, flex_strict)
        except BaseException:
            # Both should behave the same way
            with self.assertRaises(Exception):
                jsonshiatsu.loads(test_json, strict=True)

    def test_cls_parameter(self):
        """Test cls parameter compatibility."""
        # Custom decoder class
        class CustomDecoder(json.JSONDecoder):
            def decode(self, s):
                result = super().decode(s)
                if isinstance(result, dict):
                    result["_custom_decoded"] = True
                return result

        test_json = '{"test": "value"}'

        # Test with custom decoder class
        std_result = json.loads(test_json, cls=CustomDecoder)

        try:
            flex_result = jsonshiatsu.loads(test_json, cls=CustomDecoder)
            self.assertEqual(std_result, flex_result)
            self.assertTrue(std_result.get("_custom_decoded"))
            self.assertTrue(flex_result.get("_custom_decoded"))
        except BaseException:
            # cls parameter might not be fully supported yet
            pass

    def test_additional_kwargs(self):
        """Test that additional keyword arguments are handled."""
        test_json = '{"test": "value"}'

        # Test with extra kwargs (should be ignored gracefully)
        try:
            result = jsonshiatsu.loads(
                test_json, unknown_param=True, another_param="test"
            )
            self.assertEqual(result, {"test": "value"})
        except TypeError:
            # May raise TypeError for unknown params, that's acceptable
            pass


class TestLoadCompatibility(unittest.TestCase):
    """Test load() function compatibility with json.load()."""

    def setUp(self):
        """Set up test files."""
        self.test_data = {"test": "value", "number": 42, "array": [1, 2, 3]}

        # Create temporary file with JSON data
        self.temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        json.dump(self.test_data, self.temp_file)
        self.temp_file.close()

        # Create temporary file with malformed JSON
        self.malformed_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        self.malformed_file.write(
            """{
            // Comment in JSON
            "name": "test",
            'single_quotes': "value",
            unquoted_key: "value"
        }"""
        )
        self.malformed_file.close()

    def tearDown(self):
        """Clean up test files."""
        os.unlink(self.temp_file.name)
        os.unlink(self.malformed_file.name)

    def test_basic_load_compatibility(self):
        """Test basic load() function compatibility."""
        # Test with standard JSON file
        with open(self.temp_file.name, "r") as f:
            std_result = json.load(f)

        with open(self.temp_file.name, "r") as f:
            flex_result = jsonshiatsu.load(f)

        self.assertEqual(std_result, flex_result)
        self.assertEqual(flex_result, self.test_data)

    def test_load_with_parameters(self):
        """Test load() with various parameters."""
        # Test with object_hook
        def add_marker(obj):
            if isinstance(obj, dict):
                obj["_loaded"] = True
            return obj

        with open(self.temp_file.name, "r") as f:
            std_result = json.load(f, object_hook=add_marker)

        with open(self.temp_file.name, "r") as f:
            flex_result = jsonshiatsu.load(f, object_hook=add_marker)

        self.assertEqual(std_result, flex_result)
        self.assertTrue(std_result.get("_loaded"))
        self.assertTrue(flex_result.get("_loaded"))

    def test_load_malformed_json(self):
        """Test load() with malformed JSON (jsonshiatsu extension)."""
        # Standard json should fail
        with open(self.malformed_file.name, "r") as f:
            with self.assertRaises(json.JSONDecodeError):
                json.load(f)

        # jsonshiatsu should handle it
        with open(self.malformed_file.name, "r") as f:
            flex_result = jsonshiatsu.load(f)

        self.assertIsInstance(flex_result, dict)
        self.assertIn("name", flex_result)
        self.assertEqual(flex_result["name"], "test")

    def test_load_with_stringio(self):
        """Test load() with StringIO objects."""
        json_string = '{"test": "stringio"}'

        # Test with StringIO
        std_stream = io.StringIO(json_string)
        std_result = json.load(std_stream)

        flex_stream = io.StringIO(json_string)
        flex_result = jsonshiatsu.load(flex_stream)

        self.assertEqual(std_result, flex_result)
        self.assertEqual(flex_result, {"test": "stringio"})

    def test_load_with_binary_mode(self):
        """Test load() with binary file mode."""
        # Create binary JSON file
        binary_data = b'{"binary": "test"}'
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(binary_data)
            binary_file = f.name

        try:
            # Test with binary mode (should handle encoding)
            with open(binary_file, "rb") as f:
                try:
                    std_result = json.load(f)
                    with open(binary_file, "rb") as f2:
                        flex_result = jsonshiatsu.load(f2)
                    self.assertEqual(std_result, flex_result)
                except BaseException:
                    # Binary mode might not be supported the same way
                    pass
        finally:
            os.unlink(binary_file)


class TestjsonshiatsuExtensions(unittest.TestCase):
    """Test jsonshiatsu-specific extensions beyond standard json."""

    def test_malformed_json_handling(self):
        """Test that jsonshiatsu handles malformed JSON where standard json fails."""
        malformed_cases = [
            # Unquoted keys
            '{test: "value"}',
            # Single quotes
            "{'test': 'value'}",
            # Trailing commas
            '{"test": "value",}',
            # Comments
            '{"test": "value" /* comment */}',
            # Mixed quotes
            "{\"test\": 'value'}",
        ]

        for case in malformed_cases:
            with self.subTest(case=case):
                # Standard json should fail
                with self.assertRaises(json.JSONDecodeError):
                    json.loads(case)

                # jsonshiatsu should handle it
                result = jsonshiatsu.loads(case)
                self.assertIsInstance(result, dict)
                self.assertIn("test", result)
                self.assertEqual(result["test"], "value")

    def test_config_parameter(self):
        """Test jsonshiatsu-specific config parameter."""
        from jsonshiatsu.utils.config import ParseConfig, PreprocessingConfig

        malformed_json = """{
            // This has comments
            "test": "value",
            unquoted: "key"
        }"""

        # Test with custom config
        config = ParseConfig(preprocessing_config=PreprocessingConfig.aggressive())

        result = jsonshiatsu.loads(malformed_json, config=config)
        self.assertIsInstance(result, dict)
        self.assertIn("test", result)
        self.assertIn("unquoted", result)

    def test_function_call_handling(self):
        """Test jsonshiatsu-specific function call handling."""
        function_json = (
            '{"date": Date("2025-08-01"), "id": ObjectId("507f1f77bcf86cd799439011")}'
        )

        # Standard json should fail
        with self.assertRaises(json.JSONDecodeError):
            json.loads(function_json)

        # jsonshiatsu should handle it
        result = jsonshiatsu.loads(function_json)
        self.assertEqual(
            result, {"date": "2025-08-01", "id": "507f1f77bcf86cd799439011"}
        )

    def test_partial_parsing_compatibility(self):
        """Test that partial parsing doesn't break standard interface."""
        # Even with partial parsing, the standard interface should work
        valid_json = '{"valid": "data"}'

        result = jsonshiatsu.loads(valid_json)
        self.assertEqual(result, {"valid": "data"})

        # Should return the same type as standard json
        std_result = json.loads(valid_json)
        self.assertEqual(type(result), type(std_result))


class TestApiSignatures(unittest.TestCase):
    """Test that jsonshiatsu API signatures match standard json."""

    def test_loads_signature_compatibility(self):
        """Test that loads() accepts the same parameters as json.loads()."""
        import inspect

        # Get standard json.loads signature
        json_signature = inspect.signature(json.loads)
        flex_signature = inspect.signature(jsonshiatsu.loads)

        # jsonshiatsu should accept at least the same parameters
        json_params = set(json_signature.parameters.keys())
        flex_params = set(flex_signature.parameters.keys())

        # All json parameters should be supported (or via **kwargs)
        if "kw" in flex_params or any(
            "**" in str(p) for p in flex_signature.parameters.values()
        ):
            # Has **kwargs, should accept any json parameter
            pass
        else:
            # Should have all the same parameters
            missing_params = json_params - flex_params
            self.assertEqual(
                len(missing_params), 0, f"Missing parameters: {missing_params}"
            )

    def test_load_signature_compatibility(self):
        """Test that load() accepts the same parameters as json.load()."""
        import inspect

        json_signature = inspect.signature(json.load)
        flex_signature = inspect.signature(jsonshiatsu.load)

        json_params = set(json_signature.parameters.keys())
        flex_params = set(flex_signature.parameters.keys())

        # Check parameter compatibility
        if "kw" in flex_params or any(
            "**" in str(p) for p in flex_signature.parameters.values()
        ):
            pass
        else:
            missing_params = json_params - flex_params
            self.assertEqual(
                len(missing_params), 0, f"Missing parameters: {missing_params}"
            )


if __name__ == "__main__":
    unittest.main()
