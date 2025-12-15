"""Certification logic.

Determines if a scenario meets quality bar for certification.

Phase 2 implementation.
"""

from backend.lib.consistency import check_all_consistency, has_blocking_violations
from backend.lib.models import FilteredObjection, ObjectionType, ScenarioSheet
from backend.moderator.filter import has_structural_objections


async def check_certification(
    sheet: ScenarioSheet,
    filtered_objections: list[FilteredObjection],
) -> tuple[bool, str]:
    """
    Check if scenario can be certified.

    Certification requires:
    1. No blocking consistency violations
    2. No structural objections
    3. All required fields populated

    Args:
        sheet: The scenario sheet to certify
        filtered_objections: Filtered red team objections

    Returns:
        (can_certify, reason) tuple
    """
    # Check consistency
    violations = check_all_consistency(sheet)
    if has_blocking_violations(violations):
        return False, f"Blocking consistency violations: {len(violations)}"

    # Check for structural objections
    if has_structural_objections(filtered_objections):
        structural_count = sum(
            1 for o in filtered_objections
            if o.objection_type == ObjectionType.STRUCTURAL
        )
        return False, f"Structural objections remain: {structural_count}"

    # Check required fields
    missing_fields = _check_required_fields(sheet)
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"

    return True, "All certification checks passed"


def _check_required_fields(sheet: ScenarioSheet) -> list[str]:
    """Check that all required fields are populated."""
    missing = []

    if not sheet.stakes:
        missing.append("stakes")
    if not sheet.forces:
        missing.append("forces")
    if not sheet.terrain_weather:
        missing.append("terrain_weather")
    if not sheet.timeline:
        missing.append("timeline")

    return missing
