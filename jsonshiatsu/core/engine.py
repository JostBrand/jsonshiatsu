"""
Parser for jsonshiatsu - converts tokens into Python data structures.
"""

import json
import io
from typing import Any, Dict, List, Optional, Union, TextIO, Callable
from .tokenizer import Lexer, Token, TokenType
from .transformer import JSONPreprocessor
from ..utils.config import ParseConfig, ParseLimits
from ..security.limits import LimitValidator
from ..security.exceptions import ParseError, SecurityError, ErrorReporter, ErrorSuggestionEngine


class Parser:
    def __init__(self, tokens: List[Token], config: ParseConfig, error_reporter: Optional[ErrorReporter] = None):
        self.tokens = tokens
        self.pos = 0
        self.config = config
        self.validator = LimitValidator(config.limits)
        self.error_reporter = error_reporter
    
    def current_token(self) -> Token:
        if self.pos >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[self.pos]
    
    def peek_token(self, offset: int = 1) -> Token:
        pos = self.pos + offset
        if pos >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[pos]
    
    def advance(self) -> Token:
        token = self.current_token()
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return token
    
    def skip_whitespace_and_newlines(self):
        while (self.current_token().type in [TokenType.WHITESPACE, TokenType.NEWLINE] and
               self.current_token().type != TokenType.EOF):
            self.advance()
    
    def parse_value(self) -> Any:
        """Parse a JSON value."""
        self.skip_whitespace_and_newlines()
        token = self.current_token()
        
        if token.type == TokenType.STRING:
            self.validator.validate_string_length(token.value, f"line {token.position.line}")
            self.advance()
            return token.value
        
        elif token.type == TokenType.NUMBER:
            self.validator.validate_number_length(token.value, f"line {token.position.line}")
            self.advance()
            value = token.value
            if '.' in value or 'e' in value.lower():
                return float(value)
            return int(value)
        
        elif token.type == TokenType.BOOLEAN:
            self.advance()
            return token.value == 'true'
        
        elif token.type == TokenType.NULL:
            self.advance()
            return None
        
        elif token.type == TokenType.IDENTIFIER:
            self.validator.validate_string_length(token.value, f"line {token.position.line}")
            identifier_value = token.value
            self.advance()
            
            # Handle function call patterns like Date("2025-08-01")
            # If identifier is followed by a string, treat as function call and return the string value
            if (self.current_token().type == TokenType.STRING and 
                identifier_value in ['Date', 'RegExp', 'ObjectId', 'UUID', 'ISODate']):
                # Extract and return the actual value from inside the function call
                string_value = self.current_token().value
                self.advance()
                return string_value
            
            return identifier_value
        
        elif token.type == TokenType.LBRACE:
            return self.parse_object()
        
        elif token.type == TokenType.LBRACKET:
            return self.parse_array()
        
        else:
            self._raise_parse_error(f"Unexpected token: {token.type}", token.position, 
                                   ErrorSuggestionEngine.suggest_for_unexpected_token(str(token.value)))
    
    def parse_object(self) -> Dict[str, Any]:
        """Parse a JSON object."""
        self.skip_whitespace_and_newlines()
        
        if self.current_token().type != TokenType.LBRACE:
            self._raise_parse_error("Expected '{'", self.current_token().position)
        
        self.validator.enter_structure()
        
        self.advance()
        self.skip_whitespace_and_newlines()
        
        obj = {}
        
        if self.current_token().type == TokenType.RBRACE:
            self.advance()
            self.validator.exit_structure()
            return obj
        
        while True:
            self.skip_whitespace_and_newlines()
            
            key_token = self.current_token()
            if key_token.type in [TokenType.STRING, TokenType.IDENTIFIER]:
                key = key_token.value
                self.advance()
            else:
                self._raise_parse_error("Expected object key", key_token.position, 
                                       ["Object keys must be strings or identifiers", "Use quotes around keys with special characters"])
            
            self.skip_whitespace_and_newlines()
            
            if self.current_token().type != TokenType.COLON:
                self._raise_parse_error("Expected ':' after key", self.current_token().position,
                                       ["Object keys must be followed by a colon", "Check for missing colon after key"])
            
            self.advance()
            self.skip_whitespace_and_newlines()
            
            try:
                value = self.parse_value()
            except ParseError:
                value = None
            
            if key in obj and not self.config.duplicate_keys:
                obj[key] = value
            elif key in obj and self.config.duplicate_keys:
                if not isinstance(obj[key], list):
                    obj[key] = [obj[key]]
                obj[key].append(value)
            else:
                obj[key] = value
            
            self.validator.validate_object_keys(len(obj))
            
            self.skip_whitespace_and_newlines()
            
            if self.current_token().type == TokenType.COMMA:
                self.advance()
                self.skip_whitespace_and_newlines()
                
                if self.current_token().type == TokenType.RBRACE:
                    break
                    
            elif self.current_token().type == TokenType.RBRACE:
                break
            else:
                if self.current_token().type == TokenType.EOF:
                    self._raise_parse_error("Unexpected end of input, expected '}' to close object", 
                                           self.current_token().position,
                                           ErrorSuggestionEngine.suggest_for_unclosed_structure("object"))
        
        if self.current_token().type == TokenType.RBRACE:
            self.advance()
            self.validator.exit_structure()
        else:
            self._raise_parse_error("Expected '}' to close object", self.current_token().position,
                                   ErrorSuggestionEngine.suggest_for_unclosed_structure("object"))
        
        return obj
    
    def parse_array(self) -> List[Any]:
        """Parse a JSON array."""
        self.skip_whitespace_and_newlines()
        
        if self.current_token().type != TokenType.LBRACKET:
            self._raise_parse_error("Expected '['", self.current_token().position)
        
        self.validator.enter_structure()
        
        self.advance()
        self.skip_whitespace_and_newlines()
        
        arr = []
        
        if self.current_token().type == TokenType.RBRACKET:
            self.advance()
            self.validator.exit_structure()
            return arr
        
        while True:
            self.skip_whitespace_and_newlines()
            
            try:
                value = self.parse_value()
                arr.append(value)
                
                self.validator.validate_array_items(len(arr))
            except ParseError:
                arr.append(None)
            
            self.skip_whitespace_and_newlines()
            
            if self.current_token().type == TokenType.COMMA:
                self.advance()
                self.skip_whitespace_and_newlines()
                
                if self.current_token().type == TokenType.RBRACKET:
                    break
                    
            elif self.current_token().type == TokenType.RBRACKET:
                break
            else:
                if self.current_token().type == TokenType.EOF:
                    self._raise_parse_error("Unexpected end of input, expected ']' to close array",
                                           self.current_token().position,
                                           ErrorSuggestionEngine.suggest_for_unclosed_structure("array"))
        
        if self.current_token().type == TokenType.RBRACKET:
            self.advance()
            self.validator.exit_structure()
        else:
            self._raise_parse_error("Expected ']' to close array", self.current_token().position,
                                   ErrorSuggestionEngine.suggest_for_unclosed_structure("array"))
        
        return arr
    
    def parse(self) -> Any:
        """Parse the tokens into a Python data structure."""
        self.skip_whitespace_and_newlines()
        return self.parse_value()
    
    def _raise_parse_error(self, message: str, position, suggestions: Optional[List[str]] = None):
        if self.error_reporter:
            raise self.error_reporter.create_parse_error(message, position, suggestions)
        else:
            raise ParseError(message, position, suggestions=suggestions)


