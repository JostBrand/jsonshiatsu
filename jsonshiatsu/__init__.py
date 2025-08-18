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

from .core.engine import (
    JSONDecodeError,
    JSONDecoder,
    JSONEncoder,
    dump,
    dumps,
    load,
    loads,
    parse,
)
from .recovery.strategies import (
    ErrorSeverity,
    PartialParseError,
    PartialParseResult,
    RecoveryAction,
    RecoveryLevel,
    extract_valid_data,
    parse_partial,
    parse_with_fallback,
)
from .security.exceptions import ParseError, SecurityError
from .streaming.processor import StreamingParser
from .utils.config import ParseConfig, ParseLimits, PreprocessingConfig

__version__ = "0.1.0"
__author__ = "jsonshiatsu contributors"

# Import additional attributes from standard json module for full compatibility
import json as _json

# Import standard json module attributes for compatibility
try:
    _json_version = getattr(_json, "__version__", "2.0.9")
    _json_author = getattr(_json, "__author__", "Bob Ippolito <bob@redivi.com>")
except AttributeError:
    _json_version = "2.0.9"
    _json_author = "Bob Ippolito <bob@redivi.com>"

# Add module attributes that mypy expects
__version__ = "0.1.0"
__author__ = "Jost Brandstetter <brandstetterjost@gmail.com>"
__all__ = [
    # Drop-in json replacement functions and classes
    "loads",
    "load",
    "dump",
    "dumps",
    "JSONDecoder",
    "JSONEncoder",
    "JSONDecodeError",
    # Legacy jsonshiatsu functions
    "parse",
    "parse_partial",
    "extract_valid_data",
    "parse_with_fallback",
    # Configuration classes
    "ParseConfig",
    "ParseLimits",
    "PreprocessingConfig",
    # Exception classes
    "ParseError",
    "SecurityError",
    # Advanced classes
    "StreamingParser",
    "RecoveryLevel",
    "RecoveryAction",
    "ErrorSeverity",
    "PartialParseResult",
    "PartialParseError",
]
