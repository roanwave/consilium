"""The Auditor - Math, timeline, and anachronism checker."""

from typing import Any

from backend.config import ModelType
from backend.experts.base import ExpertConfig, RedTeamExpert
from backend.lib.models import (
    Chamber,
    ExpertContribution,
    ScenarioSheet,
)
from backend.lib.utils import format_number


def _get_attr(obj: Any, attr: str, default: Any = None) -> Any:
    """Safely get attribute from dict or model object."""
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


AUDITOR_SYSTEM_PROMPT = """You are THE AUDITOR, Keeper of the Numbers.

You have an eye for things that don't add up. Literally. You count heads, you time
marches, you verify that what the generals say happened could actually have happened.
You are the one who notices that the army supposedly marched 60 miles through mountains
in a single day, or that 50,000 men fought on a field that could hold perhaps 10,000.
Your loyalty is to mathematical truth, not to dramatic narrative.

## YOUR ROLE

You are the Red Team's mathematician and anachronism detector. You find:
1. **MATH ERRORS**: Numbers that don't add up (casualties > engaged, impossible ratios)
2. **TIMELINE IMPOSSIBILITIES**: Events that couldn't happen in the stated time
3. **ANACHRONISMS**: Technology, tactics, or concepts wrong for the era
4. **SCALE PROBLEMS**: Battles described at impossible scales for terrain/logistics

## ANACHRONISM DETECTION (EXPANDED SCOPE)

You are especially vigilant about:
- **Equipment anachronisms**: Full plate in 900 CE, muskets in 1200 CE
- **Tactical anachronisms**: Combined arms tactics before they existed, trench warfare in antiquity
- **Organizational anachronisms**: Regimental systems before they existed, standardized ranks in tribal armies
- **Conceptual anachronisms**: Geneva Convention thinking in ancient warfare, modern logistics assumptions
- **Communication anachronisms**: Real-time coordination before signaling systems existed
- **Supply anachronisms**: Modern consumption rates applied to pre-modern armies

## ERA-SPECIFIC CHECKS

- **ANCIENT (before 500 CE)**: No stirrups, no heavy cavalry charges, limited siege artillery
- **EARLY MEDIEVAL (500-1000)**: No crossbows until late period, limited literacy for orders
- **HIGH MEDIEVAL (1000-1300)**: No firearms, no standing armies, limited professional soldiers
- **LATE MEDIEVAL (1300-1500)**: Early firearms unreliable, plate armor expensive and rare
- **PIKE AND SHOT (1500-1700)**: Cavalry still relevant, firearms slow to reload
- **MUSKET ERA (1700-1850)**: No rifled muskets until late, no explosive shells
- **RIFLE ERA (1850-1914)**: No automatic weapons early, limited radio
- **MODERN (1914+)**: Appropriate to specific decade

## YOUR VOICE

You speak as one who has learned to distrust claims and verify facts. Your tone is
pedantic but precise—you care about getting the numbers right because the numbers
ARE the story. A battle where the victor takes 90% casualties is a different story
than one where they take 10%.

You use phrases like:
- "The mathematics here are troubling..."
- "At the stated march rate, this would require..."
- "This technology did not exist until..."
- "The numbers as given would mean..."

## OUTPUT FORMAT

Respond with a JSON object:
```json
{
    "objections": [
        {
            "target": "Specific element being questioned",
            "objection": "The mathematical, timeline, or anachronism problem",
            "severity": "critical|major|minor",
            "evidence": "The calculation or historical fact that supports your objection",
            "suggestion": "Brief hint at what might fix it (optional)"
        }
    ]
}
```

## SEVERITY LEVELS

- **CRITICAL**: Math impossibility (casualties > forces) or major anachronism (guns in 1100)
- **MAJOR**: Implausible but not impossible numbers, minor anachronism
- **MINOR**: Rounding errors, slight timeline compression, pedantic nitpicks

Remember: You find problems. You do not fix them.
"""


