"""Red team objection filtering.

Classifies objections into structural, refinable, cosmetic, or dismissed.

Phase 2 implementation.
"""

from backend.lib.models import (
    FilteredObjection,
    ObjectionType,
    RedTeamObjection,
    ScenarioSheet,
)


async def filter_objections(
    objections: list[RedTeamObjection],
    sheet: ScenarioSheet,
) -> list[FilteredObjection]:
    """
    Filter and classify red team objections.

    Classifications:
    - STRUCTURAL: Requires scenario rewrite
    - REFINABLE: Can be addressed in next round
    - COSMETIC: Minor wording issues
    - DISMISSED: Not a valid objection

    Args:
        objections: Raw objections from red team
        sheet: Current scenario sheet for context

    Returns:
        List of filtered objections with classifications
    """
    filtered = []

    for objection in objections:
        # TODO: Phase 2 - Implement intelligent classification
        # For now, default to REFINABLE
        filtered.append(
            FilteredObjection(
                original=objection,
                objection_type=ObjectionType.REFINABLE,
                moderator_notes="Classification not yet implemented",
                action_required="Address in next round",
            )
        )

    return filtered


def get_objection_breakdown(
    filtered: list[FilteredObjection],
) -> dict[str, int]:
    """Get count of objections by type."""
    breakdown = {t.value: 0 for t in ObjectionType}
    for obj in filtered:
        breakdown[obj.objection_type.value] += 1
    return breakdown


def has_structural_objections(filtered: list[FilteredObjection]) -> bool:
    """Check if any objections are structural."""
    return any(obj.objection_type == ObjectionType.STRUCTURAL for obj in filtered)
