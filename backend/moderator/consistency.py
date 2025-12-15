"""Moderator-level consistency checking.

Wraps the lib/consistency module with additional moderator-specific logic.

Phase 2 implementation.
"""

from backend.lib.consistency import check_all_consistency
from backend.lib.models import ConsistencyViolation, ScenarioSheet


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
    """
    return check_all_consistency(sheet)


async def resolve_contradictions(
    sheet: ScenarioSheet,
    violations: list[ConsistencyViolation],
) -> tuple[ScenarioSheet, list[str]]:
    """
    Attempt to automatically resolve simple contradictions.

    Returns updated sheet and list of resolutions made.
    """
    # TODO: Phase 2 - Implement resolution logic
    return sheet, []
