"""
Test cases for JavaScript-style function call patterns in JSON.

These tests cover the recently fixed infinite loop issue and ensure that
function call patterns like Date("2025-08-01") are handled correctly.
"""

import unittest

import jsonshiatsu
from jsonshiatsu.security.exceptions import JSONDecodeError


class TestFunctionCallPatterns(unittest.TestCase):
    """Test handling of JavaScript-style function calls in JSON."""

    def test_date_functions(self):
        """Test Date() function calls."""
        # Basic Date function
        result = jsonshiatsu.loads('{"joined": Date("2025-08-01")}')
        self.assertEqual(result, {"joined": "2025-08-01"})

        # ISO date format
        result = jsonshiatsu.loads('{"created": Date("2025-08-01T10:30:00Z")}')
        self.assertEqual(result, {"created": "2025-08-01T10:30:00Z"})

        # Empty date
        result = jsonshiatsu.loads('{"empty": Date("")}')
        self.assertEqual(result, {"empty": ""})

        # Date in nested structure
        result = jsonshiatsu.loads('{"user": {"lastLogin": Date("2025-08-01")}}')
        expected = {"user": {"lastLogin": "2025-08-01"}}
        self.assertEqual(result, expected)

    def test_isodate_functions(self):
        """Test ISODate() function calls (MongoDB style)."""
        result = jsonshiatsu.loads('{"timestamp": ISODate("2025-08-01T10:30:00.000Z")}')
        self.assertEqual(result, {"timestamp": "2025-08-01T10:30:00.000Z"})

        # ISODate with timezone
        result = jsonshiatsu.loads('{"time": ISODate("2025-08-01T10:30:00+05:00")}')
        self.assertEqual(result, {"time": "2025-08-01T10:30:00+05:00"})

    def test_objectid_functions(self):
        """Test ObjectId() function calls (MongoDB style)."""
        result = jsonshiatsu.loads('{"_id": ObjectId("507f1f77bcf86cd799439011")}')
        self.assertEqual(result, {"_id": "507f1f77bcf86cd799439011"})

        # ObjectId in array
        result = jsonshiatsu.loads(
            '{"ids": [ObjectId("507f1f77bcf86cd799439011"), ObjectId("507f1f77bcf86cd799439012")]}'
        )
        expected = {"ids": ["507f1f77bcf86cd799439011", "507f1f77bcf86cd799439012"]}
        self.assertEqual(result, expected)

    def test_regexp_functions(self):
        """Test RegExp() function calls."""
        result = jsonshiatsu.loads('{"pattern": RegExp("test+")}')
        self.assertEqual(result, {"pattern": "test+"})

        # Complex regex pattern
        result = jsonshiatsu.loads(
            '{"email": RegExp("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\\\.[a-zA-Z]{2,}$")}'
        )
        self.assertEqual(
            result, {"email": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"}
        )

    def test_uuid_functions(self):
        """Test UUID() function calls."""
        result = jsonshiatsu.loads(
            '{"id": UUID("550e8400-e29b-41d4-a716-446655440000")}'
        )
        self.assertEqual(result, {"id": "550e8400-e29b-41d4-a716-446655440000"})

    def test_function_calls_in_arrays(self):
        """Test function calls inside arrays."""
        result = jsonshiatsu.loads('[Date("2025-01-01"), Date("2025-12-31")]')
        self.assertEqual(result, ["2025-01-01", "2025-12-31"])

        # Mixed function calls and regular values
        result = jsonshiatsu.loads(
            '["text", Date("2025-08-01"), 123, ObjectId("507f1f77bcf86cd799439011")]'
        )
        expected = ["text", "2025-08-01", 123, "507f1f77bcf86cd799439011"]
        self.assertEqual(result, expected)

    def test_multiple_function_calls_in_object(self):
        """Test multiple function calls in the same object."""
        json_input = """{
            "created": Date("2025-08-01"),
            "id": ObjectId("507f1f77bcf86cd799439011"),
            "pattern": RegExp("test+"),
            "uuid": UUID("550e8400-e29b-41d4-a716-446655440000")
        }"""

        result = jsonshiatsu.loads(json_input)
        expected = {
            "created": "2025-08-01",
            "id": "507f1f77bcf86cd799439011",
            "pattern": "test+",
            "uuid": "550e8400-e29b-41d4-a716-446655440000",
        }
        self.assertEqual(result, expected)

    def test_function_calls_with_other_malformed_patterns(self):
        """Test function calls combined with other malformed JSON patterns."""
        # Function calls with unquoted keys and comments
        malformed_json = """{
            name: "John Doe",
            joined: Date("2025-08-01"), // registration date
            id: ObjectId("507f1f77bcf86cd799439011"),
            preferences: {
                theme: dark,
                regex: RegExp("test+")
            }
        }"""

        result = jsonshiatsu.loads(malformed_json)
        expected = {
            "name": "John Doe",
            "joined": "2025-08-01",
            "id": "507f1f77bcf86cd799439011",
            "preferences": {"theme": "dark", "regex": "test+"},
        }
        self.assertEqual(result, expected)

    def test_function_calls_without_arguments_fail(self):
        """Test that function calls without parentheses are treated as identifiers."""
        # Function name without parentheses should be treated as identifier
        result = jsonshiatsu.loads('{"test": Date}')
        self.assertEqual(result, {"test": "Date"})

        result = jsonshiatsu.loads('{"test": ObjectId}')
        self.assertEqual(result, {"test": "ObjectId"})

    def test_nested_function_calls(self):
        """Test function calls in deeply nested structures."""
        nested_json = """{
            "users": [
                {
                    "id": ObjectId("507f1f77bcf86cd799439011"),
                    "profile": {
                        "created": Date("2025-01-01"),
                        "settings": {
                            "regex": RegExp("pattern"),
                            "uuid": UUID("550e8400-e29b-41d4-a716-446655440000")
                        }
                    }
                }
            ]
        }"""

        result = jsonshiatsu.loads(nested_json)
        expected = {
            "users": [
                {
                    "id": "507f1f77bcf86cd799439011",
                    "profile": {
                        "created": "2025-01-01",
                        "settings": {
                            "regex": "pattern",
                            "uuid": "550e8400-e29b-41d4-a716-446655440000",
                        },
                    },
                }
            ]
        }
        self.assertEqual(result, expected)

    def test_original_infinite_loop_case(self):
        """Test the original case that caused infinite loops."""
        original_problematic_case = """{
          "users": [
            {
              name: "John Doe",
              'age': 030,
              "email": 'john@example.com',
              "notes": "Hello \\x41 World",
              "settings": {
                theme: dark,
                "joined": Date("2025-08-01"),
                "preferences": {
                  "languages": ["en",, "de"],
                  "vibration": false,
                },
              }
            }
          ],
          "config": {
            "timeout": NaN,
            "apiKey": undefined,
            "regex": /test+/,
            "extra_key": "alpha",
            "extra_key": "beta"
          },
          statistics: {
            total_users: 12345,
            errors: {
              "404": 12,
              "500": 3,
              "timeout": Infinity
            },
            "performance": {
              "avg_response_time": 150.25
              "uptime": "99.9%"
            }
          }
        }"""

        # This should parse successfully without hanging
        result = jsonshiatsu.loads(original_problematic_case)

        # Verify key parts are parsed correctly
        self.assertIn("users", result)
        self.assertIn("config", result)
        self.assertIn("statistics", result)

        # Verify the Date function call was handled
        user_settings = result["users"][0]["settings"]
        self.assertEqual(user_settings["joined"], "2025-08-01")

        # Verify sparse array was handled
        languages = user_settings["preferences"]["languages"]
        self.assertEqual(languages, ["en", None, "de"])


class TestFunctionCallEdgeCases(unittest.TestCase):
    """Test edge cases for function call handling."""

    def test_function_calls_with_special_characters(self):
        """Test function calls with special characters in arguments."""
        # Date with special characters
        result = jsonshiatsu.loads('{"date": Date("2025-08-01T10:30:00.123Z")}')
        self.assertEqual(result, {"date": "2025-08-01T10:30:00.123Z"})

        # RegExp with escaped characters
        result = jsonshiatsu.loads('{"pattern": RegExp("\\\\d+\\\\.\\\\d+")}')
        self.assertEqual(result, {"pattern": "\\d+\\.\\d+"})

    def test_function_calls_with_empty_strings(self):
        """Test function calls with empty string arguments."""
        result = jsonshiatsu.loads('{"empty_date": Date("")}')
        self.assertEqual(result, {"empty_date": ""})

        result = jsonshiatsu.loads('{"empty_pattern": RegExp("")}')
        self.assertEqual(result, {"empty_pattern": ""})

        result = jsonshiatsu.loads('{"empty_id": ObjectId("")}')
        self.assertEqual(result, {"empty_id": ""})


if __name__ == "__main__":
    unittest.main()
