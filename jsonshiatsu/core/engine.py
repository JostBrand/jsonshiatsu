"""
Parser for jsonshiatsu - converts tokens into Python data structures.
"""

import io
import json
from typing import Any, Callable, Optional, TextIO, Union

from ..security.exceptions import (
    ErrorReporter,
    ErrorSuggestionEngine,
    ParseError,
    SecurityError,
)
from ..security.limits import LimitValidator
from ..utils.config import ParseConfig
from .tokenizer import Lexer, Position, Token, TokenType
from .transformer import JSONPreprocessor


class Parser:
    def __init__(
        self,
        tokens: list[Token],
        config: ParseConfig,
        error_reporter: Optional[ErrorReporter] = None,
    ):
        self.tokens = tokens
        self.tokens_length = len(tokens)  # Cache length for performance
        self.pos = 0
        self.config = config
        from ..utils.config import ParseLimits

        # Optional validator for performance when limits are not needed
        self.validator = (
            LimitValidator(config.limits or ParseLimits()) if config.limits else None
        )
        self.error_reporter = error_reporter
        # Token caching for performance
        self._token_cache: Optional[Token] = None
        self._token_cache_pos = -1

    def current_token(self) -> Token:
        if self._token_cache_pos != self.pos:
            if self.pos >= self.tokens_length:
                if self.tokens:
                    self._token_cache = self.tokens[-1]
                else:
                    # Create a dummy EOF token if no tokens exist
                    self._token_cache = Token(TokenType.EOF, "", Position(0, 0))
            else:
                self._token_cache = self.tokens[self.pos]
            self._token_cache_pos = self.pos
        # At this point _token_cache is guaranteed to be not None
        return self._token_cache  # type: ignore

    def peek_token(self, offset: int = 1) -> Token:
        pos = self.pos + offset
        if pos >= self.tokens_length:
            return self.tokens[-1]
        return self.tokens[pos]

    def advance(self) -> Token:
        token = self.current_token()
        if self.pos < self.tokens_length - 1:
            self.pos += 1
            self._token_cache_pos = -1  # Invalidate cache
        return token

    def skip_whitespace_and_newlines(self) -> None:
        while (
            self.pos < self.tokens_length
            and self.tokens[self.pos].type
            in (
                TokenType.WHITESPACE,
                TokenType.NEWLINE,
            )
            and self.current_token().type != TokenType.EOF
        ):
            self.advance()

    def parse_value(self) -> Any:
        self.skip_whitespace_and_newlines()
        token = self.current_token()

        if token.type == TokenType.STRING:
            if self.validator:
                self.validator.validate_string_length(
                    token.value, f"line {token.position.line}"
                )
            self.advance()
            return self._unescape_string(token.value)

        elif token.type == TokenType.NUMBER:
            if self.validator:
                self.validator.validate_number_length(
                    token.value, f"line {token.position.line}"
                )
            self.advance()
            value = token.value
            if "." in value or "e" in value.lower():
                return float(value)
            return int(value)

        elif token.type == TokenType.BOOLEAN:
            self.advance()
            return token.value == "true"

        elif token.type == TokenType.NULL:
            self.advance()
            return None

        elif token.type == TokenType.IDENTIFIER:
            if self.validator:
                self.validator.validate_string_length(
                    token.value, f"line {token.position.line}"
                )
            identifier_value = token.value
            self.advance()

            if self.current_token().type == TokenType.STRING and identifier_value in [
                "Date",
                "RegExp",
                "ObjectId",
                "UUID",
                "ISODate",
            ]:
                string_value = self.current_token().value
                self.advance()
                return string_value

            return identifier_value

        elif token.type == TokenType.LBRACE:
            return self.parse_object()

        elif token.type == TokenType.LBRACKET:
            return self.parse_array()

        else:
            self._raise_parse_error(
                f"Unexpected token: {token.type}",
                token.position,
                ErrorSuggestionEngine.suggest_for_unexpected_token(str(token.value)),
            )

    def parse_object(self) -> dict[str, Any]:
        self.skip_whitespace_and_newlines()

        if self.current_token().type != TokenType.LBRACE:
            self._raise_parse_error("Expected '{'", self.current_token().position)

        if self.validator:
            self.validator.enter_structure()

        self.advance()
        self.skip_whitespace_and_newlines()

        obj: dict[str, Any] = {}

        if self.current_token().type == TokenType.RBRACE:
            self.advance()
            if self.validator:
                self.validator.exit_structure()
            return obj

        while True:
            self.skip_whitespace_and_newlines()

            key_token = self.current_token()
            if key_token.type in [TokenType.STRING, TokenType.IDENTIFIER]:
                key = key_token.value
                self.advance()
            else:
                self._raise_parse_error(
                    "Expected object key",
                    key_token.position,
                    [
                        "Object keys must be strings or identifiers",
                        "Use quotes around keys with special characters",
                    ],
                )

            self.skip_whitespace_and_newlines()

            if self.current_token().type != TokenType.COLON:
                self._raise_parse_error(
                    "Expected ':' after key",
                    self.current_token().position,
                    [
                        "Object keys must be followed by a colon",
                        "Check for missing colon after key",
                    ],
                )

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

            if self.validator:
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
                    self._raise_parse_error(
                        "Unexpected end of input, expected '}' to close object",
                        self.current_token().position,
                        ErrorSuggestionEngine.suggest_for_unclosed_structure("object"),
                    )

        if self.current_token().type == TokenType.RBRACE:
            self.advance()
            if self.validator:
                self.validator.exit_structure()
        else:
            self._raise_parse_error(
                "Expected '}' to close object",
                self.current_token().position,
                ErrorSuggestionEngine.suggest_for_unclosed_structure("object"),
            )

        return obj

    def parse_array(self) -> list[Any]:
        self.skip_whitespace_and_newlines()

        if self.current_token().type != TokenType.LBRACKET:
            self._raise_parse_error("Expected '['", self.current_token().position)

        if self.validator:
            self.validator.enter_structure()

        self.advance()
        self.skip_whitespace_and_newlines()

        arr: list[Any] = []

        if self.current_token().type == TokenType.RBRACKET:
            self.advance()
            if self.validator:
                self.validator.exit_structure()
            return arr

        while True:
            self.skip_whitespace_and_newlines()

            if self.current_token().type == TokenType.RBRACKET:
                break

            try:
                value = self.parse_value()
                arr.append(value)

                if self.validator:
                    self.validator.validate_array_items(len(arr))
            except ParseError:
                if self.current_token().type not in [
                    TokenType.RBRACKET,
                    TokenType.COMMA,
                ]:
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
                    self._raise_parse_error(
                        "Unexpected end of input, expected ']' to close array",
                        self.current_token().position,
                        ErrorSuggestionEngine.suggest_for_unclosed_structure("array"),
                    )

        if self.current_token().type == TokenType.RBRACKET:
            self.advance()
            if self.validator:
                self.validator.exit_structure()
        else:
            self._raise_parse_error(
                "Expected ']' to close array",
                self.current_token().position,
                ErrorSuggestionEngine.suggest_for_unclosed_structure("array"),
            )

        return arr

    def parse(self) -> Any:
        self.skip_whitespace_and_newlines()
        return self.parse_value()

    def _unescape_string(self, s: str) -> str:
        if "\\" not in s:
            return s

        result = []
        i = 0
        while i < len(s):
            if s[i] == "\\" and i + 1 < len(s):
                next_char = s[i + 1]
                if next_char == '"':
                    result.append('"')
                elif next_char == "\\":
                    result.append("\\")
                elif next_char == "/":
                    result.append("/")
                elif next_char == "b":
                    result.append("\b")
                elif next_char == "f":
                    result.append("\f")
                elif next_char == "n":
                    result.append("\n")
                elif next_char == "r":
                    result.append("\r")
                elif next_char == "t":
                    result.append("\t")
                elif next_char == "u" and i + 5 < len(s):
                    try:
                        hex_digits = s[i + 2 : i + 6]
                        unicode_char = chr(int(hex_digits, 16))
                        result.append(unicode_char)
                        i += 5
                    except (ValueError, OverflowError):
                        result.append(s[i])
                else:
                    result.append(s[i])
                    result.append(next_char)
                i += 2
            else:
                result.append(s[i])
                i += 1

        return "".join(result)

    def _raise_parse_error(
        self, message: str, position: Position, suggestions: Optional[list[str]] = None
    ) -> None:
        if self.error_reporter:
            raise self.error_reporter.create_parse_error(message, position, suggestions)
        else:
            raise ParseError(message, position, suggestions=suggestions)


