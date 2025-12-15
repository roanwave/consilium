"""SSE streaming helpers for Consilium.

Provides utilities for Server-Sent Events with sequencing and state tracking.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, AsyncIterator, Callable
from uuid import uuid4

from backend.lib.models import ScenarioSheet, SessionState, SSEEvent, TokenUsage

logger = logging.getLogger(__name__)


# =============================================================================
# Event Types
# =============================================================================


class EventType:
    """SSE event type constants."""

    # Session lifecycle
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    SESSION_ERROR = "session_error"

    # Interrogation
    INTERROGATION_START = "interrogation_start"
    INTERROGATION_COMPLETE = "interrogation_complete"

    # Deliberation
    ROUND_START = "round_start"
    ROUND_END = "round_end"

    # Expert events
    EXPERT_START = "expert_start"
    EXPERT_CHUNK = "expert_chunk"
    EXPERT_CONTRIBUTION = "expert_contribution"
    EXPERT_ERROR = "expert_error"

    # Red team events
    REDTEAM_START = "redteam_start"
    REDTEAM_OBJECTION = "redteam_objection"
    REDTEAM_COMPLETE = "redteam_complete"

    # Moderator events
    MODERATOR_SYNTHESIS = "moderator_synthesis"
    MODERATOR_FILTER = "moderator_filter"
    MODERATOR_DELTA = "moderator_delta"

    # Certification
    CERTIFIED = "certified"
    CERTIFICATION_FAILED = "certification_failed"

    # Progress
    PROGRESS = "progress"
    HEARTBEAT = "heartbeat"


# =============================================================================
# Event Builder
# =============================================================================


class EventBuilder:
    """Builder for SSE events with automatic sequencing."""

    def __init__(self, session: SessionState):
        self.session = session

    def _get_sheet_info(self) -> tuple[int, str]:
        """Get current sheet version and hash."""
        if self.session.sheet:
            return self.session.sheet.version, self.session.sheet.consistency_hash
        return 0, ""

    def build(
        self,
        event_type: str,
        data: dict[str, Any] | None = None,
        token_usage: TokenUsage | None = None,
    ) -> SSEEvent:
        """Build an SSE event with proper sequencing."""
        sheet_version, sheet_hash = self._get_sheet_info()

        return SSEEvent(
            event_id=str(uuid4()),
            sequence=self.session.next_sse_sequence(),
            event_type=event_type,
            data=data or {},
            sheet_version=sheet_version,
            sheet_hash=sheet_hash,
            token_usage=token_usage,
            timestamp=datetime.utcnow(),
        )

    def session_start(self) -> SSEEvent:
        """Build session start event."""
        return self.build(
            EventType.SESSION_START,
            {
                "session_id": str(self.session.session_id),
                "status": self.session.status.value,
            },
        )

    def session_end(self, success: bool = True) -> SSEEvent:
        """Build session end event."""
        return self.build(
            EventType.SESSION_END,
            {
                "success": success,
                "status": self.session.status.value,
                "total_tokens": self.session.total_token_usage.total_tokens,
            },
            self.session.total_token_usage,
        )

    def session_error(self, error: str, details: dict[str, Any] | None = None) -> SSEEvent:
        """Build session error event."""
        return self.build(
            EventType.SESSION_ERROR,
            {"error": error, "details": details or {}},
        )

    def round_start(self, round_number: int) -> SSEEvent:
        """Build round start event."""
        return self.build(
            EventType.ROUND_START,
            {"round": round_number, "max_rounds": self.session.max_rounds},
        )

    def round_end(self, round_number: int, certified: bool = False) -> SSEEvent:
        """Build round end event."""
        return self.build(
            EventType.ROUND_END,
            {"round": round_number, "certified": certified},
        )

    def expert_start(self, expert: str, chamber: str) -> SSEEvent:
        """Build expert start event."""
        return self.build(
            EventType.EXPERT_START,
            {"expert": expert, "chamber": chamber},
        )

    def expert_chunk(self, expert: str, chunk: str) -> SSEEvent:
        """Build expert streaming chunk event."""
        return self.build(
            EventType.EXPERT_CHUNK,
            {"expert": expert, "chunk": chunk},
        )

    def expert_contribution(
        self,
        expert: str,
        contribution: dict[str, Any],
        token_usage: TokenUsage | None = None,
    ) -> SSEEvent:
        """Build expert contribution complete event."""
        return self.build(
            EventType.EXPERT_CONTRIBUTION,
            {"expert": expert, "contribution": contribution},
            token_usage,
        )

    def expert_error(self, expert: str, error: str) -> SSEEvent:
        """Build expert error event."""
        return self.build(
            EventType.EXPERT_ERROR,
            {"expert": expert, "error": error},
        )

    def redteam_objection(
        self,
        expert: str,
        objection: dict[str, Any],
    ) -> SSEEvent:
        """Build red team objection event."""
        return self.build(
            EventType.REDTEAM_OBJECTION,
            {"expert": expert, "objection": objection},
        )

    def moderator_synthesis(self, summary: str) -> SSEEvent:
        """Build moderator synthesis event."""
        return self.build(
            EventType.MODERATOR_SYNTHESIS,
            {"summary": summary},
        )

    def moderator_filter(
        self,
        original_count: int,
        filtered_count: int,
        breakdown: dict[str, int],
    ) -> SSEEvent:
        """Build moderator filter event."""
        return self.build(
            EventType.MODERATOR_FILTER,
            {
                "original_count": original_count,
                "filtered_count": filtered_count,
                "breakdown": breakdown,
            },
        )

    def moderator_delta(
        self,
        field: str,
        operation: str,
        accepted: bool,
        reason: str = "",
    ) -> SSEEvent:
        """Build moderator delta application event."""
        return self.build(
            EventType.MODERATOR_DELTA,
            {
                "field": field,
                "operation": operation,
                "accepted": accepted,
                "reason": reason,
            },
        )

    def certified(self, sheet: ScenarioSheet) -> SSEEvent:
        """Build certification complete event."""
        return self.build(
            EventType.CERTIFIED,
            {
                "version": sheet.version,
                "hash": sheet.consistency_hash,
            },
        )

    def certification_failed(self, reason: str, violations: list[dict[str, Any]]) -> SSEEvent:
        """Build certification failed event."""
        return self.build(
            EventType.CERTIFICATION_FAILED,
            {"reason": reason, "violations": violations},
        )

    def progress(self, message: str, percent: float | None = None) -> SSEEvent:
        """Build progress event."""
        data: dict[str, Any] = {"message": message}
        if percent is not None:
            data["percent"] = percent
        return self.build(EventType.PROGRESS, data)

    def heartbeat(self) -> SSEEvent:
        """Build heartbeat event."""
        return self.build(EventType.HEARTBEAT)


# =============================================================================
# SSE Formatter
# =============================================================================


def format_sse(event: SSEEvent) -> str:
    """Format an SSEEvent for transmission."""
    lines = []

    # Event ID for reconnection
    lines.append(f"id: {event.event_id}")

    # Event type
    lines.append(f"event: {event.event_type}")

    # Data as JSON
    data = event.model_dump(mode="json")
    lines.append(f"data: {json.dumps(data)}")

    # Empty line to end event
    lines.append("")
    lines.append("")

    return "\n".join(lines)


def format_sse_simple(event_type: str, data: Any) -> str:
    """Format a simple SSE event."""
    lines = [
        f"event: {event_type}",
        f"data: {json.dumps(data)}",
        "",
        "",
    ]
    return "\n".join(lines)


# =============================================================================
# SSE Stream Generator
# =============================================================================


class SSEStream:
    """
    Async generator for SSE events.

    Supports:
    - Automatic heartbeats
    - Event buffering
    - Reconnection from sequence number
    """

    def __init__(
        self,
        session: SessionState,
        heartbeat_interval: float = 15.0,
    ):
        self.session = session
        self.builder = EventBuilder(session)
        self.heartbeat_interval = heartbeat_interval
        self._queue: asyncio.Queue[SSEEvent | None] = asyncio.Queue()
        self._closed = False
        self._heartbeat_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the stream (including heartbeat task)."""
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def close(self) -> None:
        """Close the stream."""
        self._closed = True
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        await self._queue.put(None)  # Signal end

    async def emit(self, event: SSEEvent) -> None:
        """Emit an event to the stream."""
        if not self._closed:
            await self._queue.put(event)

    async def emit_type(
        self,
        event_type: str,
        data: dict[str, Any] | None = None,
        token_usage: TokenUsage | None = None,
    ) -> None:
        """Emit an event by type."""
        event = self.builder.build(event_type, data, token_usage)
        await self.emit(event)

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats."""
        try:
            while not self._closed:
                await asyncio.sleep(self.heartbeat_interval)
                if not self._closed:
                    await self.emit(self.builder.heartbeat())
        except asyncio.CancelledError:
            pass

    async def __aiter__(self) -> AsyncIterator[str]:
        """Iterate over formatted SSE strings."""
        await self.start()
        try:
            while True:
                event = await self._queue.get()
                if event is None:
                    break
                yield format_sse(event)
        finally:
            await self.close()


# =============================================================================
# Recovery Support
# =============================================================================


async def replay_events_from_sequence(
    session: SessionState,
    from_sequence: int,
    event_history: list[SSEEvent],
) -> AsyncIterator[str]:
    """
    Replay events from a given sequence number for SSE reconnection.

    Args:
        session: Current session state
        from_sequence: Last received sequence number
        event_history: List of past events

    Yields:
        Formatted SSE strings for missed events
    """
    for event in event_history:
        if event.sequence > from_sequence:
            yield format_sse(event)
