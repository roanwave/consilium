"""Custom exceptions for Consilium."""

from typing import Any


class ConsiliumError(Exception):
    """Base exception for all Consilium errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


# =============================================================================
# LLM Errors
# =============================================================================


class LLMError(ConsiliumError):
    """Base exception for LLM-related errors."""

    pass


class LLMRateLimitError(LLMError):
    """Raised when hitting API rate limits."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: float | None = None,
        **kwargs: Any,
    ):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class LLMContextLengthError(LLMError):
    """Raised when context length is exceeded."""

    def __init__(
        self,
        message: str = "Context length exceeded",
        max_tokens: int | None = None,
        used_tokens: int | None = None,
        **kwargs: Any,
    ):
        super().__init__(message, **kwargs)
        self.max_tokens = max_tokens
        self.used_tokens = used_tokens


class LLMAuthenticationError(LLMError):
    """Raised when API authentication fails."""

    pass


class LLMConnectionError(LLMError):
    """Raised when unable to connect to LLM API."""

    pass


class LLMResponseParseError(LLMError):
    """Raised when unable to parse LLM response."""

    def __init__(
        self,
        message: str = "Failed to parse LLM response",
        raw_response: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(message, **kwargs)
        self.raw_response = raw_response


# =============================================================================
# Session Errors
# =============================================================================


class SessionError(ConsiliumError):
    """Base exception for session-related errors."""

    pass


class SessionNotFoundError(SessionError):
    """Raised when session does not exist."""

    def __init__(self, session_id: str, **kwargs: Any):
        super().__init__(f"Session not found: {session_id}", **kwargs)
        self.session_id = session_id


class SessionExpiredError(SessionError):
    """Raised when session has expired."""

    def __init__(self, session_id: str, **kwargs: Any):
        super().__init__(f"Session expired: {session_id}", **kwargs)
        self.session_id = session_id


class SessionStateError(SessionError):
    """Raised when session is in invalid state for operation."""

    def __init__(
        self,
        message: str,
        session_id: str | None = None,
        expected_status: str | None = None,
        actual_status: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(message, **kwargs)
        self.session_id = session_id
        self.expected_status = expected_status
        self.actual_status = actual_status


class SessionPersistenceError(SessionError):
    """Raised when unable to persist session state."""

    pass


# =============================================================================
# Validation Errors
# =============================================================================


class ValidationError(ConsiliumError):
    """Raised when validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        **kwargs: Any,
    ):
        super().__init__(message, **kwargs)
        self.field = field
        self.value = value


class InterrogationError(ValidationError):
    """Raised when interrogation answers are invalid."""

    pass


# =============================================================================
# Consistency Errors
# =============================================================================


class ConsistencyError(ConsiliumError):
    """Raised when scenario has consistency violations."""

    def __init__(
        self,
        message: str,
        violations: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ):
        super().__init__(message, **kwargs)
        self.violations = violations or []


class TimelineParadoxError(ConsistencyError):
    """Raised when timeline has logical paradoxes."""

    pass


class GeographyError(ConsistencyError):
    """Raised when geography/distances are inconsistent."""

    pass


class ForceCompositionError(ConsistencyError):
    """Raised when force numbers don't add up."""

    pass


class AnachronismError(ConsistencyError):
    """Raised when era constraints are violated."""

    def __init__(
        self,
        message: str,
        era: str | None = None,
        item: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(message, **kwargs)
        self.era = era
        self.item = item


# =============================================================================
# Delta/Expert Errors
# =============================================================================


class DeltaError(ConsiliumError):
    """Base exception for delta-related errors."""

    pass


class DeltaRejectedError(DeltaError):
    """Raised when a delta request is rejected."""

    def __init__(
        self,
        message: str,
        expert: str | None = None,
        field: str | None = None,
        reason: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(message, **kwargs)
        self.expert = expert
        self.field = field
        self.reason = reason


class JurisdictionError(DeltaError):
    """Raised when expert tries to modify field outside jurisdiction."""

    def __init__(
        self,
        expert: str,
        field: str,
        allowed_fields: list[str] | None = None,
        **kwargs: Any,
    ):
        message = f"Expert '{expert}' cannot modify field '{field}'"
        super().__init__(message, **kwargs)
        self.expert = expert
        self.field = field
        self.allowed_fields = allowed_fields or []


class ExpertError(ConsiliumError):
    """Raised when an expert encounters an error."""

    def __init__(
        self,
        message: str,
        expert: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(message, **kwargs)
        self.expert = expert


# =============================================================================
# Orchestration Errors
# =============================================================================


class OrchestrationError(ConsiliumError):
    """Base exception for orchestration errors."""

    pass


class MaxRoundsExceededError(OrchestrationError):
    """Raised when max deliberation rounds exceeded without consensus."""

    def __init__(
        self,
        max_rounds: int,
        **kwargs: Any,
    ):
        super().__init__(f"Max rounds ({max_rounds}) exceeded without certification", **kwargs)
        self.max_rounds = max_rounds


class DeliberationError(OrchestrationError):
    """Raised when deliberation process fails."""

    pass


# =============================================================================
# SSE Errors
# =============================================================================


class SSEError(ConsiliumError):
    """Base exception for SSE-related errors."""

    pass


class SSEConnectionError(SSEError):
    """Raised when SSE connection fails."""

    pass


class SSESequenceError(SSEError):
    """Raised when SSE sequence is out of order."""

    def __init__(
        self,
        expected: int,
        received: int,
        **kwargs: Any,
    ):
        super().__init__(f"SSE sequence error: expected {expected}, got {received}", **kwargs)
        self.expected = expected
        self.received = received
