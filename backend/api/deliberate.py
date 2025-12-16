"""Deliberation SSE endpoint."""

import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from backend.config import get_settings
from backend.lib.llm import LLMClient, get_llm_client
from backend.lib.models import SessionStatus
from backend.lib.persistence import SessionStore, get_session_store
from backend.lib.streaming import format_sse, format_sse_simple
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
        settings = get_settings()
        llm_client = LLMClient()

        # Queue for merging engine events with heartbeats
        event_queue: asyncio.Queue = asyncio.Queue()
        deliberation_done = asyncio.Event()

        async def heartbeat_task():
            """Send periodic heartbeats while deliberation is running."""
            try:
                while not deliberation_done.is_set():
                    await asyncio.sleep(HEARTBEAT_INTERVAL)
                    if not deliberation_done.is_set():
                        await event_queue.put(("heartbeat", None))
            except asyncio.CancelledError:
                pass

        async def deliberation_task():
            """Run deliberation and queue events."""
            try:
                await llm_client._ensure_clients()

                engine = DeliberationEngine(
                    session=session,
                    llm_client=llm_client,
                )

                session.status = SessionStatus.DELIBERATING
                await store.save(session)

                async for event in engine.run():
                    await event_queue.put(("event", event))

                await event_queue.put(("done", None))
            except Exception as e:
                await event_queue.put(("error", e))
            finally:
                deliberation_done.set()

        # Start both tasks
        heartbeat = asyncio.create_task(heartbeat_task())
        deliberation = asyncio.create_task(deliberation_task())

        try:
            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    logger.info(f"Client disconnected from session {session_id}")
                    break

                try:
                    msg_type, payload = await asyncio.wait_for(
                        event_queue.get(),
                        timeout=HEARTBEAT_INTERVAL + 5
                    )
                except asyncio.TimeoutError:
                    # Safety timeout - send heartbeat
                    yield format_sse_simple("heartbeat", {"message": "Processing..."})
                    continue

                if msg_type == "heartbeat":
                    yield format_sse_simple("heartbeat", {"message": "Processing..."})

                elif msg_type == "event":
                    event = payload
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

                elif msg_type == "error":
                    logger.exception(f"Deliberation error for session {session_id}")
                    yield format_sse_simple(
                        "error",
                        {"error": str(payload), "type": type(payload).__name__}
                    )
                    break

                elif msg_type == "done":
                    break

        finally:
            # Cleanup
            deliberation_done.set()
            heartbeat.cancel()
            try:
                await heartbeat
            except asyncio.CancelledError:
                pass
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