class Auditor(RedTeamExpert):
    """
    The Auditor - Keeper of the Numbers.

    Checks math, timelines, and anachronisms. Finds things that don't add up.
    Especially vigilant about era-inappropriate technology and tactics.
    """

    @property
    def config(self) -> ExpertConfig:
        return ExpertConfig(
            name="The Auditor",
            codename="auditor",
            title="Keeper of the Numbers",
            model=ModelType.CLAUDE_SONNET,
            icon="",
            chamber=Chamber.REDTEAM,
            description=(
                "Has an eye for things that don't add up. Counts heads, times marches, "
                "catches anachronisms. Loyalty is to mathematical truth."
            ),
        )

    def _build_system_prompt(self, sheet: ScenarioSheet) -> str:
        """Build the Auditor's system prompt."""
        return AUDITOR_SYSTEM_PROMPT

    def _build_user_prompt(
        self,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
        prior_contributions: list[ExpertContribution],
    ) -> str:
        """Build the user prompt with full scenario for audit."""
        prompt_parts = [
            "# Scenario for Mathematical and Anachronism Audit\n",
            f"**Era:** {sheet.era.value if sheet.era else 'Unspecified'}",
            f"**Theater:** {sheet.theater or 'Unspecified'}",
            f"**Stakes:** {sheet.stakes or 'Unspecified'}",
        ]

        # Add forces (critical for math checking)
        if sheet.forces:
            prompt_parts.append("\n## Forces (CHECK THESE NUMBERS)")
            total_engaged = 0
            for side_id, force in sheet.forces.items():
                total_engaged += force.total_strength
                prompt_parts.append(f"\n**{force.side_name}:**")
                prompt_parts.append(f"- Total Strength: {force.total_strength:,}")
                prompt_parts.append(f"- Equipment: {force.equipment or 'Unspecified'}")

                if force.composition:
                    comp_total = sum(u.count for u in force.composition)
                    prompt_parts.append(f"- Composition total: {comp_total:,}")
                    for unit in force.composition:
                        prompt_parts.append(f"  - {unit.count:,} {unit.unit_type}")

            prompt_parts.append(f"\n**Total engaged both sides:** {total_engaged:,}")

        # Add terrain
        if sheet.terrain_weather:
            tw = sheet.terrain_weather
            prompt_parts.append("\n## Terrain and Weather")
            prompt_parts.append(f"- Type: {tw.terrain_type.value}")
            prompt_parts.append(f"- Defining Feature: {tw.defining_feature}")
            prompt_parts.append(f"- Weather: {tw.weather.value}")
            prompt_parts.append(f"- Season: {tw.season}")

        # Add timeline (check for impossibilities)
        if sheet.timeline:
            prompt_parts.append("\n## Timeline (CHECK TIMING)")
            for event in sheet.timeline:
                timestamp = _get_attr(event, "timestamp", "")
                event_name = _get_attr(event, "event", "")
                prompt_parts.append(f"- [{timestamp}] {event_name}")

        # Add casualties (check against forces)
        if sheet.casualty_profile:
            cp = sheet.casualty_profile
            prompt_parts.append("\n## Casualty Profile (VERIFY MATH)")
            total_casualties = _get_attr(cp, "total_casualties")
            if total_casualties:
                prompt_parts.append(f"- Total Casualties: {format_number(total_casualties)}")
            casualty_distribution = _get_attr(cp, "casualty_distribution")
            if casualty_distribution:
                prompt_parts.append(f"- Distribution: {casualty_distribution}")

        # Add decision points
        if sheet.decision_points:
            prompt_parts.append("\n## Decision Points")
            for dp in sheet.decision_points:
                timestamp = _get_attr(dp, "timestamp", "")
                commander = _get_attr(dp, "commander", "")
                situation = _get_attr(dp, "situation", "")[:80]
                prompt_parts.append(f"- [{timestamp}] {commander}: {situation}")

        # Add prior expert claims (may contain errors)
        if prior_contributions:
            prompt_parts.append("\n## Expert Claims to Audit")
            for contrib in prior_contributions:
                prompt_parts.append(f"\n**{contrib.expert}:**")
                for claim in contrib.domain_claims:
                    prompt_parts.append(f"- {claim}")

        prompt_parts.append(
            "\n\n# Your Task\n"
            "Audit this scenario for:\n"
            "1. Mathematical impossibilities (do the numbers add up?)\n"
            "2. Timeline impossibilities (could events happen in stated time?)\n"
            "3. Anachronisms (is the technology/tactics appropriate for the era?)\n"
            "4. Scale problems (can the terrain support these numbers?)\n\n"
            "Report ALL objections you find as a JSON object with the 'objections' array."
        )

        return "\n".join(prompt_parts)
