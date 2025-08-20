"""
Test cases for production JSON parsing scenarios.

These tests cover real-world malformed JSON patterns found in production
environments, including string concatenation, escaping issues, and
mixed quote patterns.
"""

import json
import unittest

import jsonshiatsu


class TestStringConcatenation(unittest.TestCase):
    """Test string concatenation patterns."""

    def test_plus_operator_concatenation(self) -> None:
        """Test JavaScript-style + operator concatenation."""
        test_json = '{"message": "Hello " + "world"}'

        # Standard JSON should fail
        with self.assertRaises(json.JSONDecodeError):
            json.loads(test_json)

        # jsonshiatsu should handle it
        result = jsonshiatsu.loads(test_json)
        self.assertEqual(result["message"], "Hello world")

    def test_multiple_concatenation(self) -> None:
        """Test multiple string concatenation."""
        test_json = '{"text": "Part1" + "Part2" + "Part3"}'

        result = jsonshiatsu.loads(test_json)
        self.assertEqual(result["text"], "Part1Part2Part3")

    def test_concatenation_with_newlines(self) -> None:
        """Test concatenation with line breaks."""
        test_json = """{
  "reason": "Line 1" +
            "Line 2" +
            "Line 3"
}"""

        result = jsonshiatsu.loads(test_json)
        self.assertEqual(result["reason"], "Line 1Line 2Line 3")

    def test_python_style_concatenation(self) -> None:
        """Test Python-style parentheses concatenation."""
        test_json = '{"text": ("Hello" "world")}'

        result = jsonshiatsu.loads(test_json)
        self.assertEqual(result["text"], "Helloworld")

    def test_adjacent_string_concatenation(self) -> None:
        """Test implicit adjacent string concatenation."""
        test_json = '{"text": "Hello" "world"}'

        result = jsonshiatsu.loads(test_json)
        self.assertEqual(result["text"], "Helloworld")


class TestEscapingIssues(unittest.TestCase):
    """Test escaping and quote handling."""

    def test_double_backslash_newlines(self) -> None:
        """Test double backslash newline patterns."""
        test_json = r'{"text": "Line 1\\nLine 2"}'

        result = jsonshiatsu.loads(test_json)
        # Should be interpreted as literal \n, not actual newline
        self.assertEqual(result["text"], "Line 1\nLine 2")

    def test_mixed_quotes(self) -> None:
        """Test mixed single and double quotes."""
        test_json = """{"key": 'single quoted value'}"""

        result = jsonshiatsu.loads(test_json)
        self.assertEqual(result["key"], "single quoted value")

    def test_unescaped_quotes_in_strings(self) -> None:
        """Test handling of unescaped quotes within strings."""
        test_json = '{"message": "She said "hello" to me"}'

        result = jsonshiatsu.loads(test_json)
        self.assertEqual(result["message"], 'She said "hello" to me')


class TestProductionExamples(unittest.TestCase):
    """Test real production JSON examples."""

    def test_complex_concatenation_example(self) -> None:
        """Test complex string concatenation from production."""
        test_json = """{
  "RelatedTexts": [
    {
      "ID": "OPS-16",
      "Reason":
        "- Directly requires two-factor authentication." +
        "- Specifically mentions restriction of access." +
        "- Uses common terminology such as 'authentication'."
    }
  ]
}"""

        result = jsonshiatsu.loads(test_json)
        self.assertEqual(len(result["RelatedTexts"]), 1)
        self.assertEqual(result["RelatedTexts"][0]["ID"], "OPS-16")
        expected_reason = (
            "- Directly requires two-factor authentication."
            "- Specifically mentions restriction of access."
            "- Uses common terminology such as 'authentication'."
        )
        self.assertEqual(result["RelatedTexts"][0]["Reason"], expected_reason)

    def test_python_style_multiline(self) -> None:
        """Test Python-style multiline strings."""
        test_json = """{
  'RelatedTexts': [
    {
      'ID': 'DEV-02',
      'Reason': (
        "- DEV-02 focuses on development."
        "- This aligns with requirements."
        "- Both center on transparency."
      )
    }
  ]
}"""

        result = jsonshiatsu.loads(test_json)
        self.assertEqual(len(result["RelatedTexts"]), 1)
        self.assertEqual(result["RelatedTexts"][0]["ID"], "DEV-02")
        expected_reason = (
            "- DEV-02 focuses on development."
            "- This aligns with requirements."
            "- Both center on transparency."
        )
        self.assertEqual(result["RelatedTexts"][0]["Reason"], expected_reason)

    def test_single_quotes_throughout(self) -> None:
        """Test JSON with single quotes throughout."""
        test_json = """{
    'RelatedTexts': [
      {
        'ID': 'OPS-18',
        'Reason': 'Simple reason text'
      },
      {
        'ID': 'COS-03',
        'Reason': 'Another reason'
      }
    ]
  }"""

        result = jsonshiatsu.loads(test_json)
        self.assertEqual(len(result["RelatedTexts"]), 2)
        self.assertEqual(result["RelatedTexts"][0]["ID"], "OPS-18")
        self.assertEqual(result["RelatedTexts"][1]["ID"], "COS-03")

    def test_mixed_escaping_patterns(self) -> None:
        """Test mixed escaping patterns within same document."""
        test_json = r"""{
  "items": [
    {
      "path": "C:\\Users\\test\\file.txt",
      "description": "Line 1\nLine 2"
    }
  ]
}"""

        result = jsonshiatsu.loads(test_json)
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["path"], "C:\\Users\\test\\file.txt")
        self.assertEqual(result["items"][0]["description"], "Line 1\nLine 2")


class TestPerformanceAndStability(unittest.TestCase):
    """Test performance and stability with problematic inputs."""

    def test_no_infinite_loops(self) -> None:
        """Ensure no infinite loops on problematic patterns."""
        # These patterns previously caused timeouts
        problematic_patterns = [
            r'{"text": "Line\\n• bullet"}',
            r'{"text": "Mixed\\nand\\\\npatterns"}',
            '{"reason": "Text with \\"nested\\" quotes"}',
        ]

        for pattern in problematic_patterns:
            with self.subTest(pattern=pattern):
                try:
                    result = jsonshiatsu.loads(pattern)
                    self.assertIsInstance(result, dict)
                    self.assertTrue("text" in result or "reason" in result)
                except Exception as e:
                    # Should not timeout or cause infinite loops
                    # Some parsing failures are acceptable
                    self.assertNotIn("timeout", str(e).lower())

    def test_large_concatenation(self) -> None:
        """Test handling of large string concatenations."""
        # Create a large concatenation
        parts = [f'"Part{i}"' for i in range(50)]
        concatenation = " + ".join(parts)
        test_json = f'{{"large_text": {concatenation}}}'

        result = jsonshiatsu.loads(test_json)
        expected = "".join(f"Part{i}" for i in range(50))
        self.assertEqual(result["large_text"], expected)

    def test_nested_structures_with_concatenation(self) -> None:
        """Test concatenation within nested JSON structures."""
        test_json = """{
  "level1": {
    "level2": {
      "concatenated": "Start " + "middle " + "end",
      "array": [
        {"text": "Item " + "one"},
        {"text": "Item " + "two"}
      ]
    }
  }
}"""

        result = jsonshiatsu.loads(test_json)
        self.assertEqual(result["level1"]["level2"]["concatenated"], "Start middle end")
        self.assertEqual(result["level1"]["level2"]["array"][0]["text"], "Item one")
        self.assertEqual(result["level1"]["level2"]["array"][1]["text"], "Item two")


if __name__ == "__main__":
    unittest.main()
