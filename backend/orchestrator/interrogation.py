"""Two-layer interrogation logic.

Handles core interrogation and conditional expert questions.

Phase 2 implementation.
"""

from typing import Any

from backend.lib.models import (
    CoreInterrogation,
    ExpertInterrogation,
    ExpertQuestion,
    ScenarioSheet,
)


class InterrogationManager:
    """
    Manages the two-layer interrogation process.

    Layer 1: Core questions (always asked, 8-10 questions)
    Layer 2: Expert questions (conditional, max 1 per expert)
    """

    def __init__(self):
        self.experts: list[Any] = []  # Will be list[Expert] in Phase 2

    def get_core_questions(self) -> list[dict[str, Any]]:
        """Get the core interrogation questions."""
        # Defined in scenario.py for now
        pass

    async def get_expert_questions(
        self,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
    ) -> list[ExpertQuestion]:
        """
        Get conditional questions from experts.

        Only returns questions for experts with critical ambiguity.
        Most scenarios need 2-3 expert questions max.
        """
        questions = []

        for expert in self.experts:
            question = expert.get_conditional_question(sheet, answers)
            if question:
                questions.append(question)

        return questions

    def are_answers_complete(
        self,
        core_answers: CoreInterrogation,
        expert_answers: dict[str, str],
        pending_questions: list[ExpertQuestion],
    ) -> bool:
        """Check if all required answers have been provided."""
        # Core answers are always required
        if not core_answers:
            return False

        # Check all pending expert questions have answers
        for q in pending_questions:
            if q.expert not in expert_answers:
                return False

        return True
