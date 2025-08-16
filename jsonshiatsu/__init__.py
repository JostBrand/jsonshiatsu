"""
jsonshiatsu - Therapeutic JSON parser that gently massages malformed JSON into shape.

jsonshiatsu provides loads() and load() functions that are direct drop-in 
replacements for Python's json library, but with the healing power to handle
malformed and non-standard JSON that would normally fail.

🤲 **Drop-in Replacement**: Just replace `import json` with `import jsonshiatsu as json`

Key Features:
- 100% compatible with json.loads() and json.load() APIs
- Parse malformed JSON: unquoted keys, single quotes, trailing commas
- Intelligent string escaping (fixes Windows file paths automatically)
- Auto-completion of incomplete JSON structures
- Partial error recovery - extract valid data from malformed input
- Security limits to prevent resource exhaustion attacks
- Streaming support for large files
- Enhanced error reporting with position tracking

Quick Start:
    # Drop-in replacement
    import jsonshiatsu as json
    data = json.loads('{ test: "this works!" }')  # Unquoted keys work!
    
    # Advanced features
    import jsonshiatsu
    result = jsonshiatsu.loads(malformed_json, strict=True)  # Conservative mode
    
    # Legacy API
    result = jsonshiatsu.parse('{ test: "this is a test"}')
    
    # Partial error recovery
    from jsonshiatsu import parse_partial, RecoveryLevel
    result = parse_partial(malformed_json, RecoveryLevel.SKIP_FIELDS)
"""

from .core.engine import parse, loads, load
from .utils.config import ParseConfig, ParseLimits, PreprocessingConfig
from .security.exceptions import ParseError, SecurityError
from .streaming.processor import StreamingParser
from .recovery.strategies import (
    parse_partial, extract_valid_data, parse_with_fallback,
    RecoveryLevel, RecoveryAction, ErrorSeverity, PartialParseResult, PartialParseError
)

__version__ = "0.1.0"
__all__ = [
    # Drop-in json replacement functions
    "loads", "load", 
    # Legacy jsonshiatsu functions  
    "parse", "parse_partial", "extract_valid_data", "parse_with_fallback",
    # Configuration classes
    "ParseConfig", "ParseLimits", "PreprocessingConfig", 
    # Exception classes
    "ParseError", "SecurityError",
    # Advanced classes
    "StreamingParser", "RecoveryLevel", "RecoveryAction", "ErrorSeverity", 
    "PartialParseResult", "PartialParseError"
]