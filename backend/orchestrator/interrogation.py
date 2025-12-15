"""Two-layer interrogation logic.

Handles core interrogation and conditional expert questions.
"""

from typing import Any

from backend.experts.base import Expert
from backend.lib.models import (
    Commander,
    CommanderCompetence,
    CoreInterrogation,
    Era,
    ExpertInterrogation,
    ExpertQuestion,
    ForceDescription,
    MagicSystem,
    NarrativeOutcome,
    ScenarioSheet,
    TerrainType,
    TerrainWeather,
    ViolenceLevel,
    WeatherCondition,
)

# =============================================================================
# Core Questions (Layer 1)
# =============================================================================

CORE_QUESTIONS: list[dict[str, Any]] = [
    {
        "id": "era",
        "question": "What era is this battle set in?",
        "type": "select",
        "options": [
            {"value": "ancient", "label": "Ancient (Pre-500 CE)"},
            {"value": "early_medieval", "label": "Early Medieval (500-1000 CE)"},
            {"value": "high_medieval", "label": "High Medieval (1000-1300 CE)"},
            {"value": "late_medieval", "label": "Late Medieval (1300-1500 CE)"},
            {"value": "renaissance", "label": "Renaissance (1500-1600 CE)"},
            {"value": "fantasy", "label": "Fantasy (Ahistorical)"},
        ],
        "required": True,
    },
    {
        "id": "theater",
        "question": "What geographic region or theater is this battle set in?",
        "type": "text",
        "placeholder": "e.g., Western Europe, Levant, fictional kingdom of Valdoria",
        "required": False,
        "default": "",
    },
    {
        "id": "why_now",
        "question": "Why must this battle happen now? What forces the engagement?",
        "type": "text",
        "placeholder": "e.g., defending a crucial pass, relieving a siege, intercepting a supply column",
        "required": True,
    },
    {
        "id": "army_sizes",
        "question": "Approximate army sizes and key asymmetry?",
        "type": "text",
        "placeholder": "e.g., 8000 vs 12000, defenders have fortifications; 5000 cavalry vs 15000 infantry",
        "required": True,
    },
    {
        "id": "terrain_type",
        "question": "What is the primary terrain type?",
        "type": "select",
        "options": [
            {"value": "plains", "label": "Plains/Open Field"},
            {"value": "hills", "label": "Hills/Rolling Terrain"},
            {"value": "mountains", "label": "Mountains/Passes"},
            {"value": "forest", "label": "Forest/Woodland"},
            {"value": "marsh", "label": "Marsh/Wetlands"},
            {"value": "river_crossing", "label": "River Crossing"},
            {"value": "coastal", "label": "Coastal"},
            {"value": "urban", "label": "Urban/Siege"},
            {"value": "desert", "label": "Desert"},
        ],
        "required": True,
    },
    {
        "id": "terrain_feature",
        "question": "What is the ONE defining terrain feature?",
        "type": "text",
        "placeholder": "e.g., a stone bridge, a fortified hilltop, a dense oak forest, a fordable river",
        "required": True,
    },
    {
        "id": "commander_competence_side_a",
        "question": "Commander competence level for Side A (typically the protagonist)?",
        "type": "select",
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
        "question": "Commander competence level for Side B (typically the antagonist)?",
        "type": "select",
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
        "question": "Is magic present in this world?",
        "type": "boolean",
        "default": False,
        "required": True,
    },
    {
        "id": "magic_constraints",
        "question": "What are the constraints on magic use?",
        "type": "text",
        "placeholder": "e.g., rare and exhausting, limited to healing, only certain bloodlines",
        "conditional": {"field": "magic_present", "value": True},
        "required": False,
        "default": "",
    },
    {
        "id": "narrative_outcome",
        "question": "What is the desired narrative outcome?",
        "type": "select",
        "options": [
            {"value": "decisive_victory", "label": "Decisive Victory"},
            {"value": "pyrrhic_victory", "label": "Pyrrhic Victory (costly win)"},
            {"value": "stalemate", "label": "Stalemate/Draw"},
            {"value": "fighting_retreat", "label": "Fighting Retreat"},
            {"value": "rout", "label": "Rout (total defeat)"},
            {"value": "other", "label": "Other (specify in stakes)"},
        ],
        "required": True,
    },
    {
        "id": "violence_level",
        "question": "Violence detail level for the narrative?",
        "type": "select",
        "options": [
            {"value": "low", "label": "Low (sanitized, suitable for general audiences)"},
            {"value": "medium", "label": "Medium (realistic but not graphic)"},
            {"value": "high", "label": "High (graphic and visceral)"},
        ],
        "default": "medium",
        "required": True,
    },
]