def loads(s: Union[str, bytes, bytearray], 
          *,
          cls=None,
          object_hook: Optional[Callable[[Dict[str, Any]], Any]] = None,
          parse_float: Optional[Callable[[str], Any]] = None,
          parse_int: Optional[Callable[[str], Any]] = None,
          parse_constant: Optional[Callable[[str], Any]] = None,
          object_pairs_hook: Optional[Callable[[List[tuple]], Any]] = None,
          # jsonshiatsu-specific parameters
          strict: bool = False,
          config: Optional[ParseConfig] = None,
          **kw) -> Any:
    """
    Deserialize a JSON string to a Python object (drop-in replacement for json.loads).
    
    Supports all standard json.loads parameters plus jsonshiatsu-specific options.
    
    Standard json.loads parameters:
        s: JSON string to parse (str, bytes, or bytearray)
        cls: Custom JSONDecoder class (currently ignored)
        object_hook: Function called for each decoded object (dict)
        parse_float: Function to parse JSON floats
        parse_int: Function to parse JSON integers  
        parse_constant: Function to parse JSON constants (Infinity, NaN)
        object_pairs_hook: Function called with ordered pairs for each object
        **kw: Additional keyword arguments (for compatibility)
    
    jsonshiatsu-specific parameters:
        strict: If True, use conservative preprocessing (default: False)
        config: ParseConfig object for advanced control
    
    Returns:
        Parsed Python data structure
    
    Raises:
        json.JSONDecodeError: If parsing fails (for json compatibility)
        SecurityError: If security limits are exceeded
    """
    # Convert bytes/bytearray to string if needed
    if isinstance(s, (bytes, bytearray)):
        s = s.decode('utf-8')
    
    # Create configuration from parameters
    if config is None:
        from ..utils.config import PreprocessingConfig
        preprocessing_config = (
            PreprocessingConfig.conservative() if strict 
            else PreprocessingConfig.aggressive()
        )
        config = ParseConfig(
            preprocessing_config=preprocessing_config,
            fallback=True,  # Always fallback for json compatibility
            duplicate_keys=bool(object_pairs_hook)  # Enable if pairs hook provided
        )
    
    try:
        result = _parse_internal(s, config)
        
        # Apply standard json.loads hooks
        if object_pairs_hook:
            result = _apply_object_pairs_hook_recursively(result, object_pairs_hook)
        elif object_hook:
            result = _apply_object_hook_recursively(result, object_hook)
        
        # Apply parse hooks recursively
        if parse_float or parse_int or parse_constant:
            result = _apply_parse_hooks(result, parse_float, parse_int, parse_constant)
        
        return result
        
    except (ParseError, SecurityError) as e:
        # Convert to JSONDecodeError for compatibility
        import json
        raise json.JSONDecodeError(str(e), s, 0) from e


