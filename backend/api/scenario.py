"""Scenario creation endpoint."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from backend.lib.models import (
    CreateScenarioRequest,
    CreateScenarioResponse,
    SessionState,
    SessionStatus,
)
from backend.lib.persistence import SessionStore, get_session_store

router = APIRouter()


def _build_core_questions() -> list[dict]:
    """Build the list of core interrogation questions."""
    return [
        {
            "id": "era",
            "type": "select",
            "question": "What era is this battle set in?",
            "options": [
                {"value": "ancient", "label": "Ancient (Pre-500 CE)"},
                {"value": "early_medieval", "label": "Early Medieval (500-1000 CE)"},
                {"value": "high_medieval", "label": "High Medieval (1000-1300 CE)"},
                {"value": "late_medieval", "label": "Late Medieval (1300-1500 CE)"},
                {"value": "renaissance", "label": "Renaissance (1500-1600 CE)"},
                {"value": "fantasy", "label": "Fantasy"},
            ],
            "required": True,
        },
        {
            "id": "theater",
            "type": "text",
            "question": "What geographic theater is this battle in?",
            "placeholder": "e.g., Northern France, the Levant, fantasy kingdom",
            "required": False,
        },
        {
            "id": "why_battle_now",
            "type": "textarea",
            "question": "Why is this battle happening now? What forces the engagement?",
            "placeholder": "What strategic necessity or narrative reason brings these armies together?",
            "required": True,
        },
        {
            "id": "army_sizes",
            "type": "textarea",
            "question": "What are the army sizes and key asymmetries?",
            "placeholder": "e.g., 8,000 vs 12,000; defenders have fortifications; attackers have cavalry advantage",
            "required": True,
        },
        {
            "id": "terrain_type",
            "type": "select",
            "question": "What is the primary terrain type?",
            "options": [
                {"value": "plains", "label": "Plains"},
                {"value": "hills", "label": "Hills"},
                {"value": "mountains", "label": "Mountains"},
                {"value": "forest", "label": "Forest"},
                {"value": "marsh", "label": "Marsh"},
                {"value": "river_crossing", "label": "River Crossing"},
                {"value": "coastal", "label": "Coastal"},
                {"value": "urban", "label": "Urban"},
                {"value": "desert", "label": "Desert"},
            ],
            "required": True,
        },
        {
            "id": "terrain_feature",
            "type": "text",
            "question": "What is the one defining terrain feature?",
            "placeholder": "e.g., a fordable river, a steep ridge, a fortified bridge",
            "required": True,
        },
        {
            "id": "commander_competence_side_a",
            "type": "select",
            "question": "How competent is Side A's commander?",
            "options": [
                {"value": "incompetent", "label": "Incompetent"},
                {"value": "mediocre", "label": "Mediocre"},
                {"value": "competent", "label": "Competent"},
                {"value": "skilled", "label": "Skilled"},
                {"value": "brilliant", "label": "Brilliant"},
            ],
            "required": True,
        },
        {
            "id": "commander_competence_side_b",
            "type": "select",
            "question": "How competent is Side B's commander?",
            "options": [
                {"value": "incompetent", "label": "Incompetent"},
                {"value": "mediocre", "label": "Mediocre"},
                {"value": "competent", "label": "Competent"},
                {"value": "skilled", "label": "Skilled"},
                {"value": "brilliant", "label": "Brilliant"},
            ],
            "required": True,
        },
        {
            "id": "magic_present",
            "type": "boolean",
            "question": "Is magic present in this world?",
            "required": True,
        },
        {
            "id": "magic_constraints",
            "type": "textarea",
            "question": "If magic is present, what are its constraints?",
            "placeholder": "How powerful is magic? What can't it do? Who can use it?",
            "required": False,
            "conditional": {"field": "magic_present", "value": True},
        },
        {
            "id": "narrative_outcome",
            "type": "select",
            "question": "What is the desired narrative outcome?",
            "options": [
                {"value": "decisive_victory", "label": "Decisive Victory"},
                {"value": "pyrrhic_victory", "label": "Pyrrhic Victory"},
                {"value": "stalemate", "label": "Stalemate"},
                {"value": "fighting_retreat", "label": "Fighting Retreat"},
                {"value": "rout", "label": "Rout"},
                {"value": "other", "label": "Other"},
            ],
            "required": True,
        },
        {
            "id": "violence_level",
            "type": "select",
            "question": "What level of violence detail do you want?",
            "options": [
                {"value": "low", "label": "Low - Minimal graphic detail"},
                {"value": "medium", "label": "Medium - Realistic but not gratuitous"},
                {"value": "high", "label": "High - Unflinching realism"},
            ],
            "required": True,
        },
    ]


@router.post("/scenario", response_model=CreateScenarioResponse)
async def create_scenario(
    request: CreateScenarioRequest,
    store: SessionStore = Depends(get_session_store),
) -> CreateScenarioResponse:
    """
    Create a new scenario session.

    Returns session ID and core interrogation questions.
    """
    # Create new session
    session = await store.create()
    session.status = SessionStatus.INTERROGATING
    await store.save(session)

    return CreateScenarioResponse(
        session_id=session.session_id,
        status=session.status,
        core_questions=_build_core_questions(),
    )


@router.get("/scenario/{session_id}")
async def get_scenario(
    session_id: UUID,
    store: SessionStore = Depends(get_session_store),
) -> dict:
    """Get current scenario state."""
    session = await store.get(session_id)
    return {
        "session_id": str(session.session_id),
        "status": session.status.value,
        "current_round": session.current_round,
        "max_rounds": session.max_rounds,
        "sheet": session.sheet.model_dump() if session.sheet else None,
    }
