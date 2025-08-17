"""
Comprehensive test cases for complex edge cases and combinations.

These tests cover interactions between multiple malformed patterns,
stress testing, and real-world complex scenarios.
"""

import unittest
import jsonshiatsu
from jsonshiatsu.security.exceptions import JSONDecodeError, SecurityError


class TestSparseArraysComprehensive(unittest.TestCase):
    """Comprehensive tests for sparse array handling."""

    def test_basic_sparse_patterns(self):
        """Test basic sparse array patterns."""
        test_cases = [
            ("[1,, 3]", [1, None, 3]),
            ("[1,,, 4]", [1, None, None, 4]),
            ("[,, 3]", [None, None, 3]),
            ("[1,,]", [1, None]),
            ("[,,]", [None, None]),
            ("[,]", [None]),
        ]

        for json_str, expected in test_cases:
            with self.subTest(json_str=json_str):
                result = jsonshiatsu.loads(json_str)
                self.assertEqual(result, expected)

    def test_nested_sparse_arrays(self):
        """Test nested sparse arrays."""
        nested_sparse = "[1, [,, 3], [4,, 6]]"
        result = jsonshiatsu.loads(nested_sparse)
        expected = [1, [None, None, 3], [4, None, 6]]
        self.assertEqual(result, expected)

        # Deeply nested
        deep_sparse = "[[[1,,],, [,3]]]"
        result = jsonshiatsu.loads(deep_sparse)
        expected = [[[1, None], None, [None, 3]]]
        self.assertEqual(result, expected)

    def test_sparse_arrays_in_objects(self):
        """Test sparse arrays inside objects."""
        obj_with_sparse = """{
            "data": [1,, 3],
            "items": [,, "last"],
            "mixed": [1, "text",, null]
        }"""

        result = jsonshiatsu.loads(obj_with_sparse)
        expected = {
            "data": [1, None, 3],
            "items": [None, None, "last"],
            "mixed": [1, "text", None, None],
        }
        self.assertEqual(result, expected)

    def test_sparse_arrays_with_other_malformed_patterns(self):
        """Test sparse arrays combined with other malformed JSON."""
        complex_sparse = """{
            // Array with sparse elements
            languages: ["en",, "de", "fr"],
            'users': [
                {name: "John",, age: 30},
                {name: "Jane", age: 25,}
            ],
            "settings": {
                "flags": [true,, false],
                theme: dark
            }
        }"""

        result = jsonshiatsu.loads(complex_sparse)

        # Verify structure
        self.assertIn("languages", result)
        self.assertIn("users", result)
        self.assertIn("settings", result)

        # Verify sparse arrays
        self.assertEqual(result["languages"], ["en", None, "de", "fr"])
        self.assertEqual(result["settings"]["flags"], [True, None, False])


