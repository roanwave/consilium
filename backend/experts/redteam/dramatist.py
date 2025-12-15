"""The Dramatist - Narrative coherence critic."""

from typing import Any

from backend.config import ModelType
from backend.experts.base import ExpertConfig, RedTeamExpert
from backend.lib.models import (
    Chamber,
    ExpertContribution,
    ScenarioSheet,
)


def _get_attr(obj: Any, attr: str, default: Any = None) -> Any:
    """Safely get attribute from dict or model object."""
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


DRAMATIST_SYSTEM_PROMPT = """You are THE DRAMATIST, Servant of the Story.

You understand that a battle scenario is not just a simulation—it's a STORY.
And stories have rules. They need narrative logic, dramatic tension, emotional
beats. A battle where everything goes according to plan is boring. A battle
where random chaos determines everything is unsatisfying. You seek the middle
ground: the narrative that feels INEVITABLE in hindsight while being UNCERTAIN
in the moment.

## YOUR ROLE

You are the Red Team's narrative critic. You find:
1. **MISSING DRAMA**: Scenarios that are technically correct but boring
2. **NARRATIVE HOLES**: Story elements that don't connect
3. **WASTED SETUPS**: Elements introduced but never paid off
4. **ANTICLIMAX**: Big buildups with unsatisfying resolutions
5. **THEME DRIFT**: Scenarios that lose their central meaning

## WHAT MAKES A GOOD BATTLE STORY

- Clear stakes (what's being fought for?)
- Meaningful decisions (choices that matter)
- Reversal of fortune (things change)
- Character moments (commanders reveal themselves through choices)
- Irony (plans fail in revealing ways)
- Consequence (the ending follows from what came before)

## WHAT KILLS DRAMA

- Foregone conclusions (outcome never in doubt)
- Arbitrary outcomes (results disconnected from actions)
- Missing agency (things just happen)
- Unearned victories (winning without cost or cleverness)
- Wasted characters (commanders with no defining moments)

## YOUR VOICE

You speak as one who loves a good story and hates to see one wasted. Your tone
is artistic, sometimes plaintive—you're mourning the drama that could have been.
You think in arcs and beats, in setup and payoff. You want the scenario to
MEAN something.

You use phrases like:
- "Where is the moment when...?"
- "This victory feels unearned because..."
- "We set up X but never paid it off."
- "The dramatic question here should be..."

## OUTPUT FORMAT

Respond with a JSON object:
```json
{
    "objections": [
        {
            "target": "Narrative element that isn't working",
            "objection": "The storytelling problem",
            "severity": "critical|major|minor",
            "missing": "What the narrative needs",
            "suggestion": "What might improve the story (optional)"
        }
    ]
}
```

## SEVERITY LEVELS

- **CRITICAL**: The scenario has no dramatic core (why are we telling this story?)
- **MAJOR**: Significant narrative opportunity missed or botched
- **MINOR**: Polish item that would improve the story

Remember: You critique the narrative. You do not write it.
"""


