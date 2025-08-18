"""
Command-line interface for jsonshiatsu.
"""

import argparse
import json
import sys

import jsonshiatsu
from jsonshiatsu.security.exceptions import ParseError


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Parse non-standard JSON using jsonshiatsu",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  jsonshiatsu -f input.json
  echo '{ test: "value"}' | jsonshiatsu
  jsonshiatsu --no-fallback -f malformed.json
        """,
    )

    parser.add_argument(
        "-f",
        "--file",
        type=argparse.FileType("r"),
        default=sys.stdin,
        help="Input file (default: stdin)",
    )

    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Disable fallback to standard JSON parser",
    )

    parser.add_argument(
        "--duplicate-keys",
        action="store_true",
        help="Handle duplicate keys by creating arrays",
    )

    parser.add_argument(
        "--indent", type=int, default=2, help="JSON output indentation (default: 2)"
    )

    args = parser.parse_args()

    try:
        # Read input
        input_text = args.file.read()

        # Parse using jsonshiatsu
        result = jsonshiatsu.parse(
            input_text,
            fallback=not args.no_fallback,
            aggressive=args.duplicate_keys,
        )

        # Output formatted JSON
        print(json.dumps(result, indent=args.indent, ensure_ascii=False))

    except ParseError as e:
        print(f"Parse error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if args.file != sys.stdin:
            args.file.close()


if __name__ == "__main__":
    main()
