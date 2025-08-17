"""
Partial Error Parsing demonstration for jsonshiatsu.

This demo shows how jsonshiatsu can extract valid data from malformed JSON
instead of failing completely on the first error.
"""

from jsonshiatsu import (
    ErrorSeverity,
    ParseConfig,
    RecoveryAction,
    RecoveryLevel,
    extract_valid_data,
    parse_partial,
    parse_with_fallback,
)


def print_result(title, result):
    """Helper function to print parsing results nicely."""
    print(f"\n{title}")
    print("=" * len(title))

    print(f"✅ Extracted Data: {result.data}")
    print(f"📊 Success Rate: {result.success_rate:.1f}%")
    print(f"🔧 Recovery Actions: {len(result.recovery_actions)}")

    if result.warnings:
        print(f"⚠️  Warnings ({len(result.warnings)}):")
        for warning in result.warnings:
            print(f"   • {warning.message} (recovered)")

    if result.errors:
        print(f"❌ Errors ({len(result.errors)}):")
        for error in result.errors:
            print(f"   • {error.message} at line {error.line}")


def demo_basic_field_recovery():
    """Demonstrate basic field-level error recovery."""
    print("🚀 jsonshiatsu Partial Error Parsing Demo")
    print("=" * 40)

    # Example 1: Mixed valid and invalid fields
    malformed_object = """
    {
        "user_id": 12345,
        "name": "Alice Johnson",
        "email": broken_email_syntax,
        "phone": "555-1234",
        "settings": {invalid json here},
        "created_at": "2023-01-01",
        "tags": ["user", "active"]
    }
    """

    print("Example 1: Object with mixed valid/invalid fields")
    print("Input JSON:")
    print(malformed_object)

    result = parse_partial(malformed_object, RecoveryLevel.SKIP_FIELDS)
    print_result("Result (SKIP_FIELDS mode)", result)

    # Show what we extracted vs what failed
    print("\n📋 Analysis:")
    print("   ✅ Extracted: user_id, name, phone, created_at, tags")
    print("   ❌ Skipped: email (syntax error), settings (malformed object)")


def demo_array_recovery():
    """Demonstrate array element recovery."""
    malformed_array = """
    [
        {"id": 1, "name": "Alice", "status": "active"},
        {broken object syntax here},
        {"id": 2, "name": "Bob", "status": "inactive"},
        invalid_element,
        {"id": 3, "name": "Charlie", "status": "active"},
        {missing_closing_brace: "oops"
    ]
    """

    print("\n\nExample 2: Array with malformed elements")
    print("Input JSON:")
    print(malformed_array)

    result = parse_partial(malformed_array, RecoveryLevel.SKIP_FIELDS)
    print_result("Result (Array Recovery)", result)

    print("\n📋 Analysis:")
    print(f"   ✅ Extracted {len(result.data)} valid elements out of ~6 total")
    print("   ❌ Skipped malformed elements without losing valid data")


def demo_best_effort_recovery():
    """Demonstrate best-effort recovery with auto-repair."""
    auto_repairable = """
    {
        name: "Alice",
        age: 25,
        email: alice@domain.com,
        "tags": [tag1, tag2, active],
        "active": true,
        "score": 95.5,
    }
    """

    print("\n\nExample 3: Auto-repair common issues")
    print("Input JSON (missing quotes, trailing comma):")
    print(auto_repairable)

    result = parse_partial(auto_repairable, RecoveryLevel.BEST_EFFORT)
    print_result("Result (BEST_EFFORT mode)", result)

    print("\n🔧 Auto-repairs performed:")
    for action in result.recovery_actions:
        if action == RecoveryAction.ADDED_QUOTES:
            print("   • Added missing quotes around keys/values")
        elif action == RecoveryAction.REMOVED_COMMA:
            print("   • Removed trailing comma")


def demo_nested_recovery():
    """Demonstrate recovery in nested structures."""
    nested_malformed = """
    {
        "company": {
            "name": "TechCorp",
            "departments": [
                {
                    "name": "Engineering",
                    "head": broken_value,
                    "employees": [
                        {"id": 1, "name": "Alice"},
                        {malformed employee},
                        {"id": 2, "name": "Bob"}
                    ]
                },
                {
                    "name": "Sales",
                    "employees": [
                        {"id": 3, "name": "Charlie"}
                    ]
                }
            ],
            "metadata": {
                "founded": "2020",
                "status": active
            }
        }
    }
    """

    print("\n\nExample 4: Nested structure recovery")
    print("Input JSON (errors at multiple nesting levels):")
    print(nested_malformed[:200] + "...")

    result = parse_partial(nested_malformed, RecoveryLevel.BEST_EFFORT)
    print_result("Result (Nested Recovery)", result)

    print("\n🏗️ Structure preserved:")
    if result.data and "company" in result.data:
        company = result.data["company"]
        print(f"   • Company name: {company.get('name', 'N/A')}")
        if "departments" in company:
            print(f"   • Departments: {len(company['departments'])}")
            for dept in company["departments"]:
                if "employees" in dept:
                    print(f"     - {dept['name']}: {len(dept['employees'])} employees")