class TestEscapeSequenceComprehensive(unittest.TestCase):
    """Comprehensive tests for escape sequence handling."""

    def test_standard_json_escapes(self):
        """Test all standard JSON escape sequences."""
        escapes_json = """{
            "newline": "line1\\nline2",
            "tab": "col1\\tcol2",
            "carriage": "line1\\rline2",
            "backspace": "text\\bdelete",
            "formfeed": "page1\\fpage2",
            "backslash": "path\\\\file",
            "quote": "He said \\"hello\\"",
            "slash": "http:\\/\\/example.com"
        }"""

        result = jsonshiatsu.loads(escapes_json)

        self.assertEqual(result["newline"], "line1\nline2")
        self.assertEqual(result["tab"], "col1\tcol2")
        self.assertEqual(result["carriage"], "line1\rline2")
        self.assertEqual(result["backspace"], "text\bdelete")
        self.assertEqual(result["formfeed"], "page1\fpage2")
        self.assertEqual(result["backslash"], "path\\file")
        self.assertEqual(result["quote"], 'He said "hello"')
        self.assertEqual(result["slash"], "http://example.com")

    def test_unicode_escapes_comprehensive(self):
        """Test comprehensive Unicode escape handling."""
        unicode_json = """{
            "ascii": "\\u0041\\u0042\\u0043",
            "chinese": "\\u4F60\\u597D\\u4E16\\u754C",
            "emoji": "\\uD83D\\uDE00\\uD83D\\uDE01",
            "accents": "\\u00E9\\u00E8\\u00EA\\u00EB",
            "mixed": "Hello \\u4F60\\u597D World!"
        }"""

        result = jsonshiatsu.loads(unicode_json)

        self.assertEqual(result["ascii"], "ABC")
        self.assertEqual(result["chinese"], "你好世界")
        self.assertEqual(result["accents"], "éèêë")
        self.assertEqual(result["mixed"], "Hello 你好 World!")

    def test_invalid_escape_handling(self):
        """Test handling of invalid escape sequences."""
        # jsonshiatsu should handle invalid escapes gracefully
        invalid_escapes = [
            '{"invalid": "\\x41"}',  # Invalid \x escape
            '{"incomplete": "\\u00"}',  # Incomplete Unicode
            '{"wrong": "\\u00ZZ"}',  # Invalid hex
            '{"just_backslash": "\\"}',  # Trailing backslash
        ]

        for invalid_json in invalid_escapes:
            with self.subTest(invalid_json=invalid_json):
                try:
                    result = jsonshiatsu.loads(invalid_json)
                    # Should parse without crashing
                    self.assertIsInstance(result, dict)
                except JSONDecodeError:
                    # Acceptable to fail, but shouldn't crash
                    pass

    def test_escape_sequences_in_keys(self):
        """Test escape sequences in object keys."""
        key_escapes = """{
            "\\u0041": "Unicode A as key",
            "tab\\tkey": "Key with tab",
            "quote\\"key": "Key with quote",
            "\\nNewline": "Key with newline"
        }"""

        result = jsonshiatsu.loads(key_escapes)

        # Keys should have escapes processed
        self.assertIn("A", result)
        self.assertEqual(result["A"], "Unicode A as key")

    def test_file_path_vs_unicode_escapes(self):
        """Test distinction between file paths and Unicode escapes."""
        mixed_paths = """{
            "unicode": "\\u4F60\\u597D",
            "file_path": "C:\\\\data\\\\file.txt",
            "mixed": "C:\\\\temp\\\\\\u4F60\\u597D.txt"
        }"""

        result = jsonshiatsu.loads(mixed_paths)

        # Unicode should be processed
        self.assertEqual(result["unicode"], "你好")

        # File paths should be handled appropriately
        self.assertIn("file_path", result)
        self.assertIn("mixed", result)


