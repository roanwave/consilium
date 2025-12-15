"""Interrogation answers endpoint."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from backend.lib.models import (
    CoreInterrogation,
    Era,
    ExpertQuestion,
    ScenarioSheet,
    SessionStatus,
    SubmitAnswersRequest,
    SubmitAnswersResponse,
    TerrainWeather,
)
from backend.lib.persistence import SessionStore, get_session_store

router = APIRouter()


def _create_initial_sheet(answers: CoreInterrogation) -> ScenarioSheet:
    """Create initial ScenarioSheet from core interrogation answers."""
    return ScenarioSheet(
        era=answers.era,
        theater=answers.theater,
        stakes=answers.why_battle_now,
        terrain_weather=TerrainWeather(
            terrain_type=answers.terrain_type,
            defining_feature=answers.terrain_feature,
        ),
        magic={"present": answers.magic_present, "constraints": [answers.magic_constraints]}
        if answers.magic_present
        else {"present": False},
    )


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

    # Store core answers
    session.core_answers = request.core_answers

    # Create initial sheet from answers
    session.sheet = _create_initial_sheet(request.core_answers)

    # Store any expert answers
    if request.expert_answers:
        session.expert_interrogation.answers.update(request.expert_answers)

    # TODO: Phase 2 - Check if experts need to ask conditional questions
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
