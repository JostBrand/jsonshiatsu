"""
Test cases for the jsonshiatsu lexer.
"""

import unittest
from jsonshiatsu.core.tokenizer import Lexer, TokenType


class TestLexer(unittest.TestCase):
    
    def test_empty_string(self):
        lexer = Lexer("")
        tokens = lexer.get_all_tokens()
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, TokenType.EOF)
    
    def test_quoted_strings(self):
        # Double quotes
        lexer = Lexer('"test"')
        tokens = lexer.get_all_tokens()
        self.assertEqual(tokens[0].type, TokenType.STRING)
        self.assertEqual(tokens[0].value, "test")
        
        # Single quotes
        lexer = Lexer("'test'")
        tokens = lexer.get_all_tokens()
        self.assertEqual(tokens[0].type, TokenType.STRING)
        self.assertEqual(tokens[0].value, "test")
    
    def test_strings_with_special_chars(self):
        lexer = Lexer('"test with spaces"')
        tokens = lexer.get_all_tokens()
        self.assertEqual(tokens[0].type, TokenType.STRING)
        self.assertEqual(tokens[0].value, "test with spaces")
    
    def test_strings_with_embedded_quotes(self):
        lexer = Lexer('"test \\"embedded\\" quotes"')
        tokens = lexer.get_all_tokens()
        self.assertEqual(tokens[0].type, TokenType.STRING)
        self.assertEqual(tokens[0].value, 'test "embedded" quotes')
        
        lexer = Lexer("'test \\'embedded\\' quotes'")
        tokens = lexer.get_all_tokens()
        self.assertEqual(tokens[0].type, TokenType.STRING)
        self.assertEqual(tokens[0].value, "test 'embedded' quotes")
    
    def test_strings_with_newlines(self):
        lexer = Lexer('"test\\nwith\\nnewlines"')
        tokens = lexer.get_all_tokens()
        self.assertEqual(tokens[0].type, TokenType.STRING)
        self.assertEqual(tokens[0].value, "test\nwith\nnewlines")
    
    def test_numbers(self):
        # Positive integer
        lexer = Lexer("123")
        tokens = lexer.get_all_tokens()
        self.assertEqual(tokens[0].type, TokenType.NUMBER)
        self.assertEqual(tokens[0].value, "123")
        
        # Negative integer
        lexer = Lexer("-456")
        tokens = lexer.get_all_tokens()
        self.assertEqual(tokens[0].type, TokenType.NUMBER)
        self.assertEqual(tokens[0].value, "-456")
        
        # Positive float
        lexer = Lexer("123.45")
        tokens = lexer.get_all_tokens()
        self.assertEqual(tokens[0].type, TokenType.NUMBER)
        self.assertEqual(tokens[0].value, "123.45")
        
        # Negative float
        lexer = Lexer("-123.45")
        tokens = lexer.get_all_tokens()
        self.assertEqual(tokens[0].type, TokenType.NUMBER)
        self.assertEqual(tokens[0].value, "-123.45")
        
        # Float without leading digit
        lexer = Lexer(".5")
        tokens = lexer.get_all_tokens()
        self.assertEqual(tokens[0].type, TokenType.NUMBER)
        self.assertEqual(tokens[0].value, ".5")
    
    def test_structural_tokens(self):
        lexer = Lexer('{}[],:')
        tokens = lexer.get_all_tokens()
        
        expected_types = [
            TokenType.LBRACE,
            TokenType.RBRACE,
            TokenType.LBRACKET,
            TokenType.RBRACKET,
            TokenType.COMMA,
            TokenType.COLON,
            TokenType.EOF
        ]
        
        for i, expected_type in enumerate(expected_types):
            self.assertEqual(tokens[i].type, expected_type)
    
    def test_identifiers(self):
        lexer = Lexer("test")
        tokens = lexer.get_all_tokens()
        self.assertEqual(tokens[0].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[0].value, "test")
        
        lexer = Lexer("test_var")
        tokens = lexer.get_all_tokens()
        self.assertEqual(tokens[0].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[0].value, "test_var")
    
    def test_boolean_and_null(self):
        # Boolean true
        lexer = Lexer("true")
        tokens = lexer.get_all_tokens()
        self.assertEqual(tokens[0].type, TokenType.BOOLEAN)
        self.assertEqual(tokens[0].value, "true")
        
        # Boolean false
        lexer = Lexer("false")
        tokens = lexer.get_all_tokens()
        self.assertEqual(tokens[0].type, TokenType.BOOLEAN)
        self.assertEqual(tokens[0].value, "false")
        
        # Null
        lexer = Lexer("null")
        tokens = lexer.get_all_tokens()
        self.assertEqual(tokens[0].type, TokenType.NULL)
        self.assertEqual(tokens[0].value, "null")
    
    def test_whitespace_handling(self):
        lexer = Lexer("  test  ")
        tokens = lexer.get_all_tokens()
        # Whitespace should be skipped, only identifier and EOF should remain
        self.assertEqual(len(tokens), 2)
        self.assertEqual(tokens[0].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[1].type, TokenType.EOF)
    
    def test_newline_handling(self):
        lexer = Lexer("test\ntest2")
        tokens = lexer.get_all_tokens()
        expected_types = [
            TokenType.IDENTIFIER,
            TokenType.NEWLINE,
            TokenType.IDENTIFIER,
            TokenType.EOF
        ]
        
        for i, expected_type in enumerate(expected_types):
            self.assertEqual(tokens[i].type, expected_type)


if __name__ == '__main__':
    unittest.main()