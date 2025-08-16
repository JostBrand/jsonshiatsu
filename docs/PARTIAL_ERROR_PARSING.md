# Partial Error Parsing for jsonshiatsu

## 🎯 **Core Concept**

**Partial Error Parsing** means continuing to parse and extract valid data even when encountering malformed sections, rather than failing completely on the first error.

## 🔍 **Current jsonshiatsu Behavior vs. Desired Behavior**

### **Current Behavior (All-or-Nothing)**
```python
# This completely fails
malformed_json = '''
{
    "valid_field": "this works",
    "broken_field": {missing_quote: "oops},
    "another_valid": "this would work too"
}
'''

result = jsonshiatsu.parse(malformed_json)
# Throws ParseError - loses ALL data including valid parts
```

### **Desired Behavior (Partial Recovery)**
```python
# This should extract what it can and report what failed
result, errors = jsonshiatsu.parse_partial(malformed_json)

# Result contains:
{
    "valid_field": "this works", 
    "another_valid": "this would work too"
    # broken_field is omitted or marked as error
}

# Errors contains:
[
    {
        "path": "$.broken_field", 
        "error": "Missing quote around key 'missing_quote'",
        "line": 3, 
        "column": 20,
        "raw_content": '{missing_quote: "oops}'
    }
]
```

## 🛠️ **Implementation Strategy**

### **1. Error Recovery Levels**

```python
class RecoveryLevel(Enum):
    STRICT = "strict"           # Current behavior - fail on first error
    SKIP_FIELDS = "skip_fields" # Skip malformed fields, keep valid ones
    BEST_EFFORT = "best_effort" # Try to salvage even malformed fields
    COLLECT_ALL = "collect_all" # Parse everything possible, report all errors
```

### **2. Core Implementation Approach**

```python
class PartialParseResult:
    def __init__(self):
        self.data = None              # Successfully parsed data
        self.errors = []              # List of parsing errors encountered
        self.warnings = []            # Non-fatal issues
        self.success_rate = 0.0       # Percentage of input successfully parsed
        self.recovery_actions = []    # What the parser did to recover

class PartialParser:
    def __init__(self, recovery_level=RecoveryLevel.SKIP_FIELDS):
        self.recovery_level = recovery_level
        self.error_collector = []
        self.current_path = []
        
    def parse_with_recovery(self, text: str) -> PartialParseResult:
        """Parse JSON with error recovery capabilities."""
        try:
            # Try normal parsing first
            return PartialParseResult(data=self.parse_strict(text))
        except ParseError:
            # Fall back to recovery parsing
            return self.parse_with_errors(text)
```

## 🔧 **Specific Error Recovery Scenarios**

### **Scenario 1: Malformed Object Fields**

```python
# Input with multiple issues
malformed = '''
{
    "good_field": "valid",
    "bad_field": {broken syntax here},
    "another_good": 123,
    missing_quotes: "also bad",
    "final_good": true
}
'''

# Recovery Strategy: Skip malformed fields
result = {
    "good_field": "valid",
    "another_good": 123, 
    "final_good": true
}

errors = [
    {
        "field": "bad_field",
        "error": "Invalid object syntax",
        "recovery": "field_skipped"
    },
    {
        "field": "missing_quotes", 
        "error": "Unquoted key",
        "recovery": "field_skipped"  # Or could auto-fix in best_effort mode
    }
]
```

### **Scenario 2: Array with Mixed Valid/Invalid Elements**

```python
# Array with some malformed elements
malformed_array = '''
[
    {"id": 1, "name": "Alice"},
    {broken object here},
    {"id": 2, "name": "Bob"},
    invalid_element,
    {"id": 3, "name": "Charlie"}
]
'''

# Recovery: Extract valid elements, report invalid ones
result = [
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob"}, 
    {"id": 3, "name": "Charlie"}
]

errors = [
    {
        "index": 1,
        "error": "Malformed object", 
        "recovery": "element_skipped"
    },
    {
        "index": 3,
        "error": "Invalid element syntax",
        "recovery": "element_skipped"
    }
]
```

### **Scenario 3: Nested Structure Recovery**

