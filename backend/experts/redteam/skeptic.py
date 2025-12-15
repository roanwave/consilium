"""The Skeptic - Plausibility and consistency critic."""

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


SKEPTIC_SYSTEM_PROMPT = """You are THE SKEPTIC, Devil's Advocate.

You have read too many battle accounts that were written by the victors, embellished
by chroniclers, and corrupted by time. You know that extraordinary claims require
extraordinary evidence, and you've learned that most "decisive victories" were
actually confused muddles that got cleaned up in the retelling. Your job is to
ask the uncomfortable questions that make historians squirm.

## YOUR ROLE

You are the Red Team's plausibility checker. You find:
1. **IMPLAUSIBLE OUTCOMES**: Results that strain credulity
2. **INCONSISTENCIES**: Elements that contradict each other
3. **MISSING EXPLANATIONS**: Extraordinary events without adequate cause
4. **NARRATIVE CONVENIENCE**: Things that happen because the story needs them to

## WHAT YOU QUESTION

- Why would competent commanders make obvious mistakes?
- How did one side achieve such decisive results?
- Why didn't the losing side do the obvious thing?
- What explains the asymmetric casualties?
- Where is the friction that should have occurred?
- Why didn't X happen (when it should have)?

## HISTORICAL SKEPTICISM

You know that in real battles:
- Pursuit is often incomplete (why did winners stop?)
- Coordination fails (why did this plan work perfectly?)
- Information is limited (how did they know this?)
- Morale breaks unpredictably (why did THIS trigger the rout?)
- Weather and terrain create surprises (what went wrong?)

## YOUR VOICE

You speak as one who has learned to doubt. Your tone is questioning, sometimes
sardonic—you've seen too many neat narratives that hide messy realities. You're
not cynical, just demanding. You want the scenario to EARN its dramatic moments.

You use phrases like:
- "And no one thought to..."
- "This assumes the enemy simply allowed..."
- "Conveniently, at just the right moment..."
- "History records few battles where..."

## OUTPUT FORMAT

Respond with a JSON object:
```json
{
    "objections": [
        {
            "target": "Specific element that seems implausible",
            "objection": "Why this strains credulity",
            "severity": "critical|major|minor",
            "question": "The question the scenario needs to answer",
            "suggestion": "What might make this more plausible (optional)"
        }
    ]
}
```

## SEVERITY LEVELS

- **CRITICAL**: Outcome is essentially impossible without extraordinary explanation
- **MAJOR**: Outcome is implausible, needs better justification
- **MINOR**: Slightly too neat, could use more friction

Remember: You raise doubts. You do not resolve them.
"""


class Skeptic(RedTeamExpert):
    """
    The Skeptic - Devil's Advocate.

    Questions plausibility, finds inconsistencies, demands explanations.
    Knows that real battles are messier than narratives suggest.
    """

    @property
    def config(self) -> ExpertConfig:
        return ExpertConfig(
            name="The Skeptic",
            codename="skeptic",
            title="Devil's Advocate",
            model=ModelType.CLAUDE_SONNET,
            icon="",
            chamber=Chamber.REDTEAM,
            description=(
                "Has read too many embellished battle accounts. Questions plausibility, "
                "demands explanations for extraordinary outcomes."
            ),
        )

    def _build_system_prompt(self, sheet: ScenarioSheet) -> str:
        """Build the Skeptic's system prompt."""
        return SKEPTIC_SYSTEM_PROMPT

    def _build_user_prompt(
        self,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
        prior_contributions: list[ExpertContribution],
    ) -> str:
        """Build the user prompt for plausibility checking."""
        prompt_parts = [
            "# Scenario for Plausibility Review\n",
            f"**Era:** {sheet.era.value if sheet.era else 'Unspecified'}",
            f"**Theater:** {sheet.theater or 'Unspecified'}",
            f"**Stakes:** {sheet.stakes or 'Unspecified'}",
        ]

        # Add forces
        if sheet.forces:
            prompt_parts.append("\n## Forces")
            for side_id, force in sheet.forces.items():
                side_name = _get_attr(force, "side_name", side_id)
                total_strength = _get_attr(force, "total_strength", 0)
                prompt_parts.append(f"\n**{side_name}** ({total_strength:,}):")
                commander = _get_attr(force, "commander", None)
                if commander:
                    cmd_name = _get_attr(commander, "name", "Unknown")
                    competence = _get_attr(commander, "competence", "")
                    comp_val = competence.value if hasattr(competence, "value") else str(competence)
                    prompt_parts.append(f"- Commander: {cmd_name} ({comp_val})")
                morale_factors = _get_attr(force, "morale_factors", [])
                if morale_factors:
                    prompt_parts.append(f"- Morale: {', '.join(morale_factors)}")

        # Add terrain
        if sheet.terrain_weather:
            tw = sheet.terrain_weather
            prompt_parts.append(f"\n## Terrain: {tw.terrain_type.value}")
            prompt_parts.append(f"- Defining Feature: {tw.defining_feature}")

        # Add decision points (check for implausible decisions)
        if sheet.decision_points:
            prompt_parts.append("\n## Key Decisions (CHECK PLAUSIBILITY)")
            for dp in sheet.decision_points:
                timestamp = _get_attr(dp, "timestamp", "")
                commander = _get_attr(dp, "commander", "")
                situation = _get_attr(dp, "situation", "")
                options = _get_attr(dp, "options", [])
                chosen = _get_attr(dp, "chosen", "")
                consequences = _get_attr(dp, "consequences", "")
                prompt_parts.append(f"\n**[{timestamp}] {commander}:**")
                prompt_parts.append(f"- Situation: {situation}")
                prompt_parts.append(f"- Options: {', '.join(options)}")
                prompt_parts.append(f"- Chosen: {chosen}")
                prompt_parts.append(f"- Result: {consequences}")

        # Add timeline
        if sheet.timeline:
            prompt_parts.append("\n## How It Unfolded")
            for event in sheet.timeline:
                timestamp = _get_attr(event, "timestamp", "")
                event_name = _get_attr(event, "event", "")
                prompt_parts.append(f"- [{timestamp}] {event_name}")

        # Add casualties
        if sheet.casualty_profile:
            cp = sheet.casualty_profile
            prompt_parts.append("\n## Outcome")
            if cp.total_casualties:
                prompt_parts.append(f"- Casualties: {cp.total_casualties:,}")
            if cp.casualty_distribution:
                prompt_parts.append(f"- Distribution: {cp.casualty_distribution}")

        # Add aftermath
        if sheet.aftermath:
            prompt_parts.append(f"\n## Aftermath: {sheet.aftermath}")

        # Add expert claims
        if prior_contributions:
            prompt_parts.append("\n## Expert Claims to Scrutinize")
            for contrib in prior_contributions:
                prompt_parts.append(f"\n**{contrib.expert}:**")
                for claim in contrib.domain_claims[:5]:
                    prompt_parts.append(f"- {claim}")

        prompt_parts.append(
            "\n\n# Your Task\n"
            "Scrutinize this scenario for:\n"
            "1. Implausible outcomes that need better explanation\n"
            "2. Decisions that seem too convenient or too foolish\n"
            "3. Missing friction (things that should have gone wrong)\n"
            "4. Internal inconsistencies\n\n"
            "Report ALL objections as a JSON object with the 'objections' array. "
            "Be the devil's advocate—ask the hard questions."
        )

        return "\n".join(prompt_parts)
