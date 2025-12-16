"""Output retrieval endpoint."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from backend.lib.models import ScenarioOutputResponse, SessionStatus
from backend.lib.persistence import SessionStore, get_session_store

router = APIRouter()


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

    # TODO: Phase 3 - Generate full narrative from sheet
    narrative = ""

    return ScenarioOutputResponse(
        session_id=session.session_id,
        status=session.status,
        sheet=session.sheet,
        narrative=narrative,
        total_token_usage=session.total_token_usage,
    )
