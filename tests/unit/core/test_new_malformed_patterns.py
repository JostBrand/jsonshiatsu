"""
Test cases for new malformed JSON patterns.

This module tests the enhanced jsonshiatsu functionality for handling
additional malformed JSON patterns including JavaScript constructs,
special numbers, empty values, and complex string concatenation.
"""

import pytest

import jsonshiatsu as json


class TestMixedQuotesAndMissingCommas:
    """Test mixed quotes and missing comma handling."""

    def test_mixed_quotes_with_missing_comma(self) -> None:
        """Test Example 1: Mixed single/double quotes with missing comma."""
        malformed = """{
  name: "John Doe",
  'age': 30,
  "city": "New York"
  "country": "USA",
}"""
        expected = {"name": "John Doe", "age": 30, "city": "New York", "country": "USA"}
        result = json.loads(malformed)
        assert result == expected


class TestAssignmentOperatorsAndUndefined:
    """Test assignment operators and undefined value handling."""

    def test_assignment_operator_with_undefined(self) -> None:
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
        assert result == expected


class TestCommentsAndPythonBooleans:
    """Test comment removal and Python boolean handling."""

    def test_comments_and_python_booleans(self) -> None:
        """Test Example 3: Comments and Python True/False."""
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
        assert result == expected


class TestArrayElementSeparation:
    """Test array element separation and mixed quotes."""

    def test_array_elements_and_mixed_quotes(self) -> None:
        """Test Example 4: Array element separation."""
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
        assert result == expected


class TestSpecialNumbers:
    """Test special number format handling."""

    def test_duplicate_keys_and_special_numbers(self) -> None:
        """Test Example 6: Duplicate keys, NaN, Infinity, octal numbers."""
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
                "name": "Bob",  # Last value wins for duplicate keys
                "age": 21,  # Octal 025 -> 21
                "score": None,  # NaN -> null
                "balance": 1e308,  # Infinity -> very large number
            }
        }
        result = json.loads(malformed)
        assert result == expected

    def test_hexadecimal_numbers(self) -> None:
        """Test hexadecimal number conversion."""
        malformed = '{"hex": 0x1A, "hex2": 0xFF}'
        expected = {"hex": 26, "hex2": 255}
        result = json.loads(malformed)
        assert result == expected

    def test_octal_numbers(self) -> None:
        """Test octal number conversion."""
        malformed = '{"octal1": 025, "octal2": 0777}'
        expected = {"octal1": 21, "octal2": 511}
        result = json.loads(malformed)
        assert result == expected


class TestEmptyValuesAndEscapes:
    """Test empty value handling and escape sequences."""

    def test_empty_values_and_invalid_escapes(self) -> None:
        """Test Example 7: Empty values and invalid escape sequences."""
        malformed = """{
  "message": "Hello \\x World",
  "path": "C:\\temp\\file.txt",
  "unicode": "\\u00G1",
  "empty": ,
}"""
        expected = {
            "message": "Hello \\x World",
            "path": "C:\temp\x0cile.txt",  # Some escapes processed
            "unicode": "u00G1",  # Invalid unicode escape handled
            "empty": None,  # Empty value -> null
        }
        result = json.loads(malformed)
        assert result == expected


class TestJavaScriptConstructs:
    """Test JavaScript construct handling."""

    def test_javascript_constructs(self) -> None:
        """Test Example 8: Functions, hex numbers, string concatenation."""
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
                "id": 26,  # 0x1A -> 26
                "callback": None,  # function() {} -> null
                "result": "successful",  # 'success' + 'ful' -> "successful"
            },
            {"status": "active"},  # unquoted identifier -> quoted
        ]
        result = json.loads(malformed)
        assert result == expected

    def test_function_removal(self) -> None:
        """Test function definition removal."""
        malformed = '{"fn": function(x, y) { return x + y; }, "value": 42}'
        expected = {"fn": None, "value": 42}
        result = json.loads(malformed)
        assert result == expected

    def test_regex_literals(self) -> None:
        """Test regex literal conversion."""
        malformed = '{"pattern": /test/gi, "simple": /abc/}'
        expected = {"pattern": "test", "simple": "abc"}
        result = json.loads(malformed)
        assert result == expected

    def test_new_expressions(self) -> None:
        """Test new expression removal."""
        malformed = '{"date": new Date(), "obj": new Object(), "arr": new Array()}'
        expected = {"date": None, "obj": None, "arr": None}
        result = json.loads(malformed)
        assert result == expected