def load(fp: TextIO,
         *,
         cls=None,
         object_hook: Optional[Callable[[Dict[str, Any]], Any]] = None,
         parse_float: Optional[Callable[[str], Any]] = None,
         parse_int: Optional[Callable[[str], Any]] = None,
         parse_constant: Optional[Callable[[str], Any]] = None,
         object_pairs_hook: Optional[Callable[[List[tuple]], Any]] = None,
         # jsonshiatsu-specific parameters
         strict: bool = False,
         config: Optional[ParseConfig] = None,
         **kw) -> Any:
    """
    Deserialize a JSON file to a Python object (drop-in replacement for json.load).
    
    Same as loads() but reads from a file-like object.
    
    Parameters:
        fp: File-like object containing JSON
        (all other parameters same as loads())
    
    Returns:
        Parsed Python data structure
    """
    return loads(
        fp.read(),
        cls=cls,
        object_hook=object_hook,
        parse_float=parse_float,
        parse_int=parse_int,
        parse_constant=parse_constant,
        object_pairs_hook=object_pairs_hook,
        strict=strict,
        config=config,
        **kw
    )


def parse(text: Union[str, TextIO], 
          fallback: bool = True, 
          duplicate_keys: bool = False, 
          aggressive: bool = False,
          config: Optional[ParseConfig] = None) -> Any:
    """
    Parse a JSON-like string or stream into a Python data structure.
    
    This is the legacy jsonshiatsu API. For drop-in json replacement, use loads()/load().
    
    Args:
        text: The JSON-like string to parse, or a file-like object for streaming
        fallback: If True, try standard JSON parsing if custom parsing fails
        duplicate_keys: If True, handle duplicate object keys by creating arrays
        aggressive: If True, apply aggressive preprocessing to handle malformed JSON
        config: Optional ParseConfig for advanced options and security limits
    
    Returns:
        Parsed Python data structure
    
    Raises:
        ParseError: If parsing fails and fallback is False
        SecurityError: If security limits are exceeded
        json.JSONDecodeError: If fallback parsing also fails
    """
    if config is None:
        config = ParseConfig(
            fallback=fallback,
            duplicate_keys=duplicate_keys,
            aggressive=aggressive
        )
    
    return _parse_internal(text, config)


