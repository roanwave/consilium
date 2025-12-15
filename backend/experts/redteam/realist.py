"""The Realist - Practical feasibility critic."""

from typing import Any

from backend.config import ModelType
from backend.experts.base import ExpertConfig, RedTeamExpert
from backend.lib.models import (
    Chamber,
    ExpertContribution,
    ScenarioSheet,
)


REALIST_SYSTEM_PROMPT = """You are THE REALIST, Grounded in Mud and Blood.

You have walked battlefields before the chroniclers arrived to clean them up.
You know what war actually smells like, sounds like, looks like. You distrust
grand narratives because you've seen how they erase the chaos, the confusion,
the sheer physical difficulty of moving thousands of men and making them fight.
Your job is to ask: could this actually HAPPEN? Not in theory—in practice.

## YOUR ROLE

You are the Red Team's practical feasibility checker. You find:
1. **PHYSICAL IMPOSSIBILITIES**: Things humans/animals/equipment can't do
2. **LOGISTICAL HAND-WAVES**: Supply and movement treated as trivial
3. **COMMAND FANTASIES**: Coordination that couldn't exist with period communications
4. **MORALE MAGIC**: Troops behaving unlike actual humans under stress

## WHAT YOU CHECK

- Can troops actually march that far in that time?
- Can commanders actually coordinate that maneuver?
- Would troops actually stand under those conditions?
- Can supplies actually support that operation?
- Would visibility actually allow that observation?
- Would exhaustion affect that final charge?

## PHYSICAL REALITIES

You know that:
- Men tire, horses founder, weapons break
- Night fighting is nearly impossible before modern optics
- Rain turns roads to mud and bowstrings to slack
- Smoke obscures battlefields within minutes
- Men break before they're cut down
- Commanders can only see a fraction of their battlefield

## YOUR VOICE

You speak as one who has been there—in the mud, in the chaos, in the press of
bodies where theory meets reality. Your tone is blunt, sometimes crude—you
have no patience for armchair generals who've never smelled blood. You speak
of sweat, of fatigue, of fear.

You use phrases like:
- "Try getting men to do that after eight hours of fighting."
- "In theory, yes. In a muddy field with arrows falling? No."
- "That assumes the horses aren't blown by then."
- "No one who's been in a shield wall believes that."

## OUTPUT FORMAT

Respond with a JSON object:
```json
{
    "objections": [
        {
            "target": "Specific claimed action or outcome",
            "objection": "Why this wouldn't work in practice",
            "severity": "critical|major|minor",
            "reality": "What would actually happen",
            "suggestion": "What might be more realistic (optional)"
        }
    ]
}
```

## SEVERITY LEVELS

- **CRITICAL**: Physically impossible (humans can't do this)
- **MAJOR**: Extremely unlikely in real conditions
- **MINOR**: Optimistic but not impossible

Remember: You test against reality. You do not provide solutions.
"""


class Realist(RedTeamExpert):
    """
    The Realist - Grounded in Mud and Blood.

    Checks practical feasibility. Knows what war actually looks like.
    Has no patience for armchair generals who've never smelled blood.
    """

    @property
    def config(self) -> ExpertConfig:
        return ExpertConfig(
            name="The Realist",
            codename="realist",
            title="Grounded in Mud and Blood",
            model=ModelType.CLAUDE_SONNET,
            icon="",
            chamber=Chamber.REDTEAM,
            description=(
                "Has walked battlefields before the chroniclers cleaned them up. "
                "Tests scenarios against physical reality and human limitations."
            ),
        )

    def _build_system_prompt(self, sheet: ScenarioSheet) -> str:
        """Build the Realist's system prompt."""
        return REALIST_SYSTEM_PROMPT

    def _build_user_prompt(
        self,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
        prior_contributions: list[ExpertContribution],
    ) -> str:
        """Build the user prompt for practical feasibility review."""
        prompt_parts = [
            "# Scenario for Practical Feasibility Review\n",
            f"**Era:** {sheet.era.value if sheet.era else 'Unspecified'}",
            f"**Theater:** {sheet.theater or 'Unspecified'}",
        ]

        # Add terrain and conditions (critical for feasibility)
        if sheet.terrain_weather:
            tw = sheet.terrain_weather
            prompt_parts.append("\n## Conditions (AFFECTS EVERYTHING)")
            prompt_parts.append(f"- Terrain: {tw.terrain_type.value}")
            prompt_parts.append(f"- Defining Feature: {tw.defining_feature}")
            prompt_parts.append(f"- Weather: {tw.weather.value}")
            prompt_parts.append(f"- Ground: {tw.ground_conditions}")
            prompt_parts.append(f"- Visibility: {tw.visibility}")
            prompt_parts.append(f"- Time: {tw.time_of_day}")

        # Add forces (check physical demands)
        if sheet.forces:
            prompt_parts.append("\n## Forces (CHECK PHYSICAL DEMANDS)")
            total = sum(f.total_strength for f in sheet.forces.values())
            prompt_parts.append(f"**Total troops to move/feed/coordinate:** {total:,}")

            for side_id, force in sheet.forces.items():
                prompt_parts.append(f"\n**{force.side_name}:**")
                prompt_parts.append(f"- Strength: {force.total_strength:,}")
                prompt_parts.append(f"- Supply State: {force.supply_state or 'Unspecified'}")
                if force.composition:
                    for unit in force.composition[:4]:
                        prompt_parts.append(f"- {unit.count:,} {unit.unit_type}")

        # Add timeline (check if physically possible)
        if sheet.timeline:
            prompt_parts.append("\n## Timeline (CAN THIS PHYSICALLY HAPPEN?)")
            for event in sheet.timeline:
                prompt_parts.append(f"- [{event.timestamp}] {event.event}")

        # Add decision points (check command feasibility)
        if sheet.decision_points:
            prompt_parts.append("\n## Command Decisions (CHECK COORDINATION)")
            for dp in sheet.decision_points:
                prompt_parts.append(f"- [{dp.timestamp}] {dp.commander}: {dp.chosen}")

        # Add constraints
        if sheet.constraints:
            prompt_parts.append("\n## Stated Constraints")
            for c in sheet.constraints:
                prompt_parts.append(f"- {c}")

        # Add expert claims (may claim impossible feats)
        if prior_contributions:
            prompt_parts.append("\n## Expert Claims (TEST AGAINST REALITY)")
            for contrib in prior_contributions:
                if contrib.domain_claims:
                    prompt_parts.append(f"\n**{contrib.expert}:**")
                    for claim in contrib.domain_claims[:4]:
                        prompt_parts.append(f"- {claim}")

        prompt_parts.append(
            "\n\n# Your Task\n"
            "Test this scenario against practical reality:\n"
            "1. Can troops physically do what's claimed (march distances, fight duration)?\n"
            "2. Can commanders coordinate what's described with period communications?\n"
            "3. Would troops actually behave this way under these conditions?\n"
            "4. Do logistics support the claimed operations?\n\n"
            "Report ALL objections as a JSON object with the 'objections' array. "
            "Ground this scenario in mud and blood."
        )

        return "\n".join(prompt_parts)
