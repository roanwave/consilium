"""The Adversary - Opponent perspective critic."""

from typing import Any

from backend.config import ModelType
from backend.experts.base import ExpertConfig, RedTeamExpert
from backend.lib.models import (
    Chamber,
    ExpertContribution,
    ScenarioSheet,
)


ADVERSARY_SYSTEM_PROMPT = """You are THE ADVERSARY, Voice of the Enemy.

You speak for those who lost, or for those cast as villains in the narrative.
You know that the enemy commander was not stupid—they had reasons for their
decisions, even the ones that led to defeat. You ask: what did THEY see? What
did THEY know? Why did THEIR plan make sense to them? Too many battle narratives
make the loser an idiot. You demand better.

## YOUR ROLE

You are the Red Team's enemy advocate. You find:
1. **UNREASONABLE ENEMY BEHAVIOR**: When the opposition acts stupidly for no reason
2. **IGNORED ENEMY OPTIONS**: Obvious moves the enemy should have made
3. **ASYMMETRIC INTELLIGENCE**: One side knowing too much, the other too little
4. **VILLAIN BALL**: Enemy making mistakes because the narrative needs them to lose

## WHAT YOU CHAMPION

- The enemy commander's perspective and information
- Why the enemy's decisions made sense at the time
- Options the enemy should have considered
- How the enemy would have seen the battle unfold
- What the enemy could have done to change the outcome

## COMMON PROBLEMS

- "The enemy inexplicably failed to..."
- "The enemy commander didn't notice..."
- "The enemy army just stood there while..."
- "The enemy had no scouts/reserves/plan B..."
- "The enemy's elite troops fled without fighting..."

## YOUR VOICE

You speak as one who has sat in the enemy's chair and seen the battle from their
side. Your tone is challenging, sometimes accusatory—you're tired of narratives
where the enemy exists only to lose. You demand that the enemy be given agency,
intelligence, and reasonable behavior.

You use phrases like:
- "From the enemy's position, they would have seen..."
- "A competent commander in their situation would..."
- "Why would they NOT have..."
- "The enemy is being made to carry the idiot ball here."

## OUTPUT FORMAT

Respond with a JSON object:
```json
{
    "objections": [
        {
            "target": "Specific enemy action or inaction",
            "objection": "Why this makes no sense from the enemy's perspective",
            "severity": "critical|major|minor",
            "enemy_perspective": "What the enemy would actually have seen/known",
            "suggestion": "What would make the enemy's behavior reasonable (optional)"
        }
    ]
}
```

## SEVERITY LEVELS

- **CRITICAL**: Enemy acts with obvious stupidity that no commander would display
- **MAJOR**: Enemy misses obvious opportunity or makes avoidable error
- **MINOR**: Enemy behavior is slightly sub-optimal

Remember: You defend the enemy's intelligence. You do not write their victory.
"""


class Adversary(RedTeamExpert):
    """
    The Adversary - Voice of the Enemy.

    Speaks for those who lost. Demands the enemy be given agency and intelligence.
    Catches narratives that make the loser an idiot.
    """

    @property
    def config(self) -> ExpertConfig:
        return ExpertConfig(
            name="The Adversary",
            codename="adversary",
            title="Voice of the Enemy",
            model=ModelType.CLAUDE_SONNET,
            icon="",
            chamber=Chamber.REDTEAM,
            description=(
                "Speaks for those who lost. Demands the enemy be given agency and "
                "intelligence. Tired of narratives where the enemy exists only to lose."
            ),
        )

    def _build_system_prompt(self, sheet: ScenarioSheet) -> str:
        """Build the Adversary's system prompt."""
        return ADVERSARY_SYSTEM_PROMPT

    def _build_user_prompt(
        self,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
        prior_contributions: list[ExpertContribution],
    ) -> str:
        """Build the user prompt for enemy perspective review."""
        prompt_parts = [
            "# Scenario for Enemy Perspective Review\n",
            f"**Era:** {sheet.era.value if sheet.era else 'Unspecified'}",
            f"**Theater:** {sheet.theater or 'Unspecified'}",
            f"**Stakes:** {sheet.stakes or 'Unspecified'}",
        ]

        # Identify sides and their outcomes (if discernible)
        if sheet.forces:
            prompt_parts.append("\n## The Combatants")
            for side_id, force in sheet.forces.items():
                prompt_parts.append(f"\n**{force.side_name}** ({force.total_strength:,}):")
                if force.commander:
                    prompt_parts.append(
                        f"- Commander: {force.commander.name} "
                        f"({force.commander.competence.value})"
                    )
                    if force.commander.notable_traits:
                        prompt_parts.append(
                            f"- Traits: {', '.join(force.commander.notable_traits)}"
                        )
                if force.composition:
                    prompt_parts.append("- Forces:")
                    for unit in force.composition[:4]:
                        prompt_parts.append(f"  - {unit.count:,} {unit.unit_type}")

        # Add terrain (what both sides could see)
        if sheet.terrain_weather:
            tw = sheet.terrain_weather
            prompt_parts.append(f"\n## Battlefield: {tw.terrain_type.value}")
            prompt_parts.append(f"- Defining Feature: {tw.defining_feature}")
            prompt_parts.append(f"- Visibility: {tw.visibility}")

        # Add decision points (especially enemy decisions)
        if sheet.decision_points:
            prompt_parts.append("\n## Key Decisions (EXAMINE ENEMY CHOICES)")
            for dp in sheet.decision_points:
                prompt_parts.append(f"\n**[{dp.timestamp}] {dp.commander}:**")
                prompt_parts.append(f"- Faced: {dp.situation}")
                prompt_parts.append(f"- Options: {', '.join(dp.options)}")
                prompt_parts.append(f"- Chose: {dp.chosen}")
                prompt_parts.append(f"- Result: {dp.consequences}")

        # Add timeline (how did the enemy experience this?)
        if sheet.timeline:
            prompt_parts.append("\n## How It Unfolded (WHAT DID EACH SIDE SEE?)")
            for event in sheet.timeline:
                prompt_parts.append(f"- [{event.timestamp}] {event.event}")

        # Add casualty distribution (who lost more?)
        if sheet.casualty_profile:
            cp = sheet.casualty_profile
            prompt_parts.append("\n## Outcome")
            if cp.casualty_distribution:
                prompt_parts.append(f"- Distribution: {cp.casualty_distribution}")

        # Add aftermath (who is portrayed as victor/loser?)
        if sheet.aftermath:
            prompt_parts.append(f"\n## Aftermath: {sheet.aftermath}")

        # Add expert claims about enemy
        if prior_contributions:
            prompt_parts.append("\n## What Experts Said About The Forces")
            for contrib in prior_contributions:
                if contrib.domain_claims:
                    prompt_parts.append(f"\n**{contrib.expert}:**")
                    for claim in contrib.domain_claims[:4]:
                        prompt_parts.append(f"- {claim}")

        prompt_parts.append(
            "\n\n# Your Task\n"
            "Review this scenario from the ENEMY's perspective:\n"
            "1. Does the enemy behave reasonably given what they knew?\n"
            "2. Did the enemy miss obvious opportunities without good reason?\n"
            "3. Is the enemy given agency, or do they exist only to lose?\n"
            "4. Would a competent commander have done what the enemy did?\n\n"
            "Report ALL objections as a JSON object with the 'objections' array. "
            "Defend the enemy's right to be intelligent."
        )

        return "\n".join(prompt_parts)
