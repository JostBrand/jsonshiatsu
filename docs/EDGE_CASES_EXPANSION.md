# jsonshiatsu Edge Cases & Scope Expansion

## 🌐 **Format Support Edge Cases**

### 1. **Extended JSON Variants**
```python
# JSON-LD (Linked Data)
{
  "@context": "https://schema.org/",
  "@type": "Person",
  "name": "John Doe"
}

# GeoJSON with custom extensions
{
  "type": "FeatureCollection",
  "bbox": [-180, -90, 180, 90],
  "features": [...],
  "custom:metadata": "value"  # Namespaced properties
}

# MongoDB Extended JSON
{
  "_id": {"$oid": "507f1f77bcf86cd799439011"},
  "date": {"$date": "2023-01-01T00:00:00Z"},
  "binary": {"$binary": {"base64": "SGVsbG8=", "subType": "00"}}
}
```

### 2. **Configuration File Formats**
```python
# HOCON (Human-Optimized Config Object Notation)
{
  database {
    host = localhost
    port = 5432
    credentials = ${?DATABASE_URL}  # Environment variable substitution
  }
  include "database.conf"  # File inclusion
}

# YAML-like JSON
{
  # Multi-line strings with YAML syntax
  description: |
    This is a multi-line
    string that preserves
    line breaks
  
  # Anchors and references
  default: &default_config
    timeout: 30
  
  production: 
    <<: *default_config  # Merge reference
    timeout: 60
}

# Terraform JSON with interpolation
{
  "variable": {
    "region": {
      "default": "us-west-2"
    }
  },
  "resource": {
    "aws_instance": {
      "web": {
        "ami": "${var.region == \"us-west-2\" ? \"ami-123\" : \"ami-456\"}"
      }
    }
  }
}
```

## 🔢 **Data Type Edge Cases**

### 3. **Extended Number Formats**
```python
# Scientific notation variants
{
  "planck": 6.62607015E-34,
  "avogadro": 6.02214076e+23,
  "hex": 0xFF,           # Hexadecimal
  "octal": 0o777,        # Octal  
  "binary": 0b1010,      # Binary
  "big_int": 123456789012345678901234567890n,  # BigInt
  "infinity": Infinity,
  "neg_infinity": -Infinity,
  "not_a_number": NaN
}

# Currency and measurement units
{
  "price": "$19.99",
  "weight": "10.5kg", 
  "temperature": "23.5°C",
  "percentage": "85.3%",
  "fraction": "3/4",
  "range": "10-20"
}
```

### 4. **Date/Time Variants**
```python
{
  "iso_date": "2023-12-25T10:30:00.000Z",
  "rfc_date": "Mon, 25 Dec 2023 10:30:00 GMT",
  "unix_timestamp": 1703505000,
  "human_date": "Dec 25, 2023",
  "relative_date": "2 days ago",
  "time_only": "10:30 AM",
  "duration": "PT2H30M",  # ISO 8601 duration
  "cron": "0 30 10 * * MON-FRI"  # Cron expression
}
```

### 5. **Complex Data Structures**
```python
{
  # Sets (represented as arrays with unique constraint)
  "unique_items": [1, 2, 3],  # with set semantics
  
  # Tuples (fixed-length arrays)
  "coordinates": (40.7128, -74.0060),  # with tuple semantics
  
  # Ordered dictionaries
  "ordered_map": OrderedDict([("first", 1), ("second", 2)]),
  
  # Multi-dimensional arrays
  "matrix": [[1, 2], [3, 4]],
  
  # Sparse arrays
  "sparse": {0: "first", 5: "sixth", 10: "eleventh"},
  
  # Nested references
  "self_ref": {"parent": "$.root", "child": "$[0].nested"}
}
```

## 🛡️ **Error Recovery Edge Cases**

### 6. **Advanced Error Recovery**
```python
# Partial parsing with error collection
{
  "valid_field": "works",
  "broken_field": {missing_quote: value},  # Continue parsing after error
  "another_valid": true
}

# Multiple JSON documents in one stream
{"doc1": "value1"}
{"doc2": "value2"}  # JSONL/NDJSON support
{"doc3": "value3"}

# Corrupted data recovery
{
  "field1": "value1",,  # Extra comma
  "field2": "value2"
  "field3"  # Missing colon and value
  "field4": "value4"
}

# Encoding error recovery
{
  "text": "Hello\x00World",  # Null bytes
  "unicode": "Caf\xE9",     # Invalid UTF-8
  "mixed": "ASCII + 中文"    # Mixed encoding
}
```

