"""Output retrieval endpoint."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from backend.lib.models import ScenarioOutputResponse, SessionStatus
from backend.lib.persistence import SessionStore, get_session_store

router = APIRouter()


def _synthesize_narrative(session) -> str:
    """
    Synthesize narrative from expert contributions.

    Collects narrative_fragment from each expert contribution across all rounds
    and combines them into a coherent battle narrative.
    """
    fragments = []

    # Collect narrative fragments from all rounds
    for round_data in session.rounds:
        for contribution in round_data.consilium_contributions:
            if contribution.narrative_fragment:
                fragments.append({
                    "expert": contribution.expert,
                    "fragment": contribution.narrative_fragment.strip()
                })

    if not fragments:
        return ""

    # Build narrative sections
    sections = []

    # Group by expert for better narrative structure
    expert_order = [
        "strategist",   # Strategic context first
        "chronicler",   # Historical context
        "herald",       # Forces and human element
        "geographer",   # Terrain
        "tactician",    # Battle flow
        "commander",    # Command decisions
        "surgeon",      # Casualties
        "armorer",      # Equipment
        "logistician",  # Supply
    ]

    # Add fragments in order
    seen_experts = set()
    for expert in expert_order:
        for frag in fragments:
            if frag["expert"] == expert and expert not in seen_experts:
                sections.append(frag["fragment"])
                seen_experts.add(expert)

    # Add any remaining fragments not in the order list
    for frag in fragments:
        if frag["expert"] not in seen_experts:
            sections.append(frag["fragment"])

    return "\n\n".join(sections)


@router.get("/output/{session_id}", response_model=ScenarioOutputResponse)
async def get_output(
    session_id: UUID,
    store: SessionStore = Depends(get_session_store),
) -> ScenarioOutputResponse:
    """
    Get the final scenario output.

    Only available after deliberation is certified.
    """
    session = await store.get(session_id)

    # Allow both certified and failed - user should see what was generated
    if session.status not in [SessionStatus.CERTIFIED, SessionStatus.FAILED]:
        raise HTTPException(
            status_code=400,
            detail=f"Deliberation not complete. Status: {session.status.value}",
        )

    if not session.sheet:
        raise HTTPException(
            status_code=500,
            detail="Session is certified but has no sheet",
        )

    # Synthesize narrative from expert contributions
    narrative = _synthesize_narrative(session)

    return ScenarioOutputResponse(
        session_id=session.session_id,
        status=session.status,
        sheet=session.sheet,
        narrative=narrative,
        total_token_usage=session.total_token_usage,
    )
