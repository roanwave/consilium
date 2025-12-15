"""Delta application logic.

Applies approved delta requests to the ScenarioSheet.

Phase 2 implementation.
"""

from typing import Any

from backend.lib.models import DeltaOperation, DeltaRequest, ScenarioSheet


def apply_delta(
    sheet: ScenarioSheet,
    delta: DeltaRequest,
) -> tuple[bool, str]:
    """
    Apply a single delta to the sheet.

    Args:
        sheet: The sheet to modify
        delta: The delta request

    Returns:
        (success, message) tuple
    """
    try:
        field_path = delta.field.split(".")
        target = sheet

        # Navigate to parent of target field
        for part in field_path[:-1]:
            if hasattr(target, part):
                target = getattr(target, part)
            elif isinstance(target, dict):
                target = target[part]
            else:
                return False, f"Cannot navigate to {delta.field}"

        final_field = field_path[-1]

        if delta.operation == DeltaOperation.SET:
            if hasattr(target, final_field):
                setattr(target, final_field, delta.value)
            elif isinstance(target, dict):
                target[final_field] = delta.value
            else:
                return False, f"Cannot set {delta.field}"

        elif delta.operation == DeltaOperation.APPEND:
            current = getattr(target, final_field, None) or target.get(final_field)
            if isinstance(current, list):
                current.append(delta.value)
            else:
                return False, f"Cannot append to non-list field {delta.field}"

        elif delta.operation == DeltaOperation.MODIFY:
            # Modify requires value to be a dict with partial updates
            current = getattr(target, final_field, None) or target.get(final_field)
            if isinstance(current, dict) and isinstance(delta.value, dict):
                current.update(delta.value)
            else:
                return False, f"Cannot modify {delta.field}"

        return True, "Applied"

    except Exception as e:
        return False, str(e)


def apply_all_deltas(
    sheet: ScenarioSheet,
    deltas: list[DeltaRequest],
    modified_by: str = "moderator",
) -> tuple[ScenarioSheet, list[dict[str, Any]]]:
    """
    Apply all deltas to the sheet.

    Returns sheet and list of results for each delta.
    """
    results = []

    for delta in deltas:
        success, message = apply_delta(sheet, delta)
        results.append({
            "field": delta.field,
            "operation": delta.operation.value,
            "success": success,
            "message": message,
            "rationale": delta.rationale,
        })

    # Increment version if any deltas were applied
    if any(r["success"] for r in results):
        sheet.increment_version(modified_by)

    return sheet, results