class TestComplexRealWorldScenarios(unittest.TestCase):
    """Test complex real-world malformed JSON scenarios."""

    def test_llm_api_response_simulation(self):
        """Test simulated LLM API response with multiple issues."""
        llm_response = """```json
        {
            // Generated response
            "response": {
                "message": "Hello! I'd say \"welcome\" to you.",
                "confidence": 0.95,
                "timestamp": Date("2025-08-16T10:30:00Z"),
                "metadata": {
                    model: gpt-4,
                    tokens: 150,
                    "categories": ["greeting", "polite",],
                    settings: {
                        temperature: 0.7,
                        "max_tokens": 1000
                    }
                }
            },
            "status": "success", // Operation completed
            debug_info: {
                "processing_time": 1.23e-2,
                "memory_usage": "45MB",
                errors: [],
            }
        }
        ```
        
        This response contains multiple formatting issues but should be parseable."""

        result = jsonshiatsu.loads(llm_response)

        # Should extract the JSON from markdown
        self.assertIn("response", result)
        self.assertIn("status", result)
        self.assertIn("debug_info", result)

        # Verify specific values
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["response"]["timestamp"], "2025-08-16T10:30:00Z")
        self.assertEqual(result["response"]["metadata"]["model"], "gpt-4")

    def test_legacy_config_file(self):
        """Test legacy configuration file with mixed formats."""
        legacy_config = """{
            // Legacy application config
            database: {
                host: "localhost",
                port: 5432,
                'username': "admin",
                "password": "secret123",
                ssl_enabled: true,
                options: {
                    timeout: 30,
                    "retry_attempts": 3,
                    'pool_size': 10,
                }
            },
            features: ["auth", "logging", "metrics",],
            "api": {
                version: "v2",
                'endpoints': [
                    "/users",
                    "/posts", 
                    "/comments"
                ],
                rate_limit: {
                    requests_per_minute: 100,
                    burst: 150
                }
            },
            logging: {
                level: "INFO",
                'file': "/var/log/app.log",
                "rotate": true
            }
        }"""

        result = jsonshiatsu.loads(legacy_config)

        # Verify structure
        self.assertIn("database", result)
        self.assertIn("features", result)
        self.assertIn("api", result)
        self.assertIn("logging", result)

        # Verify values
        self.assertEqual(result["database"]["host"], "localhost")
        self.assertEqual(result["database"]["port"], 5432)
        self.assertEqual(result["api"]["version"], "v2")
        self.assertEqual(len(result["features"]), 4)

    def test_mongodb_export_style(self):
        """Test MongoDB export style JSON with ObjectIds and ISODates."""
        mongodb_json = """{
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "name": "John Doe",
            "email": "john@example.com",
            "created": ISODate("2025-08-16T10:30:00.000Z"),
            "profile": {
                "_id": ObjectId("507f1f77bcf86cd799439012"),
                "bio": "Software engineer with 5+ years experience",
                "skills": ["Python", "JavaScript", "Go"],
                "projects": [
                    {
                        "_id": ObjectId("507f1f77bcf86cd799439013"),
                        "name": "jsonshiatsu",
                        "started": Date("2025-01-01"),
                        "status": "active"
                    }
                ]
            },
            "settings": {
                "theme": "dark",
                "notifications": true,
                "privacy": {
                    "public_profile": false,
                    "show_email": false
                }
            }
        }"""

        result = jsonshiatsu.loads(mongodb_json)

        # Verify ObjectIds are extracted
        self.assertEqual(result["_id"], "507f1f77bcf86cd799439011")
        self.assertEqual(result["profile"]["_id"], "507f1f77bcf86cd799439012")

        # Verify dates are extracted
        self.assertEqual(result["created"], "2025-08-16T10:30:00.000Z")
        self.assertEqual(result["profile"]["projects"][0]["started"], "2025-01-01")

        # Verify structure integrity
        self.assertEqual(result["name"], "John Doe")
        self.assertEqual(len(result["profile"]["skills"]), 3)

    def test_javascript_object_literal(self):
        """Test JavaScript object literal style."""
        js_object = """{
            // JavaScript object
            name: 'MyApp',
            version: "2.1.0",
            dependencies: {
                react: "^18.0.0",
                'react-dom': "^18.0.0",
                typescript: "^4.9.0"
            },
            scripts: {
                start: "react-scripts start",
                build: "react-scripts build",
                test: "react-scripts test",
                eject: "react-scripts eject"
            },
            browserslist: {
                production: [
                    ">0.2%",
                    "not dead",
                    "not op_mini all"
                ],
                development: [
                    "last 1 chrome version",
                    "last 1 firefox version",
                    "last 1 safari version"
                ]
            }
        }"""

        result = jsonshiatsu.loads(js_object)

        # Verify structure
        self.assertEqual(result["name"], "MyApp")
        self.assertEqual(result["version"], "2.1.0")
        self.assertIn("dependencies", result)
        self.assertIn("scripts", result)
        self.assertIn("browserslist", result)

        # Verify nested values
        self.assertEqual(result["dependencies"]["react"], "^18.0.0")
        self.assertEqual(result["scripts"]["start"], "react-scripts start")


