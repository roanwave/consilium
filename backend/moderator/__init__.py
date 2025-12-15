"""Moderator package - synthesis, consistency, and filtering."""

from backend.moderator.consistency import (
    is_certified_ready,
    resolve_contradictions,
    run_consistency_pass,
    summarize_violations,
)
from backend.moderator.moderator import (
    DeltaApplicator,
    FIELD_OWNERSHIP,
    Moderator,
    RedTeamFilter,
)

__all__ = [
    # Consistency
    "is_certified_ready",
    "resolve_contradictions",
    "run_consistency_pass",
    "summarize_violations",
    # Moderator
    "DeltaApplicator",
    "FIELD_OWNERSHIP",
    "Moderator",
    "RedTeamFilter",
]