```python
# Deeply nested with errors at different levels
complex_malformed = '''
{
    "user": {
        "id": 123,
        "profile": {
            "name": "Alice",
            "contacts": {
                "email": invalid@email,
                "phone": "555-1234"
            },
            "settings": broken_object
        },
        "metadata": {
            "created": "2023-01-01",
            "tags": ["user", "active"]
        }
    }
}
'''

# Recovery: Extract valid nested data
result = {
    "user": {
        "id": 123,
        "profile": {
            "name": "Alice",
            "contacts": {
                "phone": "555-1234"  # email skipped due to error
            }
            # settings skipped due to error
        },
        "metadata": {
            "created": "2023-01-01",
            "tags": ["user", "active"]
        }
    }
}
```

### **Scenario 4: Best-Effort Field Recovery**

```python
# Try to salvage malformed fields when possible
malformed_with_salvageable = '''
{
    "name": Alice,              # Missing quotes - can fix
    "age": 25,                  # Valid
    "email": alice@domain.com,  # Missing quotes - can fix 
    "tags": [tag1, tag2],      # Missing quotes on array elements - can fix
    "config": {broken: }       # Cannot salvage
}
'''

# Best-effort recovery
result = {
    "name": "Alice",           # Auto-quoted
    "age": 25,
    "email": "alice@domain.com", # Auto-quoted
    "tags": ["tag1", "tag2"],   # Auto-quoted array elements
    # config omitted - not salvageable
}

recovery_actions = [
    {"field": "name", "action": "added_quotes"},
    {"field": "email", "action": "added_quotes"}, 
    {"field": "tags[0]", "action": "added_quotes"},
    {"field": "tags[1]", "action": "added_quotes"},
    {"field": "config", "action": "field_skipped", "reason": "unsalvageable"}
]
```

## 🚀 **Advanced Recovery Techniques**

### **1. Context-Aware Recovery**

```python
# Detect patterns and apply appropriate fixes
class ContextualRecovery:
    def detect_pattern(self, error_context):
        if "missing quotes around" in error_context:
            return RecoveryAction.ADD_QUOTES
        elif "trailing comma" in error_context:
            return RecoveryAction.REMOVE_COMMA
        elif "missing colon" in error_context:
            return RecoveryAction.ADD_COLON
        elif "unclosed string" in error_context:
            return RecoveryAction.CLOSE_STRING
        else:
            return RecoveryAction.SKIP_FIELD
```

### **2. Statistical Recovery**

```python
# Use heuristics based on surrounding valid data
class StatisticalRecovery:
    def infer_type(self, malformed_value, context):
        # Look at similar fields in the same object/array
        # Infer likely intended type and format
        if context.similar_fields_are_strings():
            return attempt_string_recovery(malformed_value)
        elif context.similar_fields_are_numbers():
            return attempt_number_recovery(malformed_value)
```

### **3. Template-Based Recovery**

```python
# Learn from valid parts to fix malformed parts
class TemplateRecovery:
    def build_template(self, valid_objects):
        # Analyze structure of valid objects
        # Create template for expected format
        template = {
            "id": "number",
            "name": "string", 
            "email": "email_format",
            "tags": "string_array"
        }
        return template
    
    def apply_template(self, malformed_object, template):
        # Try to fix malformed object using template
        pass
```

## 📊 **Error Reporting & Diagnostics**

### **Detailed Error Information**

```python
class ParseError:
    def __init__(self):
        self.path = ""              # JSONPath to error location
        self.line = 0               # Line number
        self.column = 0             # Column number  
        self.error_type = ""        # Category of error
        self.message = ""           # Human-readable description
        self.suggestion = ""        # How to fix it
        self.context_before = ""    # Text before error
        self.context_after = ""     # Text after error
        self.recovery_attempted = False
        self.recovery_action = ""   # What recovery was tried
        self.severity = ""          # error, warning, info
```

### **Error Categories**

```python
class ErrorType(Enum):
    SYNTAX_ERROR = "syntax_error"           # Invalid JSON syntax
    MISSING_QUOTES = "missing_quotes"       # Unquoted strings/keys
    TRAILING_COMMA = "trailing_comma"       # Extra commas
    UNCLOSED_STRING = "unclosed_string"     # Missing closing quote
    MISSING_COLON = "missing_colon"         # Object key without colon
    MISSING_COMMA = "missing_comma"         # Missing separator
    INVALID_VALUE = "invalid_value"         # Invalid literal value
    NESTED_ERROR = "nested_error"           # Error in nested structure
    ENCODING_ERROR = "encoding_error"       # Character encoding issues
    STRUCTURE_ERROR = "structure_error"     # Malformed objects/arrays
```

