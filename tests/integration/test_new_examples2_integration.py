"""
Integration tests for the 10 new malformed JSON examples from test_new_examples2.py

These tests verify that jsonshiatsu can handle the specific malformed JSON
patterns provided in the second test file.
"""

import pytest

import jsonshiatsu as json


class TestNewExamples2Integration:
    """Integration tests for the 10 new malformed JSON examples."""

    def test_example_1_mixed_quotes_missing_comma(self) -> None:
        """Test Example 1: Mixed quotes and missing comma."""
        malformed = """{
                name: "John Doe",
                'age': 30,
                "city": "New York"
                "country": "USA",
                }"""
        expected = {"name": "John Doe", "age": 30, "city": "New York", "country": "USA"}
        result = json.loads(malformed)
        assert result == expected, f"Expected {expected}, got {result}"

    def test_example_2_assignment_undefined(self) -> None:
        """Test Example 2: Assignment operators and undefined values."""
        malformed = """{
                "users": [
                    {
                        "id" = 1,
                        "username": "alice",
                        "active": true
                        }
                    {
                        "id": 2,
                        "username": "bob"
                        "active": false,
                        "email": undefined
                        }
                    ]
                }"""
        expected = {
            "users": [
                {"id": 1, "username": "alice", "active": True},
                {"id": 2, "username": "bob", "active": False, "email": None},
            ]
        }
        result = json.loads(malformed)
        assert result == expected, f"Expected {expected}, got {result}"

    def test_example_3_comments_python_booleans(self) -> None:
        """Test Example 3: Comments and Python booleans."""
        malformed = """{
                "product": {
                    "name": "Laptop",
                    "price": 999.99,
                    "specs": {
                        "cpu": "Intel i7"
                        "ram": "16GB",
                        "storage": "512GB SSD"
                        },
                    /* This is a comment */
                    "available": True
                    }
                }"""
        expected = {
            "product": {
                "name": "Laptop",
                "price": 999.99,
                "specs": {"cpu": "Intel i7", "ram": "16GB", "storage": "512GB SSD"},
                "available": True,
            }
        }
        result = json.loads(malformed)
        assert result == expected, f"Expected {expected}, got {result}"

    def test_example_4_array_elements_mixed_quotes(self) -> None:
        """Test Example 4: Array elements and mixed quotes."""
        malformed = """[
                {
                    "timestamp": "2025-08-20T18:32:00",
                    "event": "login",
                    "user_id": 123
                    },
                {
                    temperature: 25.5,
                    "humidity": 60,
                    "location": 'Berlin'
                    },
                {
                    "status": "active",
                    "count": 42,
                    "tags": ["urgent" "important"]
                    },
                ]"""
        expected = [
            {"timestamp": "2025-08-20T18:32:00", "event": "login", "user_id": 123},
            {"temperature": 25.5, "humidity": 60, "location": "Berlin"},
            {"status": "active", "count": 42, "tags": ["urgent", "important"]},
        ]
        result = json.loads(malformed)
        assert result == expected, f"Expected {expected}, got {result}"

    def test_example_5_urls_multiline_strings(self) -> None:
        """Test Example 5: URLs and multiline strings."""
        malformed = """{
                "config": {
                    "debug": true,
                    "timeout": 5000,
                    "endpoints": {
                        "api": "https://api.example.com",
                        "auth": "https://auth.example.com"
                        "backup": "https://backup.example.com"
                        }
                    },
                "features": [
                    "feature1",
                    "feature2",
                    ],
                version: "1.2.3",
                "description": "This is a test
                configuration file"
                }"""
        expected = {
            "config": {
                "debug": True,
                "timeout": 5000,
                "endpoints": {
                    "api": "https://api.example.com",
                    "auth": "https://auth.example.com",
                    "backup": "https://backup.example.com"
                }
            },
            "features": ["feature1", "feature2"],
            "version": "1.2.3",
            "description": "This is a test\nconfiguration file"
        }
        result = json.loads(malformed)
        assert result == expected, f"Expected {expected}, got {result}"

    def test_example_6_special_numbers_duplicates(self) -> None:
        """Test Example 6: Special numbers and duplicate keys."""
        malformed = """{
                "user": {
                    "name": "Alice",
                    "name": "Bob",
                    "age": 025,
                    "score": NaN,
                    "balance": Infinity
                    }
                }"""
        expected = {
            "user": {
                "name": "Bob",  # Last value wins
                "age": 21,  # Octal conversion
                "score": "NaN",  # NaN -> string (JSON-compliant)
                "balance": "Infinity",  # Infinity -> string (JSON-compliant)
            }
        }
        result = json.loads(malformed)
        assert result == expected, f"Expected {expected}, got {result}"

    def test_example_7_invalid_escapes_empty_values(self) -> None:
        """Test Example 7: Invalid escape sequences and empty values."""
        malformed = """{
                "message": "Hello \\x World",
                "path": "C:\\temp\\file.txt",
                "unicode": "\\u00G1",
                "empty": ,
                }"""
        result = json.loads(malformed)

        # Verify structure (exact escape handling may vary)
        assert "message" in result
        assert "path" in result
        assert "unicode" in result
        assert "empty" in result
        assert result["empty"] is None  # Empty value should become null

    def test_example_8_javascript_constructs(self) -> None:
        """Test Example 8: JavaScript constructs."""
        malformed = """[
                {
                    "id": 0x1A,
                    "callback": function() {
                        return true;
                        },
                    "result": 'success' + 'ful',
                    },
                {
                    "status": active,
                    }
                ]"""
        expected = [
            {
                "id": 26,  # Hex conversion
                "callback": None,  # Function -> null
                "result": "successful",  # String concatenation
            },
            {"status": "active"},  # Unquoted identifier
        ]
        result = json.loads(malformed)
        assert result == expected, f"Expected {expected}, got {result}"

    def test_example_9_incomplete_structures(self) -> None:
        """Test Example 9: Incomplete structures and sparse arrays."""
        malformed = """{
                "settings": {
                    "theme": "dark",
                    "language": "en-US",
                    "notifications": {
                        "email": true,
                        "push": false,
                        "sms":
                        },
                    },
                "data": [1, 2, 3, 4, , 6],
                "timestamp": "2025-08-20T18:48:00+02:00,
                }"""
        result = json.loads(malformed)

        # Verify structure
        assert "settings" in result
        assert "data" in result
        assert "timestamp" in result

        # Check specific fixes
        assert result["settings"]["notifications"]["sms"] is None  # Missing value
        assert result["data"] == [1, 2, 3, 4, None, 6]  # Sparse array
        assert isinstance(result["timestamp"], str)  # Unclosed string fixed

    def test_example_10_complex_template_literals(self) -> None:
        """Test Example 10: Complex template literals."""
        malformed = """{
                "mixed": 'single" + "double',
                "regex": /pattern/gi,
                "date": new Date(),
                "calculation": 10 + 5,
                "template": `Hello ${name}`,
                }"""
        expected = {
            "mixed": "singledouble",  # String concatenation
            "regex": "pattern",  # Regex literal -> string
            "date": None,  # Constructor call -> null
            "calculation": 15,  # Arithmetic expression
            "template": "Hello ${name}",  # Template literal preserved as string
        }
        result = json.loads(malformed)
        assert result == expected, f"Expected {expected}, got {result}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