def loads(
    s: Union[str, bytes, bytearray],
    *,
    cls: Optional[Any] = None,
    object_hook: Optional[Callable[[dict[str, Any]], Any]] = None,
    parse_float: Optional[Callable[[str], Any]] = None,
    parse_int: Optional[Callable[[str], Any]] = None,
    parse_constant: Optional[Callable[[str], Any]] = None,
    object_pairs_hook: Optional[Callable[[list[tuple[str, Any]]], Any]] = None,
    # jsonshiatsu-specific parameters
    strict: bool = False,
    config: Optional[ParseConfig] = None,
    **kw: Any,
) -> Any:
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
        s = s.decode("utf-8")

    # Create configuration from parameters
    if config is None:
        from ..utils.config import PreprocessingConfig

        preprocessing_config = (
            PreprocessingConfig.conservative()
            if strict
            else PreprocessingConfig.aggressive()
        )
        config = ParseConfig(
            preprocessing_config=preprocessing_config,
            fallback=True,  # Always fallback for json compatibility
            duplicate_keys=bool(object_pairs_hook),  # Enable if pairs hook provided
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


def load(
    fp: TextIO,
    *,
    cls: Optional[Any] = None,
    object_hook: Optional[Callable[[dict[str, Any]], Any]] = None,
    parse_float: Optional[Callable[[str], Any]] = None,
    parse_int: Optional[Callable[[str], Any]] = None,
    parse_constant: Optional[Callable[[str], Any]] = None,
    object_pairs_hook: Optional[Callable[[list[tuple[str, Any]]], Any]] = None,
    # jsonshiatsu-specific parameters
    strict: bool = False,
    config: Optional[ParseConfig] = None,
    **kw: Any,
) -> Any:
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
        **kw,
    )


