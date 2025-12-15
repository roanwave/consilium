"""Interrogation answers endpoint."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from backend.config import get_settings
from backend.lib.models import (
    CoreInterrogation,
    ExpertQuestion,
    MagicSystem,
    SessionStatus,
    SubmitAnswersRequest,
    SubmitAnswersResponse,
    TerrainWeather,
)
from backend.lib.persistence import SessionStore, get_session_store
from backend.orchestrator.interrogation import InterrogationManager

router = APIRouter()


@router.post("/scenario/{session_id}/answers", response_model=SubmitAnswersResponse)
async def submit_answers(
    session_id: UUID,
    request: SubmitAnswersRequest,
    store: SessionStore = Depends(get_session_store),
) -> SubmitAnswersResponse:
    """
    Submit answers to interrogation questions.

    First submission should include core_answers.
    May return additional expert questions if needed.
    """
    session = await store.get(session_id)

    if session.status != SessionStatus.INTERROGATING:
        raise HTTPException(
            status_code=400,
            detail=f"Session is not in interrogating state: {session.status.value}",
        )

    # Initialize interrogation manager
    manager = InterrogationManager()

    # Build answers dict from CoreInterrogation
    answers_dict = {
        "era": request.core_answers.era.value,
        "theater": request.core_answers.theater or "",
        "why_now": request.core_answers.why_battle_now,
        "army_sizes": request.core_answers.army_sizes,
        "terrain_type": request.core_answers.terrain_type.value,
        "terrain_feature": request.core_answers.terrain_feature,
        "commander_competence_side_a": request.core_answers.commander_competence_side_a.value,
        "commander_competence_side_b": request.core_answers.commander_competence_side_b.value,
        "magic_present": request.core_answers.magic_present,
        "magic_constraints": request.core_answers.magic_constraints or "",
        "narrative_outcome": request.core_answers.narrative_outcome.value,
        "violence_level": request.core_answers.violence_level.value,
    }

    # Validate core answers
    errors = manager.validate_core_answers(answers_dict)
    if errors:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid answers: {'; '.join(errors)}",
        )

    # Build CoreInterrogation model
    core = manager.build_core_interrogation(answers_dict)

    # Build initial ScenarioSheet
    initial_sheet = manager.build_initial_sheet(core)

    # Store in session
    session.core_answers = core
    session.sheet = initial_sheet

    # Store any expert answers
    if request.expert_answers:
        session.expert_interrogation.answers.update(request.expert_answers)

    # Get max rounds from settings
    settings = get_settings()
    session.max_rounds = settings.max_rounds

    # Check if experts need to ask conditional questions
    # For now, we skip expert interrogation and go straight to deliberation
    expert_questions: list[ExpertQuestion] = []
    ready_to_deliberate = True

    if ready_to_deliberate:
        session.status = SessionStatus.DELIBERATING

    await store.save(session)

    return SubmitAnswersResponse(
        session_id=session.session_id,
        status=session.status,
        expert_questions=expert_questions,
        ready_to_deliberate=ready_to_deliberate,
    )


@router.get("/scenario/{session_id}/questions")
async def get_expert_questions(
    session_id: UUID,
    store: SessionStore = Depends(get_session_store),
) -> dict:
    """
    Get any pending expert questions for a session.

    Returns empty list if no questions or if core answers not yet submitted.
    """
    session = await store.get(session_id)

    if session.status != SessionStatus.INTERROGATING:
        return {
            "session_id": str(session_id),
            "expert_questions": [],
            "message": "No pending questions",
        }

    # If we have a sheet, we can check for expert questions
    if session.sheet:
        manager = InterrogationManager()
        # Get answers dict from session
        answers = {}
        if session.core_answers:
            answers = session.core_answers.model_dump()
        answers.update(session.expert_interrogation.answers)

        questions = await manager.get_expert_questions(session.sheet, answers)
        return {
            "session_id": str(session_id),
            "expert_questions": [q.model_dump() for q in questions],
        }

    return {
        "session_id": str(session_id),
        "expert_questions": [],
        "message": "Submit core answers first",
    }
