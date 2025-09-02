"""
Base parser functionality shared between engine and streaming parsers.
"""

from typing import TYPE_CHECKING, Any, Optional

from ..security.limits import LimitValidator
from .error_handling import ErrorContextBuilder, ErrorReporterImpl
from .tokenizer import Token

if TYPE_CHECKING:
    pass


class BaseParserMixin:
    """Common parsing functionality shared between different parsers."""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Ensure proper interface compliance for subclasses."""
        super().__init_subclass__(**kwargs)
        # Could add interface validation here in the future

    def create_error_context(self, original_text: str = "") -> Any:
        """Create error context from current parser state."""
        try:
            # Try to get position from current token if available
            position = 0
            if hasattr(self, "current_token"):
                token = self.current_token()
                position = getattr(token, "position", 0)
            elif hasattr(self, "position"):
                position = self.position

            return ErrorContextBuilder.build_context(position, original_text)
        except Exception:
            return ErrorContextBuilder.build_context(0, original_text)

    def create_error_reporter(
        self, original_text: str = "", include_context: bool = True
    ) -> ErrorReporterImpl:
        """Create an error reporter for this parser."""
        return ErrorReporterImpl(original_text, include_context)

    def parse_number_token(self, token: Token) -> Any:
        """Parse a number token into int or float."""
        value = token.value
        if "." in value or "e" in value.lower():
            return float(value)
        return int(value)

    def parse_boolean_token(self, token: Token) -> bool:
        """Parse a boolean token."""
        return token.value == "true"

    def parse_null_token(self, token: Token) -> Optional[Any]:  # pylint: disable=unused-argument
        """Parse a null token."""
        return None

    def handle_duplicate_key(
        self, obj: dict[str, Any], key: str, value: Any, config_duplicate_keys: bool
    ) -> None:
        """Handle duplicate key based on configuration."""
        if key in obj:
            if config_duplicate_keys:
                if not isinstance(obj[key], list):
                    obj[key] = [obj[key]]
                obj[key].append(value)
            else:
                obj[key] = value
        else:
            obj[key] = value

    def validate_and_enter_structure(self, validator: Optional[LimitValidator]) -> None:
        """Validate and enter a structure if validator exists."""
        if validator:
            validator.enter_structure()

    def validate_and_exit_structure(self, validator: Optional[LimitValidator]) -> None:
        """Validate and exit a structure if validator exists."""
        if validator:
            validator.exit_structure()

    def init_empty_array(self) -> list[Any]:
        """Initialize an empty array."""
        return []

    def init_empty_object(self) -> dict[str, Any]:
        """Initialize an empty object."""
        return {}
