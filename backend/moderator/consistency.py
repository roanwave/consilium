"""Moderator-level consistency checking.

Wraps the lib/consistency module with additional moderator-specific logic.
"""

import copy
import logging
from typing import Any

from backend.lib.consistency import (
    check_all_consistency,
    has_blocking_violations,
    filter_violations_by_severity,
)
from backend.lib.models import ConsistencyViolation, ScenarioSheet

logger = logging.getLogger(__name__)


async def run_consistency_pass(
    sheet: ScenarioSheet,
) -> list[ConsistencyViolation]:
    """
    Run full consistency pass on the scenario.

    Includes:
    - Numerical consistency
    - Timeline consistency
    - Geography/distance consistency
    - Commander knowledge vs fog of war
    - Era/anachronism detection

    Args:
        sheet: ScenarioSheet to validate

    Returns:
        List of consistency violations found
    """
    violations = check_all_consistency(sheet)

    # Log summary
    errors = filter_violations_by_severity(violations, "error")
    warnings = filter_violations_by_severity(violations, "warning")
    logger.info(f"Consistency check: {len(errors)} errors, {len(warnings)} warnings")

    return violations


async def resolve_contradictions(
    sheet: ScenarioSheet,
    violations: list[ConsistencyViolation],
) -> tuple[ScenarioSheet, list[str]]:
    """
    Attempt to automatically resolve simple contradictions.

    Only resolves straightforward numerical issues - complex contradictions
    require expert intervention.

    Args:
        sheet: ScenarioSheet with violations
        violations: List of detected violations

    Returns:
        Tuple of (updated_sheet, list_of_resolutions_made)
    """
    # Work on a copy to avoid mutating the original
    sheet = sheet.model_copy(deep=True)
    resolutions: list[str] = []

    for violation in violations:
        resolution = _try_resolve_violation(sheet, violation)
        if resolution:
            resolutions.append(resolution)

    return sheet, resolutions


def _try_resolve_violation(
    sheet: ScenarioSheet,
    violation: ConsistencyViolation,
) -> str | None:
    """
    Try to automatically resolve a single violation.

    Args:
        sheet: ScenarioSheet to modify (mutated in place)
        violation: The violation to resolve

    Returns:
        Resolution description if resolved, None otherwise
    """
    v_type = violation.violation_type

    # Force count mismatch - adjust total_strength to match unit sum
    if v_type == "force_count_mismatch":
        return _resolve_force_count_mismatch(sheet, violation)

    # Invalid percentages - clamp to 0-100
    if v_type == "invalid_percentage":
        return _resolve_invalid_percentage(sheet, violation)

    # Other violations require human/expert intervention
    return None


def _resolve_force_count_mismatch(
    sheet: ScenarioSheet,
    violation: ConsistencyViolation,
) -> str | None:
    """Resolve force count mismatch by adjusting total_strength."""
    # Parse side_id from field like "forces.side_a"
    field = violation.field
    if not field.startswith("forces."):
        return None

    side_id = field.split(".")[1]
    if side_id not in sheet.forces:
        return None

    force = sheet.forces[side_id]
    if not force.composition:
        return None

    # Calculate correct sum
    unit_sum = sum(unit.count for unit in force.composition)
    old_total = force.total_strength

    # Update total_strength
    force.total_strength = unit_sum

    return (
        f"Auto-resolved force count mismatch for {side_id}: "
        f"adjusted total_strength from {old_total} to {unit_sum}"
    )


def _resolve_invalid_percentage(
    sheet: ScenarioSheet,
    violation: ConsistencyViolation,
) -> str | None:
    """Resolve invalid percentage by clamping to 0-100."""
    if not sheet.casualty_profile:
        return None

    field = violation.field
    if "winner_casualties_percent" in field:
        old_val = sheet.casualty_profile.winner_casualties_percent
        sheet.casualty_profile.winner_casualties_percent = min(100.0, max(0.0, old_val))
        return f"Clamped winner_casualties_percent from {old_val} to 100"

    if "loser_casualties_percent" in field:
        old_val = sheet.casualty_profile.loser_casualties_percent
        sheet.casualty_profile.loser_casualties_percent = min(100.0, max(0.0, old_val))
        return f"Clamped loser_casualties_percent from {old_val} to 100"

    return None


def is_certified_ready(violations: list[ConsistencyViolation]) -> bool:
    """
    Check if the scenario is ready for certification.

    A scenario is certifiable if it has no blocking errors.
    Warnings are acceptable.

    Args:
        violations: List of consistency violations

    Returns:
        True if scenario can be certified
    """
    return not has_blocking_violations(violations)


def summarize_violations(violations: list[ConsistencyViolation]) -> str:
    """
    Create a human-readable summary of violations.

    Args:
        violations: List of violations

    Returns:
        Summary string
    """
    if not violations:
        return "No consistency violations found."

    errors = filter_violations_by_severity(violations, "error")
    warnings = filter_violations_by_severity(violations, "warning")

    lines = [
        f"Consistency Check: {len(errors)} errors, {len(warnings)} warnings",
        "",
    ]

    if errors:
        lines.append("ERRORS (must fix):")
        for v in errors:
            lines.append(f"  - [{v.field}] {v.description}")

    if warnings:
        lines.append("")
        lines.append("WARNINGS (should review):")
        for v in warnings:
            lines.append(f"  - [{v.field}] {v.description}")

    return "\n".join(lines)
