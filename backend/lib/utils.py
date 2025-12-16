"""Utility functions for the Consilium backend."""

from typing import Any


def format_number(value: Any, default: str = "0") -> str:
    """
    Safely format a number with comma separators.

    Handles values that might be:
    - Integers or floats
    - Strings with commas like "3,200"
    - Strings without commas like "3200"
    - None or invalid values

    Args:
        value: The value to format
        default: Default string if formatting fails

    Returns:
        Formatted string with comma separators

    Examples:
        >>> format_number(3200)
        '3,200'
        >>> format_number("3,200")
        '3,200'
        >>> format_number("3200")
        '3,200'
        >>> format_number(None)
        '0'
    """
    if value is None:
        return default
    try:
        # If it's already a number, format it
        if isinstance(value, (int, float)):
            return f"{int(value):,}"
        # If it's a string, remove commas and convert
        if isinstance(value, str):
            cleaned = value.replace(",", "").strip()
            return f"{int(float(cleaned)):,}"
        return default
    except (ValueError, TypeError):
        return str(value) if value else default


def safe_get(obj: Any, *keys: str, default: Any = None) -> Any:
    """
    Safely get nested attributes from dict or object.

    Works with both Pydantic models and raw dicts, navigating through
    nested structures safely.

    Args:
        obj: The object or dict to get the value from
        *keys: The sequence of keys/attributes to traverse
        default: The default value if any key is not found

    Returns:
        The value at the nested path, or default if not found

    Examples:
        >>> safe_get(sheet, 'casualty_profile', 'total_casualties', default=0)
        >>> safe_get(force, 'commander', 'name', default='Unknown')
    """
    for key in keys:
        if obj is None:
            return default
        if isinstance(obj, dict):
            obj = obj.get(key)
        else:
            obj = getattr(obj, key, None)
    return obj if obj is not None else default
