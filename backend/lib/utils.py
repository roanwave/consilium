"""Utility functions for the Consilium backend."""

from typing import Any


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