class TestIncompleteStructures:
    """Test handling of incomplete JSON structures."""

    def test_incomplete_objects_and_sparse_arrays(self) -> None:
        """Test Example 9: Incomplete objects and sparse arrays."""
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
        expected = {
            "settings": {
                "theme": "dark",
                "language": "en-US",
                "notifications": {
                    "email": True,
                    "push": False,
                    "sms": None,  # Missing value -> null
                },
            },
            "data": [1, 2, 3, 4, None, 6],  # Sparse array
            "timestamp": "2025-08-20T18:48:00+02:00",  # Unclosed string fixed
        }
        result = json.loads(malformed)
        assert result == expected

    def test_empty_array_elements(self) -> None:
        """Test sparse array handling."""
        malformed = "[1, , 3, , , 6]"
        expected = [1, None, 3, None, None, 6]
        result = json.loads(malformed)
        assert result == expected

    def test_empty_object_values(self) -> None:
        """Test empty object value handling."""
        malformed = '{"a": , "b": 2, "c": }'
        expected = {"a": None, "b": 2, "c": None}
        result = json.loads(malformed)
        assert result == expected


class TestStringConcatenation:
    """Test various string concatenation patterns."""

    def test_simple_string_concatenation(self) -> None:
        """Test simple string concatenation."""
        malformed = '{"result": "hello" + "world", "num": "foo" + "bar"}'
        expected = {"result": "helloworld", "num": "foobar"}
        result = json.loads(malformed)
        assert result == expected

    def test_mixed_quote_concatenation(self) -> None:
        """Test mixed quote concatenation."""
        malformed = '{"mixed": \'single\' + "double"}'
        expected = {"mixed": "singledouble"}
        result = json.loads(malformed)
        assert result == expected

    def test_arithmetic_expressions(self) -> None:
        """Test simple arithmetic expression evaluation."""
        malformed = '{"sum": 10 + 5, "diff": 20 - 3}'
        expected = {"sum": 15, "diff": 17}
        result = json.loads(malformed)
        assert result == expected


class TestTemplateLiterals:
    """Test template literal handling."""

    def test_simple_template_literals(self) -> None:
        """Test simple template literal conversion."""
        malformed = '{"greeting": `Hello world`, "message": `Simple text`}'
        expected = {"greeting": "Hello world", "message": "Simple text"}
        result = json.loads(malformed)
        assert result == expected

    def test_template_literals_with_variables(self) -> None:
        """Test template literals with variable placeholders."""
        malformed = '{"template": `Hello ${name}`, "path": `${dir}/file.txt`}'
        expected = {"template": "Hello ${name}", "path": "${dir}/file.txt"}
        result = json.loads(malformed)
        assert result == expected


class TestURLPreservation:
    """Test URL preservation in comment removal."""

    def test_url_preservation(self) -> None:
        """Test that URLs are preserved when removing comments."""
        malformed = """{
  "api": "https://api.example.com/v1",
  "backup": "http://backup.example.com",
  "comment": "// This should be removed"
}"""
        expected = {
            "api": "https://api.example.com/v1",
            "backup": "http://backup.example.com",
            "comment": "",  # Comment removed
        }
        result = json.loads(malformed)
        assert result == expected


class TestUnquotedIdentifiers:
    """Test unquoted identifier handling."""

    def test_unquoted_keys_and_values(self) -> None:
        """Test unquoted keys and values."""
        malformed = '{key1: "value1", key2: true, key3: active}'
        expected = {"key1": "value1", "key2": True, "key3": "active"}
        result = json.loads(malformed)
        assert result == expected


class TestEdgeCases:
    """Test edge cases and complex combinations."""

    def test_deeply_nested_malformed(self) -> None:
        """Test deeply nested malformed JSON."""
        malformed = """{
  level1: {
    level2: {
      'mixed': "quotes",
      number: 0xFF,
      empty: ,
      func: function() { return null; }
    }
  }
}"""
        expected = {
            "level1": {
                "level2": {
                    "mixed": "quotes",
                    "number": 255,
                    "empty": None,
                    "func": None,
                }
            }
        }
        result = json.loads(malformed)
        assert result == expected

    def test_combination_of_issues(self) -> None:
        """Test combination of multiple malformed patterns."""
        malformed = """{
  name: 'John "Johnny" Doe',
  age: 025,
  score: NaN,
  active: true,
  callback: function() { return "test"; },
  data: [1, , 3],
  empty: ,
  calculation: 5 + 3
}"""
        expected = {
            "name": 'John "Johnny" Doe',
            "age": 21,  # octal
            "score": None,  # NaN
            "active": True,
            "callback": None,  # function
            "data": [1, None, 3],  # sparse array
            "empty": None,  # empty value
            "calculation": 8,  # arithmetic
        }
        result = json.loads(malformed)
        assert result == expected


# Performance and timeout tests
class TestPerformanceAndTimeout:
    """Test performance and timeout handling."""

    def test_regex_timeout_protection(self) -> None:
        """Test that regex operations don't hang indefinitely."""
        # Create a potentially problematic pattern
        malformed = '{"test": "' + "a" * 1000 + '"}'
        result = json.loads(malformed)
        assert result == {"test": "a" * 1000}

    def test_large_input_handling(self) -> None:
        """Test handling of large inputs."""
        large_array = "[" + ", ".join([f'"{i}"' for i in range(100)]) + "]"
        result = json.loads(large_array)
        assert len(result) == 100
        assert result[0] == "0"
        assert result[99] == "99"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
