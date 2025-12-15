"""API router aggregating all route modules."""

from fastapi import APIRouter

from backend.api.answers import router as answers_router
from backend.api.deliberate import router as deliberate_router
from backend.api.output import router as output_router
from backend.api.scenario import router as scenario_router

router = APIRouter()

# Include all sub-routers
router.include_router(scenario_router, tags=["Scenario"])
router.include_router(answers_router, tags=["Answers"])
router.include_router(deliberate_router, tags=["Deliberation"])
router.include_router(output_router, tags=["Output"])