class Dramatist(RedTeamExpert):
    """
    The Dramatist - Servant of the Story.

    Critiques narrative coherence and dramatic structure.
    Wants scenarios to mean something, not just simulate.
    """

    @property
    def config(self) -> ExpertConfig:
        return ExpertConfig(
            name="The Dramatist",
            codename="dramatist",
            title="Servant of the Story",
            model=ModelType.CLAUDE_SONNET,
            icon="",
            chamber=Chamber.REDTEAM,
            description=(
                "Understands that a battle is a story. Critiques narrative coherence, "
                "dramatic tension, and emotional resonance."
            ),
        )

    def _build_system_prompt(self, sheet: ScenarioSheet) -> str:
        """Build the Dramatist's system prompt."""
        return DRAMATIST_SYSTEM_PROMPT

    def _build_user_prompt(
        self,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
        prior_contributions: list[ExpertContribution],
    ) -> str:
        """Build the user prompt for narrative review."""
        prompt_parts = [
            "# Scenario for Narrative Review\n",
            f"**Era:** {sheet.era.value if sheet.era else 'Unspecified'}",
            f"**Theater:** {sheet.theater or 'Unspecified'}",
        ]

        # The dramatic question (stakes)
        prompt_parts.append("\n## THE DRAMATIC QUESTION")
        prompt_parts.append(f"**Stakes:** {sheet.stakes or 'MISSING - this is a problem'}")

        # The characters (commanders)
        if sheet.forces:
            prompt_parts.append("\n## THE CHARACTERS")
            for side_id, force in sheet.forces.items():
                side_name = _get_attr(force, "side_name", side_id)
                prompt_parts.append(f"\n**{side_name}:**")
                commander = _get_attr(force, "commander", None)
                if commander:
                    cmd_name = _get_attr(commander, "name", "Unknown")
                    competence = _get_attr(commander, "competence", "")
                    comp_val = competence.value if hasattr(competence, "value") else str(competence)
                    prompt_parts.append(f"- {cmd_name}")
                    prompt_parts.append(f"- Competence: {comp_val}")
                    traits = _get_attr(commander, "notable_traits", None) or _get_attr(commander, "personality_traits", [])
                    if traits:
                        prompt_parts.append(f"- Traits: {', '.join(traits)}")
                else:
                    prompt_parts.append("- Commander: UNNAMED (reduces dramatic potential)")
                morale_factors = _get_attr(force, "morale_factors", [])
                if morale_factors:
                    prompt_parts.append(f"- Fighting for: {', '.join(morale_factors)}")

        # The setting (terrain)
        if sheet.terrain_weather:
            tw = sheet.terrain_weather
            prompt_parts.append("\n## THE SETTING")
            prompt_parts.append(f"- Terrain: {tw.terrain_type.value}")
            prompt_parts.append(f"- Defining Feature: {tw.defining_feature}")
            prompt_parts.append(f"- Weather: {tw.weather.value}")
            prompt_parts.append(f"- Time: {tw.time_of_day}")

        # The plot (decision points)
        if sheet.decision_points:
            prompt_parts.append("\n## THE TURNING POINTS")
            for dp in sheet.decision_points:
                timestamp = _get_attr(dp, "timestamp", "")
                commander = _get_attr(dp, "commander", "")
                situation = _get_attr(dp, "situation", "")
                chosen = _get_attr(dp, "chosen", "")
                consequences = _get_attr(dp, "consequences", "")
                prompt_parts.append(f"\n**{commander}** at {timestamp}:")
                prompt_parts.append(f"- Faces: {situation}")
                prompt_parts.append(f"- Chooses: {chosen}")
                prompt_parts.append(f"- Result: {consequences}")
        else:
            prompt_parts.append(
                "\n## THE TURNING POINTS\n"
                "**NONE DEFINED** - Where are the moments of choice?"
            )

        # The arc (timeline)
        if sheet.timeline:
            prompt_parts.append("\n## THE ARC")
            for event in sheet.timeline:
                timestamp = _get_attr(event, "timestamp", "")
                event_name = _get_attr(event, "event", "")
                prompt_parts.append(f"- [{timestamp}] {event_name}")

        # The resolution (aftermath)
        if sheet.aftermath:
            prompt_parts.append(f"\n## THE RESOLUTION: {sheet.aftermath}")
        else:
            prompt_parts.append("\n## THE RESOLUTION: **UNDEFINED**")

        # Add narrative fragments from experts
        narrative_fragments = []
        if prior_contributions:
            for contrib in prior_contributions:
                if contrib.narrative_fragment:
                    narrative_fragments.append(
                        f"**{contrib.expert}:** {contrib.narrative_fragment[:200]}"
                    )
        if narrative_fragments:
            prompt_parts.append("\n## EXPERT NARRATIVE CONTRIBUTIONS")
            prompt_parts.extend(narrative_fragments)

        prompt_parts.append(
            "\n\n# Your Task\n"
            "Review this scenario as a STORY:\n"
            "1. What is the dramatic question? Is it clear?\n"
            "2. Do the characters have defining moments?\n"
            "3. Are there setups that pay off? Reversals?\n"
            "4. Does the ending feel earned?\n"
            "5. Is there something this battle MEANS?\n\n"
            "Report ALL narrative objections as a JSON object with the 'objections' array. "
            "Make this story worth telling."
        )

        return "\n".join(prompt_parts)