def get_visible_questions(answers: dict[str, Any]) -> list[dict[str, Any]]:
    """Get questions that should be visible given current answers."""
    visible = []
    for q in CORE_QUESTIONS:
        # Check conditional
        if "conditional" in q:
            cond = q["conditional"]
            field_value = answers.get(cond["field"])
            if field_value != cond["value"]:
                continue  # Skip this question
        visible.append(q)
    return visible


# =============================================================================
# Interrogation Manager
# =============================================================================


class InterrogationManager:
    """
    Manages the two-layer interrogation process.

    Layer 1: Core questions (always asked, 8-10 questions)
    Layer 2: Expert questions (conditional, max 1 per expert)
    """

    def __init__(self, experts: list[Expert] | None = None):
        """
        Initialize manager.

        Args:
            experts: List of Expert instances for layer 2 questions.
        """
        self.experts = experts or []

    def get_core_questions(self, answers: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        Get the core interrogation questions.

        Args:
            answers: Current answers (for conditional visibility)

        Returns:
            List of question definitions
        """
        if answers is None:
            answers = {}
        return get_visible_questions(answers)

    def validate_core_answers(self, answers: dict[str, Any]) -> list[str]:
        """
        Validate that all required core answers are provided.

        Args:
            answers: The answers to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        visible = get_visible_questions(answers)

        for q in visible:
            qid = q["id"]
            required = q.get("required", False)

            if required and qid not in answers:
                errors.append(f"Missing required answer: {q['question']}")
            elif required and answers.get(qid) in (None, ""):
                errors.append(f"Empty answer for required question: {q['question']}")

        return errors

    def build_core_interrogation(self, answers: dict[str, Any]) -> CoreInterrogation:
        """
        Build CoreInterrogation model from raw answers.

        Args:
            answers: Raw answer dict

        Returns:
            CoreInterrogation model
        """
        return CoreInterrogation(
            era=Era(answers.get("era", "high_medieval")),
            theater=answers.get("theater", ""),
            why_battle_now=answers.get("why_now", ""),
            army_sizes=answers.get("army_sizes", ""),
            terrain_type=TerrainType(answers.get("terrain_type", "plains")),
            terrain_feature=answers.get("terrain_feature", ""),
            commander_competence_side_a=CommanderCompetence(
                answers.get("commander_competence_side_a", "competent")
            ),
            commander_competence_side_b=CommanderCompetence(
                answers.get("commander_competence_side_b", "competent")
            ),
            magic_present=answers.get("magic_present", False),
            magic_constraints=answers.get("magic_constraints", ""),
            narrative_outcome=NarrativeOutcome(
                answers.get("narrative_outcome", "decisive_victory")
            ),
            violence_level=ViolenceLevel(answers.get("violence_level", "medium")),
        )

    def build_initial_sheet(self, core: CoreInterrogation) -> ScenarioSheet:
        """
        Build initial ScenarioSheet from core interrogation answers.

        Args:
            core: CoreInterrogation with validated answers

        Returns:
            ScenarioSheet with initial values populated
        """
        # Parse army sizes for initial force estimates
        side_a_strength, side_b_strength = self._parse_army_sizes(core.army_sizes)

        # Build initial sheet
        sheet = ScenarioSheet(
            era=core.era,
            theater=core.theater,
            stakes=core.why_battle_now,
            constraints=[],
            forces={
                "side_a": ForceDescription(
                    side_name="Side A",
                    total_strength=side_a_strength,
                    composition=[],
                    commander=Commander(
                        name="Commander A",
                        title="",
                        competence=core.commander_competence_side_a,
                        personality_traits=[],
                        known_for="",
                    ),
                    morale="steady",
                    supply_state="adequate",
                    objectives=[],
                    constraints=[],
                ),
                "side_b": ForceDescription(
                    side_name="Side B",
                    total_strength=side_b_strength,
                    composition=[],
                    commander=Commander(
                        name="Commander B",
                        title="",
                        competence=core.commander_competence_side_b,
                        personality_traits=[],
                        known_for="",
                    ),
                    morale="steady",
                    supply_state="adequate",
                    objectives=[],
                    constraints=[],
                ),
            },
            terrain_weather=TerrainWeather(
                terrain_type=core.terrain_type,
                defining_feature=core.terrain_feature,
                features=[],
                weather=WeatherCondition.CLEAR,
                visibility="good",
                ground_conditions="firm",
                time_of_day="morning",
                season="summer",
                what_matters=[],
                what_doesnt=[],
            ),
            timeline=[],
            decision_points=[],
            casualty_profile=None,
            aftermath="",
            open_risks=[],
            magic=MagicSystem(
                present=core.magic_present,
                constraints=[core.magic_constraints] if core.magic_constraints else [],
                practitioners=[],
                tactical_role="",
            ),
            last_modified_by="interrogation",
        )

        # Set initial version
        sheet.increment_version("interrogation")

        return sheet

    def _parse_army_sizes(self, army_sizes_text: str) -> tuple[int, int]:
        """
        Parse army sizes from freeform text.

        Args:
            army_sizes_text: Text like "8000 vs 12000" or "5000 cavalry vs 15000 infantry"

        Returns:
            Tuple of (side_a_strength, side_b_strength)
        """
        import re

        # Try to find numbers
        numbers = re.findall(r"(\d+(?:,\d{3})*)", army_sizes_text)

        if len(numbers) >= 2:
            # Parse first two numbers
            side_a = int(numbers[0].replace(",", ""))
            side_b = int(numbers[1].replace(",", ""))
            return (side_a, side_b)
        elif len(numbers) == 1:
            # Single number - assume equal forces
            size = int(numbers[0].replace(",", ""))
            return (size, size)
        else:
            # Default to reasonable medieval battle size
            return (5000, 5000)

    async def get_expert_questions(
        self,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
    ) -> list[ExpertQuestion]:
        """
        Get conditional questions from experts.

        Only returns questions for experts with critical ambiguity.
        Most scenarios need 2-3 expert questions max.

        Args:
            sheet: Current ScenarioSheet
            answers: All answers so far (core + any previous expert)

        Returns:
            List of ExpertQuestion from experts who need clarification
        """
        questions = []

        for expert in self.experts:
            try:
                question = expert.get_conditional_question(sheet, answers)
                if question:
                    questions.append(question)
            except Exception:
                # Expert question generation failed - skip silently
                pass

        return questions

    def are_answers_complete(
        self,
        core_answers: CoreInterrogation | None,
        expert_answers: dict[str, str],
        pending_questions: list[ExpertQuestion],
    ) -> bool:
        """
        Check if all required answers have been provided.

        Args:
            core_answers: Core interrogation answers (None if not yet provided)
            expert_answers: Answers to expert questions keyed by expert codename
            pending_questions: Expert questions awaiting answers

        Returns:
            True if ready to proceed to deliberation
        """
        # Core answers are always required
        if not core_answers:
            return False

        # Check all pending expert questions have answers
        for q in pending_questions:
            if q.expert not in expert_answers:
                # Check if question has default
                if not q.default:
                    return False

        return True

    def apply_expert_defaults(
        self,
        expert_answers: dict[str, str],
        pending_questions: list[ExpertQuestion],
    ) -> dict[str, str]:
        """
        Apply defaults for unanswered expert questions.

        Args:
            expert_answers: Current expert answers
            pending_questions: All expert questions

        Returns:
            Expert answers with defaults applied
        """
        result = dict(expert_answers)

        for q in pending_questions:
            if q.expert not in result and q.default:
                result[q.expert] = q.default

        return result

    def build_expert_interrogation(
        self,
        questions: list[ExpertQuestion],
        answers: dict[str, str],
    ) -> ExpertInterrogation:
        """
        Build ExpertInterrogation model.

        Args:
            questions: Expert questions asked
            answers: Answers provided

        Returns:
            ExpertInterrogation model
        """
        return ExpertInterrogation(
            questions=questions,
            answers=answers,
        )
