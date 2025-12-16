"""Deliberation SSE endpoint."""

import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from backend.lib.llm import LLMClient
from backend.lib.models import SessionStatus
from backend.lib.persistence import SessionStore, get_session_store
from backend.lib.streaming import format_sse
from backend.orchestrator.engine import DeliberationEngine

HEARTBEAT_INTERVAL = 10  # seconds

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/deliberate/{session_id}")
async def deliberate(
    session_id: UUID,
    request: Request,
    store: SessionStore = Depends(get_session_store),
) -> EventSourceResponse:
    """
    Start or resume deliberation via SSE stream.

    Supports reconnection via Last-Event-ID header.
    """
    session = await store.get(session_id)

    # Validate session state
    if session.status == SessionStatus.INTERROGATING:
        raise HTTPException(
            status_code=400,
            detail="Submit answers first via POST /api/scenario/{session_id}/answers",
        )

    if session.status in [SessionStatus.CERTIFIED, SessionStatus.FAILED]:
        raise HTTPException(
            status_code=400,
            detail=f"Deliberation already complete. Status: {session.status.value}",
        )

    # Check for reconnection
    last_event_id = request.headers.get("Last-Event-ID")
    start_sequence = int(last_event_id) + 1 if last_event_id else 0

    async def event_generator():
        """Generate SSE events for deliberation with heartbeat keep-alive."""
        llm_client = LLMClient()

        # Heartbeat SSE format - must include event_type in data for frontend
        def make_heartbeat() -> str:
            return f"event: heartbeat\ndata: {json.dumps({'event_type': 'heartbeat', 'message': 'Processing...'})}\n\n"

        try:
            await llm_client._ensure_clients()

            engine = DeliberationEngine(
                session=session,
                llm_client=llm_client,
            )

            session.status = SessionStatus.DELIBERATING
            await store.save(session)

            # Create async iterator from engine
            engine_iter = engine.run().__aiter__()
            last_event_time = asyncio.get_event_loop().time()

            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    logger.info(f"Client disconnected from session {session_id}")
                    break

                try:
                    # Wait for next event with timeout for heartbeat
                    event = await asyncio.wait_for(
                        engine_iter.__anext__(),
                        timeout=HEARTBEAT_INTERVAL
                    )
                    last_event_time = asyncio.get_event_loop().time()

                    # Skip events before reconnection point
                    if event.sequence < start_sequence:
                        continue

                    yield format_sse(event)

                    # Persist session after major state changes
                    if event.event_type in [
                        "round_end",
                        "certified",
                        "certification_failed",
                        "session_end",
                    ]:
                        await store.save(session)

                except asyncio.TimeoutError:
                    # No event in HEARTBEAT_INTERVAL seconds - send heartbeat
                    logger.debug(f"Sending heartbeat for session {session_id}")
                    yield make_heartbeat()

                except StopAsyncIteration:
                    # Engine finished
                    logger.info(f"Deliberation complete for session {session_id}")
                    break

        except Exception as e:
            logger.exception(f"Deliberation error for session {session_id}")
            error_data = json.dumps({
                "event_type": "error",
                "error": str(e),
                "type": type(e).__name__
            })
            yield f"event: error\ndata: {error_data}\n\n"

        finally:
            await llm_client.close()

    return EventSourceResponse(event_generator())


@router.post("/deliberate/{session_id}/cancel")
async def cancel_deliberation(
    session_id: UUID,
    store: SessionStore = Depends(get_session_store),
) -> dict:
    """
    Cancel an in-progress deliberation.

    Note: This sets a flag - actual cancellation happens on next event check.
    """
    session = await store.get(session_id)

    if session.status != SessionStatus.DELIBERATING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel - session is not deliberating. Status: {session.status.value}",
        )

    session.status = SessionStatus.FAILED
    await store.save(session)

    return {
        "session_id": str(session_id),
        "status": "cancelled",
        "message": "Deliberation cancelled",
    }
