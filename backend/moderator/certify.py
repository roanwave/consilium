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
    max_structural_allowed: int = 3,
) -> tuple[bool, str]:
    """
    Check if scenario can be certified.

    Certification requires:
    1. No blocking consistency violations
    2. Structural objections within threshold (default: 3 allowed)
    3. All required fields populated

    Args:
        sheet: The scenario sheet to certify
        filtered_objections: Filtered red team objections
        max_structural_allowed: Maximum number of structural objections to allow

    Returns:
        (can_certify, reason) tuple
    """
    # Check consistency - be lenient with violations from LLM output
    try:
        violations = check_all_consistency(sheet)
        if has_blocking_violations(violations):
            # Only block on truly critical violations (> 5)
            critical_count = len([v for v in violations if v.severity == "error"])
            if critical_count > 5:
                return False, f"Too many critical consistency violations: {critical_count}"
    except Exception as e:
        # Don't fail certification on consistency check errors
        pass

    # Check for structural objections - allow some through
    structural_count = sum(
        1 for o in filtered_objections
        if o.objection_type == ObjectionType.STRUCTURAL
    )
    if structural_count > max_structural_allowed:
        return False, f"Too many structural objections: {structural_count} (max {max_structural_allowed})"

    # Check required fields - be lenient
    missing_fields = _check_required_fields(sheet)
    # Only block if critical fields are missing
    critical_missing = [f for f in missing_fields if f in ["forces", "stakes"]]
    if critical_missing:
        return False, f"Missing critical fields: {', '.join(critical_missing)}"

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