## 🎯 **API Design**

### **Main Parsing Functions**

```python
# Basic partial parsing
def parse_partial(text: str, 
                 recovery_level: RecoveryLevel = RecoveryLevel.SKIP_FIELDS,
                 collect_errors: bool = True) -> PartialParseResult:
    """Parse with error recovery, returning partial results."""
    pass

# Advanced partial parsing with configuration
def parse_with_recovery(text: str,
                       config: PartialParseConfig) -> PartialParseResult:
    """Parse with detailed recovery configuration.""" 
    pass

# Quick utility for "get what you can"
def extract_valid_data(text: str) -> dict:
    """Simple function to extract any valid data, ignore errors."""
    result, _ = parse_partial(text, RecoveryLevel.BEST_EFFORT)
    return result.data
```

### **Configuration Options**

```python
@dataclass
class PartialParseConfig:
    recovery_level: RecoveryLevel = RecoveryLevel.SKIP_FIELDS
    max_errors: int = 100                    # Stop after N errors
    auto_quote_keys: bool = True             # Try to fix unquoted keys
    auto_quote_values: bool = True           # Try to fix unquoted string values
    remove_trailing_commas: bool = True      # Auto-remove trailing commas
    infer_missing_quotes: bool = True        # Infer string boundaries
    preserve_error_locations: bool = True    # Keep error position info
    attempt_repair: bool = True              # Try to fix vs just skip
    continue_on_fatal: bool = False          # Continue after fatal errors
```

## 🔍 **Real-World Use Cases**

### **1. Log File Processing**
```python
# Parse JSON logs even when some entries are malformed
log_entries = '''
{"timestamp": "2023-01-01", "level": "info", "message": "Started"}
{"timestamp": "2023-01-01", "level": "error", message: "Missing quotes"}
{"timestamp": "2023-01-01", "level": "info", "message": "Completed"}
'''

# Extract valid log entries, report malformed ones
valid_logs, errors = parse_partial_jsonl(log_entries)
```

### **2. API Response Tolerance**
```python
# Handle APIs that sometimes return malformed JSON
api_response = '''
{
    "status": "success",
    "data": {
        "users": [
            {"id": 1, "name": "Alice"},
            {id: 2, name: "Bob"},  # Missing quotes
            {"id": 3, "name": "Charlie"}
        ]
    },
    "meta": {count: 3}  # Missing quotes
}
'''

# Extract what's valid, report what's not
result, errors = parse_partial(api_response)
# Still get Alice and Charlie's data, Bob is skipped/repaired
```

### **3. Configuration File Tolerance**
```python
# Parse config files with some malformed sections
config_with_errors = '''
{
    "database": {
        "host": "localhost",
        "port": 5432,
        "credentials": {missing closing brace
    },
    "logging": {
        "level": "info",
        "file": "/var/log/app.log"
    }
}
'''

# Get valid config sections, warn about malformed ones
valid_config, errors = parse_partial(config_with_errors)
# Can still start app with valid logging config
```

## 🎯 **Implementation Priority**

### **Phase 1: Basic Error Recovery**
- Skip malformed fields/elements
- Collect error information
- Basic auto-quoting for unquoted keys/values

### **Phase 2: Advanced Recovery**
- Best-effort field repair
- Context-aware recovery strategies
- Template-based recovery

### **Phase 3: Intelligent Recovery**
- Statistical inference
- Pattern learning
- Semantic understanding

## 🏆 **Competitive Advantage**

This feature would make jsonshiatsu **the only JSON parser** that can:
- Extract partial data from malformed inputs
- Provide detailed error diagnostics
- Continue processing despite syntax errors
- Offer configurable recovery strategies

**Perfect for real-world scenarios** where you need resilience against:
- Malformed API responses
- Corrupted log files  
- Hand-edited configuration files
- Generated JSON with occasional syntax errors

This stays true to jsonshiatsu's core mission of handling malformed JSON while adding a **unique capability** no other parser provides.