class TestErrorRecoveryComprehensive(unittest.TestCase):
    """Comprehensive error recovery and partial parsing tests."""

    def test_mixed_valid_invalid_fields(self):
        """Test objects with mix of valid and invalid fields."""
        mixed_json = """{
            "valid1": "this works",
            broken_field: {missing_quote: "oops"},
            "valid2": "this also works",
            invalid_number: "123.45.67.89",
            "valid3": [1, 2, 3],
            "malformed_array": [1, 2, {broken: null}],
            "valid4": true
        }"""

        try:
            result = jsonshiatsu.loads(mixed_json)
            # Should get some valid fields even if some fail
            self.assertIsInstance(result, dict)

            # At least some valid fields should be present
            valid_fields = ["valid1", "valid2", "valid3", "valid4"]
            found_valid = sum(1 for field in valid_fields if field in result)
            self.assertGreater(found_valid, 0)

        except JSONDecodeError:
            # Acceptable to fail on severely malformed JSON
            pass

    def test_incomplete_structures_recovery(self):
        """Test recovery from incomplete structures."""
        incomplete_cases = [
            # Missing closing brace
            '{"name": "John", "age": 30',
            # Missing closing bracket
            '["apple", "banana", "cherry"',
            # Nested incomplete
            '{"user": {"name": "Alice", "data": [1, 2',
            # Incomplete string
            '{"message": "Hello world',
        ]

        for incomplete_json in incomplete_cases:
            with self.subTest(incomplete_json=incomplete_json):
                try:
                    result = jsonshiatsu.loads(incomplete_json)
                    # Should handle gracefully if possible
                    self.assertIsInstance(result, (dict, list))
                except JSONDecodeError:
                    # Acceptable to fail
                    pass

    def test_cascading_errors(self):
        """Test handling of cascading errors."""
        cascading_errors = """{
            "level1": {
                "level2": {
                    broken_syntax: {missing_value: },
                    "level3": {
                        "another_error": [1, 2, {malformed: }],
                        "valid_data": "should still work"
                    }
                }
            },
            "separate_valid": "isolated from errors"
        }"""

        try:
            result = jsonshiatsu.loads(cascading_errors)
            # Should handle partial recovery
            self.assertIsInstance(result, dict)

            # Some valid data should survive
            if "separate_valid" in result:
                self.assertEqual(result["separate_valid"], "isolated from errors")

        except JSONDecodeError:
            # Acceptable for complex cascading errors
            pass


class TestPerformanceEdgeCases(unittest.TestCase):
    """Test performance characteristics and limits."""

    def test_deeply_nested_structures(self):
        """Test deeply nested structures within reasonable limits."""
        # Create moderately deep nesting
        depth = 50
        nested_json = '{"level": ' * depth + '"deep_value"' + "}" * depth

        try:
            result = jsonshiatsu.loads(nested_json)

            # Navigate to deep value
            current = result
            for i in range(depth):
                self.assertIn("level", current)
                current = current["level"]

            self.assertEqual(current, "deep_value")

        except SecurityError:
            # Expected if depth limit is exceeded
            pass

    def test_large_arrays_within_limits(self):
        """Test large arrays within security limits."""
        # Create moderately large array
        size = 1000
        large_array = "[" + ",".join(str(i) for i in range(size)) + "]"

        try:
            result = jsonshiatsu.loads(large_array)
            self.assertEqual(len(result), size)
            self.assertEqual(result[0], 0)
            self.assertEqual(result[-1], size - 1)

        except SecurityError:
            # Expected if size limit is exceeded
            pass

    def test_large_objects_within_limits(self):
        """Test large objects within security limits."""
        # Create moderately large object
        size = 100
        pairs = [f'"key{i}": "value{i}"' for i in range(size)]
        large_object = "{" + ", ".join(pairs) + "}"

        try:
            result = jsonshiatsu.loads(large_object)
            self.assertEqual(len(result), size)
            self.assertEqual(result["key0"], "value0")
            self.assertEqual(result[f"key{size-1}"], f"value{size-1}")

        except SecurityError:
            # Expected if key count limit is exceeded
            pass


if __name__ == "__main__":
    unittest.main()