### 7. **Incremental Parsing**
```python
# Stream parsing with partial updates
parser = IncrementalParser()
parser.feed('{"users": [')
parser.feed('{"id": 1, "name": "Alice"},')
parser.feed('{"id": 2, "name": "Bob"}')
parser.feed(']}')
result = parser.get_result()

# Real-time data streams
{
  "timestamp": "2023-01-01T00:00:00Z",
  "data": {...},
  "continuation": "next_chunk_id"  # For paginated APIs
}
```

## 🌍 **Internationalization Edge Cases**

### 8. **Global Format Support**
```python
{
  # RTL language support
  "arabic": "مرحبا بالعالم",
  "hebrew": "שלום עולם",
  
  # Different number formats
  "european_decimal": "1.234,56",    # European decimal separator
  "indian_lakh": "12,34,567",        # Indian number grouping
  "chinese_numbers": "一千二百三十四",  # Chinese numerals
  
  # Date formats by locale
  "us_date": "12/25/2023",
  "eu_date": "25/12/2023", 
  "iso_week": "2023-W52-1",
  
  # Currency by locale
  "usd": "$1,234.56",
  "eur": "€1.234,56",
  "jpy": "¥123,456",
  "btc": "₿0.00123456"
}
```

### 9. **Encoding & Character Set Edge Cases**
```python
{
  # Different encodings
  "utf8": "Hello 🌍",
  "latin1": "Café",
  "ascii_safe": "Hello World",
  
  # Escaped unicode variants
  "unicode_escape": "\u0048\u0065\u006C\u006C\u006F",
  "html_entities": "&lt;div&gt;Hello&lt;/div&gt;",
  "url_encoded": "Hello%20World%21",
  "base64": "SGVsbG8gV29ybGQ=",
  
  # Control characters
  "with_tabs": "Column1\tColumn2\tColumn3",
  "with_newlines": "Line1\nLine2\nLine3",
  "bell_char": "Alert!\a",
  "null_terminated": "String\0End"
}
```

## 🔗 **Real-World API Edge Cases**

### 10. **Common API Response Patterns**
```python
# GraphQL responses
{
  "data": {
    "user": {
      "id": "123",
      "name": "Alice"
    }
  },
  "errors": [
    {
      "message": "Field 'email' is deprecated",
      "path": ["user", "email"],
      "extensions": {"code": "DEPRECATED_FIELD"}
    }
  ]
}

# Envelope patterns
{
  "success": true,
  "data": {...},
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total": 100,
    "has_more": true
  },
  "metadata": {
    "request_id": "req_123",
    "processing_time_ms": 45
  }
}

# Webhook payloads
{
  "event": "user.created",
  "timestamp": 1703505000,
  "data": {...},
  "signature": "sha256=abc123...",
  "delivery_id": "delivery_123"
}

# Server-Sent Events
data: {"event": "update", "data": {...}}
event: custom-event
id: 12345
retry: 10000
```

### 11. **Database Export Formats**
```python
# SQL result sets
{
  "columns": ["id", "name", "email"],
  "rows": [
    [1, "Alice", "alice@example.com"],
    [2, "Bob", "bob@example.com"]
  ],
  "affected_rows": 2
}

# NoSQL document exports
{
  "_id": ObjectId("..."),
  "_version": 1,
  "_metadata": {
    "created_at": ISODate("..."),
    "updated_at": ISODate("...")
  },
  "data": {...}
}

# Time series data
{
  "metric": "cpu_usage",
  "tags": {"host": "server1", "region": "us-west"},
  "points": [
    [1703505000, 45.2],
    [1703505060, 47.1],
    [1703505120, 43.8]
  ]
}
```

## 🔒 **Security & Validation Edge Cases**

### 12. **Advanced Security Scenarios**
```python
# Schema validation
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "name": {"type": "string", "minLength": 1},
    "age": {"type": "integer", "minimum": 0, "maximum": 150}
  },
  "required": ["name"]
}

# Content Security Policy
{
  "allowed_origins": ["https://*.example.com"],
  "max_depth": 10,
  "forbidden_keys": ["__proto__", "constructor"],
  "sanitization_rules": {
    "strip_html": true,
    "escape_sql": true
  }
}

# Digital signatures
{
  "data": {...},
  "signature": {
    "algorithm": "RS256",
    "value": "eyJ...",
    "keyid": "key-123",
    "timestamp": 1703505000
  }
}
```

