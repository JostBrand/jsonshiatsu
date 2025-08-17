"""
Test cases for the jsonshiatsu tokenizer.

Tests focus on tokenization accuracy for malformed JSON patterns.
"""

import unittest
from jsonshiatsu.core.tokenizer import Lexer, TokenType


class TestTokenizerAccuracy(unittest.TestCase):
    """Test tokenizer accuracy for various input patterns."""
    
    def _get_non_eof_tokens(self, text):
        """Helper to get tokens excluding EOF for easier testing."""
        lexer = Lexer(text)
        tokens = lexer.get_all_tokens()
        return [t for t in tokens if t.type != TokenType.EOF]
    
    def test_string_tokenization(self):
        """Test string tokenization with various quote styles."""
        # Basic strings
        tokens = self._get_non_eof_tokens('"hello"')
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, TokenType.STRING)
        self.assertEqual(tokens[0].value, "hello")
        
        # Single quotes (malformed JSON feature)
        tokens = self._get_non_eof_tokens("'world'")
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, TokenType.STRING)
        self.assertEqual(tokens[0].value, "world")
    
    def test_escape_sequence_tokenization(self):
        """Test that escape sequences are properly tokenized."""
        tokens = self._get_non_eof_tokens('"line1\\nline2"')
        self.assertEqual(tokens[0].type, TokenType.STRING)
        self.assertEqual(tokens[0].value, "line1\nline2")
        
        tokens = self._get_non_eof_tokens('"quote: \\"test\\""')
        self.assertEqual(tokens[0].value, 'quote: "test"')
    
    def test_number_tokenization(self):
        """Test number tokenization accuracy."""
        test_cases = [
            ("123", "123"),
            ("-456", "-456"),
            ("78.90", "78.90"),
            ("1.23e-4", "1.23e-4"),
        ]
        
        for input_num, expected_value in test_cases:
            with self.subTest(input_num=input_num):
                tokens = self._get_non_eof_tokens(input_num)
                self.assertEqual(len(tokens), 1)
                self.assertEqual(tokens[0].type, TokenType.NUMBER)
                self.assertEqual(tokens[0].value, expected_value)
    
    def test_identifier_tokenization(self):
        """Test identifier tokenization for unquoted keys/values."""
        tokens = self._get_non_eof_tokens("unquoted_key")
        self.assertEqual(tokens[0].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[0].value, "unquoted_key")
        
        tokens = self._get_non_eof_tokens("camelCase")
        self.assertEqual(tokens[0].value, "camelCase")
    
    def test_keyword_tokenization(self):
        """Test boolean and null keyword tokenization."""
        keywords = [
            ("true", TokenType.BOOLEAN),
            ("false", TokenType.BOOLEAN),
            ("null", TokenType.NULL),
        ]
        
        for keyword, expected_type in keywords:
            with self.subTest(keyword=keyword):
                tokens = self._get_non_eof_tokens(keyword)
                self.assertEqual(tokens[0].type, expected_type)
                self.assertEqual(tokens[0].value, keyword)
    
    def test_structural_tokenization(self):
        """Test structural character tokenization."""
        structural_chars = "{}[],:".strip()
        expected_types = [
            TokenType.LBRACE, TokenType.RBRACE,
            TokenType.LBRACKET, TokenType.RBRACKET,
            TokenType.COMMA, TokenType.COLON
        ]
        
        tokens = self._get_non_eof_tokens(structural_chars)
        self.assertEqual(len(tokens), len(expected_types))
        
        for token, expected_type in zip(tokens, expected_types):
            self.assertEqual(token.type, expected_type)
    
    def test_malformed_json_tokenization(self):
        """Test tokenization of common malformed JSON patterns."""
        # Unquoted object key
        tokens = self._get_non_eof_tokens('key: "value"')
        token_types = [t.type for t in tokens]
        expected = [TokenType.IDENTIFIER, TokenType.COLON, TokenType.STRING]
        self.assertEqual(token_types, expected)
        
        # Mixed quotes
        tokens = self._get_non_eof_tokens("{'key': \"value\"}")
        values = [t.value for t in tokens if t.type in (TokenType.STRING, TokenType.IDENTIFIER)]
        self.assertIn("key", values)
        self.assertIn("value", values)
    
    def test_whitespace_and_newline_handling(self):
        """Test whitespace handling behavior."""
        # Spaces should be ignored except in strings
        tokens = self._get_non_eof_tokens('  "test"  ')
        meaningful_tokens = [t for t in tokens if t.type not in (TokenType.NEWLINE,)]
        self.assertEqual(len(meaningful_tokens), 1)
        self.assertEqual(meaningful_tokens[0].type, TokenType.STRING)
        
        # Newlines should be tokenized for potential error reporting
        tokens = self._get_non_eof_tokens('line1\nline2')
        has_newline = any(t.type == TokenType.NEWLINE for t in tokens)
        self.assertTrue(has_newline)


if __name__ == '__main__':
    unittest.main()