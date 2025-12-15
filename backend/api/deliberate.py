"""Deliberation SSE endpoint."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from backend.lib.models import SessionStatus
from backend.lib.persistence import SessionStore, get_session_store
from backend.lib.streaming import EventBuilder, SSEStream, format_sse

router = APIRouter()


@router.get("/deliberate/{session_id}")
async def deliberate(
    session_id: UUID,
    last_event_id: str | None = None,
    store: SessionStore = Depends(get_session_store),
) -> EventSourceResponse:
    """
    Start or resume deliberation via SSE stream.

    Query params:
        last_event_id: For reconnection, the last received event ID
    """
    session = await store.get(session_id)

    if session.status not in [SessionStatus.DELIBERATING, SessionStatus.CERTIFIED]:
        raise HTTPException(
            status_code=400,
            detail=f"Session cannot deliberate in state: {session.status.value}",
        )

    async def event_generator():
        """Generate SSE events for deliberation."""
        builder = EventBuilder(session)

        # Emit session start
        yield format_sse(builder.session_start())

        # TODO: Phase 2 - Implement actual deliberation loop
        # For now, emit a progress message and end
        yield format_sse(builder.progress("Deliberation not yet implemented", 0))

        # Emit session end
        yield format_sse(builder.session_end(success=True))

    return EventSourceResponse(event_generator())