def demo_real_world_scenarios():
    """Demonstrate real-world use cases."""
    print("\n\nReal-World Scenarios")
    print("=" * 20)

    # Scenario 1: Log file processing
    print("\n📄 Scenario 1: Log File Processing")
    log_entries = """
    {"timestamp": "2023-12-01T10:00:00", "level": "info", "message": "Service started"}
    {"timestamp": "2023-12-01T10:01:00", "level": "error", message: "Missing quotes in log entry"}
    {"timestamp": "2023-12-01T10:02:00", "level": "info", "message": "Processing request"}
    """

    print("Processing JSON log entries...")

    # Parse each line separately
    valid_logs = []
    total_logs = 0
    for line in log_entries.strip().split("\n"):
        line = line.strip()
        if line:
            total_logs += 1
            data = extract_valid_data(line)
            if data:
                valid_logs.append(data)

    print(f"✅ Extracted {len(valid_logs)} valid logs out of {total_logs} total")
    print("   Valid logs preserved despite malformed entries")

    # Scenario 2: API Response tolerance
    print("\n🌐 Scenario 2: API Response Tolerance")
    api_response = """
    {
        "status": "success",
        "data": {
            "users": [
                {"id": 1, "name": "Alice", "email": "alice@example.com"},
                {id: 2, name: "Bob", email: "bob@example.com"},
                {"id": 3, "name": "Charlie", "email": "charlie@example.com"}
            ],
            "total": 3,
            "page": 1
        },
        "meta": {
            "request_id": req_12345,
            "processing_time": 45
        }
    }
    """

    result = parse_partial(api_response, RecoveryLevel.BEST_EFFORT)
    print(f"✅ API response processed with {result.success_rate:.1f}% success rate")

    if result.data and "data" in result.data and "users" in result.data["data"]:
        users = result.data["data"]["users"]
        print(f"   Extracted {len(users)} user records")
        print("   Application can continue with available data")

    # Scenario 3: Configuration file resilience
    print("\n⚙️ Scenario 3: Configuration File Resilience")
    config_with_errors = """
    {
        "database": {
            "host": "localhost",
            "port": 5432,
            "password": broken_config_value
        },
        "logging": {
            "level": "info",
            "file": "/var/log/app.log",
            "rotation": daily
        },
        "features": {
            "auth": true,
            "metrics": true
        }
    }
    """

    result = parse_partial(config_with_errors, RecoveryLevel.BEST_EFFORT)
    print(f"✅ Config processed with {result.success_rate:.1f}% success rate")

    if result.data:
        available_sections = list(result.data.keys())
        print(f"   Available config sections: {available_sections}")
        print("   Application can start with partial configuration")


def demo_convenience_functions():
    """Demonstrate convenience functions."""
    print("\n\nConvenience Functions")
    print("=" * 20)

    malformed = '{"valid": "data", broken: syntax, "more": "valid"}'

    # Quick data extraction
    print("\n🚀 Quick Data Extraction:")
    data = extract_valid_data(malformed)
    print(f"extract_valid_data(): {data}")

    # Data + errors tuple
    print("\n📊 Data + Errors Tuple:")
    data, errors = parse_with_fallback(malformed)
    print(f"Data: {data}")
    print(f"Errors: {len(errors)} errors found")

    # Full control
    print("\n🎛️ Full Control:")
    result = parse_partial(malformed, RecoveryLevel.BEST_EFFORT)
    print(f"Success rate: {result.success_rate:.1f}%")
    print(f"Recovery actions: {len(result.recovery_actions)}")
    print(f"Warnings: {len(result.warnings)}")
    print(f"Errors: {len(result.errors)}")


def demo_recovery_levels():
    """Demonstrate different recovery levels."""
    print("\n\nRecovery Levels Comparison")
    print("=" * 30)

    test_json = '{name: Alice, "age": 25, broken: syntax, "city": "NYC"}'

    levels = [
        (RecoveryLevel.STRICT, "STRICT - Fail on first error"),
        (RecoveryLevel.SKIP_FIELDS, "SKIP_FIELDS - Skip malformed fields"),
        (RecoveryLevel.BEST_EFFORT, "BEST_EFFORT - Try to repair"),
        (RecoveryLevel.EXTRACT_ALL, "EXTRACT_ALL - Get everything possible"),
    ]

    for level, description in levels:
        print(f"\n{description}:")
        try:
            result = parse_partial(test_json, level)
            print(f"   Data: {result.data}")
            print(f"   Success rate: {result.success_rate:.1f}%")
            print(f"   Errors: {len(result.errors)}, Warnings: {len(result.warnings)}")
        except Exception as e:
            print(f"   Failed: {str(e)}")


def main():
    """Run all demonstrations."""
    demo_basic_field_recovery()
    demo_array_recovery()
    demo_best_effort_recovery()
    demo_nested_recovery()
    demo_real_world_scenarios()
    demo_convenience_functions()
    demo_recovery_levels()

    print("\n\n🎉 Partial Error Parsing Demo Complete!")
    print("=" * 45)
    print("Key Benefits:")
    print("• Extract valid data instead of losing everything")
    print("• Detailed error reporting with recovery information")
    print("• Configurable recovery levels for different use cases")
    print("• Perfect for production systems handling unreliable JSON")


if __name__ == "__main__":
    main()