def parse(
    text: Union[str, TextIO],
    fallback: bool = True,
    duplicate_keys: bool = False,
    aggressive: bool = False,
    config: Optional[ParseConfig] = None,
) -> Any:
    """
    Parse a JSON-like string or stream into a Python data structure.

    This is the legacy jsonshiatsu API. For drop-in json replacement, use
    loads()/load().

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
            fallback=fallback, duplicate_keys=duplicate_keys, aggressive=aggressive
        )

    return _parse_internal(text, config)


def _parse_internal(text: Union[str, TextIO], config: ParseConfig) -> Any:
    """Internal parsing function used by both parse() and loads()."""
    if hasattr(text, "read"):
        from ..streaming.processor import StreamingParser

        streaming_parser = StreamingParser(config)
        if isinstance(text, str):
            stream: TextIO = io.StringIO(text)
        else:
            stream = text
        return streaming_parser.parse_stream(stream)

    if isinstance(text, str):
        if config.limits and config.limits.max_input_size:
            LimitValidator(config.limits).validate_input_size(text)

        if len(text) > config.streaming_threshold:
            stream = io.StringIO(text)
            from ..streaming.processor import StreamingParser

            streaming_parser = StreamingParser(config)
            return streaming_parser.parse_stream(stream)

        # Store original text for error reporting (dynamic attribute)
        config._original_text = text  # type: ignore[attr-defined]
        error_reporter = (
            ErrorReporter(text, config.max_error_context)
            if config.include_position
            else None
        )

        preprocessed_text = JSONPreprocessor.preprocess(
            text, aggressive=config.aggressive, config=config.preprocessing_config
        )

        try:
            lexer = Lexer(preprocessed_text)
            tokens = lexer.get_all_tokens()
            parser = Parser(tokens, config, error_reporter)
            return parser.parse()

        except (ParseError, SecurityError) as e:
            if config.fallback and not isinstance(e, SecurityError):
                # Try additional preprocessing on failure
                try:
                    # Apply more aggressive preprocessing
                    from ..utils.config import PreprocessingConfig

                    # Use more aggressive config for fallback
                    fallback_config = PreprocessingConfig.aggressive()
                    fallback_text = JSONPreprocessor.preprocess(
                        text, True, fallback_config
                    )

                    # Try parsing the fallback text
                    lexer = Lexer(fallback_text)
                    tokens = lexer.get_all_tokens()
                    parser = Parser(tokens, config, error_reporter)
                    return parser.parse()

                except Exception:
                    # If that fails, try standard json.loads on various versions
                    try:
                        return json.loads(preprocessed_text)
                    except json.JSONDecodeError:
                        try:
                            return json.loads(text)
                        except json.JSONDecodeError:
                            # Final attempt - try to extract just the JSON part more
                            # aggressively
                            try:
                                cleaned = JSONPreprocessor.extract_first_json(
                                    preprocessed_text
                                )
                                return json.loads(cleaned)
                            except json.JSONDecodeError:
                                raise e from None
            else:
                raise e

    else:
        raise ValueError("Input must be a string or file-like object")


def _apply_parse_hooks(
    obj: Any,
    parse_float: Optional[Callable[[str], Any]] = None,
    parse_int: Optional[Callable[[str], Any]] = None,
    parse_constant: Optional[Callable[[str], Any]] = None,
) -> Any:
    """Apply json.loads-style parse hooks recursively."""
    if isinstance(obj, dict):
        return {
            k: _apply_parse_hooks(v, parse_float, parse_int, parse_constant)
            for k, v in obj.items()
        }
    elif isinstance(obj, list):
        return [
            _apply_parse_hooks(item, parse_float, parse_int, parse_constant)
            for item in obj
        ]
    elif isinstance(obj, float) and parse_float:
        return parse_float(str(obj))
    elif isinstance(obj, int) and parse_int:
        return parse_int(str(obj))
    elif obj in (float("inf"), float("-inf")) and parse_constant:
        return parse_constant("Infinity" if obj == float("inf") else "-Infinity")
    elif obj != obj and parse_constant:  # NaN check
        return parse_constant("NaN")
    else:
        return obj


def _apply_object_hook_recursively(
    obj: Any, hook: Callable[[dict[str, Any]], Any]
) -> Any:
    """Apply the object_hook recursively."""
    if isinstance(obj, dict):
        # First, recurse into the values of the dictionary
        processed_obj = {
            k: _apply_object_hook_recursively(v, hook) for k, v in obj.items()
        }
        # Then, apply the hook to the dictionary itself
        return hook(processed_obj)
    elif isinstance(obj, list):
        return [_apply_object_hook_recursively(item, hook) for item in obj]
    else:
        return obj


def _apply_object_pairs_hook_recursively(
    obj: Any, hook: Callable[[list[tuple[str, Any]]], Any]
) -> Any:
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


def dump(
    obj: Any,
    fp: TextIO,
    *,
    skipkeys: bool = False,
    ensure_ascii: bool = True,
    check_circular: bool = True,
    allow_nan: bool = True,
    cls: Optional[Any] = None,
    indent: Optional[Union[int, str]] = None,
    separators: Optional[tuple[str, str]] = None,
    default: Optional[Callable[[Any], Any]] = None,
    sort_keys: bool = False,
    **kw: Any,
) -> None:
    """
    Serialize obj as a JSON formatted stream to fp (drop-in replacement for json.dump).

    This function delegates to the standard json.dump() since jsonshiatsu focuses on
    parsing/repair, not serialization.
    """
    return json.dump(
        obj,
        fp,
        skipkeys=skipkeys,
        ensure_ascii=ensure_ascii,
        check_circular=check_circular,
        allow_nan=allow_nan,
        cls=cls,
        indent=indent,
        separators=separators,
        default=default,
        sort_keys=sort_keys,
        **kw,
    )


def dumps(
    obj: Any,
    *,
    skipkeys: bool = False,
    ensure_ascii: bool = True,
    check_circular: bool = True,
    allow_nan: bool = True,
    cls: Optional[Any] = None,
    indent: Optional[Union[int, str]] = None,
    separators: Optional[tuple[str, str]] = None,
    default: Optional[Callable[[Any], Any]] = None,
    sort_keys: bool = False,
    **kw: Any,
) -> str:
    """
    Serialize obj to a JSON formatted str (drop-in replacement for json.dumps).

    This function delegates to the standard json.dumps() since jsonshiatsu focuses on
    parsing/repair, not serialization.
    """
    return json.dumps(
        obj,
        skipkeys=skipkeys,
        ensure_ascii=ensure_ascii,
        check_circular=check_circular,
        allow_nan=allow_nan,
        cls=cls,
        indent=indent,
        separators=separators,
        default=default,
        sort_keys=sort_keys,
        **kw,
    )


class JSONDecoder(json.JSONDecoder):
    """
    Drop-in replacement for json.JSONDecoder that uses jsonshiatsu for parsing.

    This class extends the standard JSONDecoder but uses jsonshiatsu's enhanced
    parsing capabilities while maintaining full API compatibility.
    """

    def __init__(
        self,
        *,
        object_hook: Optional[Callable[[dict[str, Any]], Any]] = None,
        parse_float: Optional[Callable[[str], Any]] = None,
        parse_int: Optional[Callable[[str], Any]] = None,
        parse_constant: Optional[Callable[[str], Any]] = None,
        strict: bool = True,
        object_pairs_hook: Optional[Callable[[list[tuple[str, Any]]], Any]] = None,
    ) -> None:
        # Call super().__init__ with proper defaults to ensure compatibility
        super().__init__(
            object_hook=object_hook,
            parse_float=parse_float,
            parse_int=parse_int,
            parse_constant=parse_constant,
            strict=strict,
            object_pairs_hook=object_pairs_hook,
        )
        # Store original scan_once for compatibility
        self.scan_once = self._scan_once

    def decode(self, s: str, _w: Optional[Any] = None) -> Any:
        """Decode a JSON string using jsonshiatsu."""
        return loads(
            s,
            object_hook=self.object_hook,
            parse_float=self.parse_float,
            parse_int=self.parse_int,
            parse_constant=self.parse_constant,
            object_pairs_hook=self.object_pairs_hook,
            strict=self.strict,
        )

    def raw_decode(self, s: str, idx: int = 0) -> tuple[Any, int]:
        """Decode a JSON string starting at idx."""
        try:
            result = self.decode(s[idx:])
            # Find end position by re-parsing with standard json to get exact position
            try:
                json.loads(s[idx:])
                end_idx = len(s)
            except json.JSONDecodeError:
                # Try to estimate end position
                end_idx = idx + len(s[idx:].lstrip())
            return result, end_idx
        except json.JSONDecodeError:
            raise

    def _scan_once(self, s: str, idx: int) -> tuple[Any, int]:
        """Internal method for compatibility."""
        return self.raw_decode(s, idx)


class JSONEncoder(json.JSONEncoder):
    """
    Drop-in replacement for json.JSONEncoder.

    Since jsonshiatsu focuses on parsing/repair rather than encoding,
    this class simply delegates to the standard JSONEncoder.
    """

    pass


# Import JSONDecodeError from standard json module for compatibility
JSONDecodeError = json.JSONDecodeError