### 13. **Content Filtering & Transformation**
```python
# PII detection and masking
{
  "user_data": {
    "name": "John Doe",
    "email": "j***@***.com",        # Masked email
    "ssn": "***-**-1234",           # Masked SSN
    "credit_card": "**** **** **** 1234"  # Masked credit card
  }
}

# Data anonymization
{
  "user_id": "hash:a1b2c3d4",  # Hashed identifier
  "location": "US-CA",         # Generalized location
  "age_range": "25-35"         # Age bucket instead of exact age
}
```

## 🚀 **Performance & Scale Edge Cases**

### 14. **Big Data Scenarios**
```python
# Very large arrays
{
  "data": [/* 10 million items */],
  "chunked": true,
  "chunk_size": 10000,
  "total_chunks": 1000
}

# Streaming processing markers
{
  "stream_id": "stream_123",
  "sequence": 1547,
  "batch": [
    {"timestamp": 1703505000, "value": 42},
    {"timestamp": 1703505001, "value": 43}
  ],
  "checkpoint": "offset:1547:hash:abc123"
}

# Memory-mapped data references
{
  "data_ref": "mmap://file.dat:offset:1024:length:2048",
  "compression": "gzip",
  "encoding": "binary"
}
```

### 15. **Distributed System Edge Cases**
```python
# Vector clocks for distributed systems
{
  "data": {...},
  "vector_clock": {
    "node_a": 5,
    "node_b": 3,
    "node_c": 7
  },
  "causality": "happens_before"
}

# Conflict resolution
{
  "base_version": {...},
  "conflicts": [
    {
      "path": "$.user.name",
      "values": ["Alice", "Alicia"],
      "timestamps": [1703505000, 1703505010]
    }
  ],
  "resolution_strategy": "last_writer_wins"
}
```

## 🔧 **Integration Edge Cases**

### 16. **Cross-Language Compatibility**
```python
# Python-specific types
{
  "decimal": Decimal("19.99"),      # Exact decimal arithmetic
  "datetime": datetime(2023, 12, 25),
  "uuid": UUID("123e4567-e89b-12d3-a456-426614174000"),
  "bytes": b"binary data",
  "frozenset": frozenset([1, 2, 3])
}

# Language-agnostic type hints
{
  "value": 42,
  "__type__": "int64",
  "__metadata__": {
    "source_language": "python",
    "serialization_version": "1.0"
  }
}
```

### 17. **Protocol Integration**
```python
# gRPC JSON representation
{
  "name": "CreateUser",
  "request": {
    "user": {
      "name": "Alice",
      "email": "alice@example.com"
    }
  },
  "@type": "type.googleapis.com/myservice.CreateUserRequest"
}

# Protocol Buffers Any type
{
  "@type": "type.googleapis.com/google.protobuf.Value",
  "value": {...}
}

# Message queue formats
{
  "headers": {
    "message-id": "msg_123",
    "correlation-id": "corr_456",
    "content-type": "application/json"
  },
  "body": {...},
  "routing_key": "user.events.created"
}
```

## 🎯 **Implementation Priority**

### **High Impact (Immediate Value)**
1. **Extended number formats** (hex, binary, infinity, NaN)
2. **Advanced error recovery** with partial parsing
3. **JSONL/NDJSON streaming** support
4. **Date/time format flexibility**
5. **Encoding detection and conversion**

### **Medium Impact (Significant Value)**
1. **Configuration file format support** (HOCON, extended JSON)
2. **Schema validation integration**
3. **Incremental/streaming parsing**
4. **Internationalization support**
5. **Common API pattern recognition**

### **Future Expansion (Specialized Use Cases)**
1. **Database export format support**
2. **Distributed system features**
3. **Cross-language type compatibility**
4. **Advanced security features**
5. **Big data processing capabilities**

## 🚀 **Strategic Benefits**

Adding these edge cases would position jsonshiatsu as:
- **The most comprehensive JSON parser** in the Python ecosystem
- **Enterprise-ready** for complex real-world scenarios
- **Future-proof** for emerging JSON use cases
- **Developer-friendly** with intelligent error recovery
- **Globally compatible** with international formats

Each edge case addresses real-world pain points that developers encounter when working with diverse JSON sources, making jsonshiatsu an indispensable tool for modern applications.