def _parse_internal(text: Union[str, TextIO], config: ParseConfig) -> Any:
    """Internal parsing function used by both parse() and loads()."""
    if hasattr(text, 'read'):
        from ..streaming.processor import StreamingParser
        streaming_parser = StreamingParser(config)
        return streaming_parser.parse_stream(text)
    
    if isinstance(text, str):
        config.limits.max_input_size and LimitValidator(config.limits).validate_input_size(text)
        
        if len(text) > config.streaming_threshold:
            stream = io.StringIO(text)
            from ..streaming.processor import StreamingParser
            streaming_parser = StreamingParser(config)
            return streaming_parser.parse_stream(stream)
        
        config._original_text = text
        error_reporter = ErrorReporter(text, config.max_error_context) if config.include_position else None
        
        preprocessed_text = JSONPreprocessor.preprocess(text, aggressive=config.aggressive, config=config.preprocessing_config)
        
        try:
            lexer = Lexer(preprocessed_text)
            tokens = lexer.get_all_tokens()
            parser = Parser(tokens, config, error_reporter)
            return parser.parse()
            
        except (ParseError, SecurityError) as e:
            if config.fallback and not isinstance(e, SecurityError):
                try:
                    return json.loads(preprocessed_text)
                except json.JSONDecodeError:
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        raise e
            else:
                raise e
    
    else:
        raise ValueError("Input must be a string or file-like object")


def _apply_parse_hooks(obj: Any, 
                      parse_float: Optional[Callable[[str], Any]] = None,
                      parse_int: Optional[Callable[[str], Any]] = None, 
                      parse_constant: Optional[Callable[[str], Any]] = None) -> Any:
    """Apply json.loads-style parse hooks recursively."""
    if isinstance(obj, dict):
        return {k: _apply_parse_hooks(v, parse_float, parse_int, parse_constant) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_apply_parse_hooks(item, parse_float, parse_int, parse_constant) for item in obj]
    elif isinstance(obj, float) and parse_float:
        return parse_float(str(obj))
    elif isinstance(obj, int) and parse_int:
        return parse_int(str(obj))
    elif obj in (float('inf'), float('-inf')) and parse_constant:
        return parse_constant('Infinity' if obj == float('inf') else '-Infinity')
    elif obj != obj and parse_constant:  # NaN check
        return parse_constant('NaN')
    else:
        return obj


def _apply_object_hook_recursively(obj: Any, hook: Callable[[Dict[str, Any]], Any]) -> Any:
    """Apply the object_hook recursively."""
    if isinstance(obj, dict):
        # First, recurse into the values of the dictionary
        processed_obj = {k: _apply_object_hook_recursively(v, hook) for k, v in obj.items()}
        # Then, apply the hook to the dictionary itself
        return hook(processed_obj)
    elif isinstance(obj, list):
        return [_apply_object_hook_recursively(item, hook) for item in obj]
    else:
        return obj


def _apply_object_pairs_hook_recursively(obj: Any, hook: Callable[[List[tuple]], Any]) -> Any:
    """Apply the object_pairs_hook recursively."""
    if isinstance(obj, dict):
        # Recurse into values first
        processed_items = [
            (k, _apply_object_pairs_hook_recursively(v, hook)) for k, v in obj.items()
        ]
        # Apply the hook to the list of pairs
        return hook(processed_items)
    elif isinstance(obj, list):
        return [_apply_object_pairs_hook_recursively(item, hook) for item in obj]
    else:
        return obj
