"""The Geographer - Terrain, weather, and battlefield environment expert."""

from typing import Any

from backend.config import ModelType
from backend.experts.base import Expert, ExpertConfig, Jurisdiction
from backend.lib.models import (
    Chamber,
    ExpertContribution,
    ExpertQuestion,
    ScenarioSheet,
)


GEOGRAPHER_SYSTEM_PROMPT = """You are THE GEOGRAPHER, Surveyor of the King's Domains.

You see what others miss. Where a soldier sees a hill, you see a reverse slope that hides
movement, a crest that silhouettes defenders, drainage that turns to mud in rain. You have
walked battlefields before and after, and you know that the ground decides more battles
than the generals do. The earth is patient, and it punishes those who ignore it.

## YOUR DOMAIN

You speak ONLY to:
- Terrain features and their tactical significance
- Weather conditions and their effects on combat
- Visibility, footing, and movement constraints
- How the ground channels, blocks, or enables maneuver
- What the terrain makes easy, and what it makes impossible
- The difference between the map and the reality

You may propose deltas to these ScenarioSheet fields:
- terrain_weather (all sub-fields)
- constraints (ONLY terrain-based constraints)

## HARD BOUNDARIES

You do NOT touch — ever:
- Strategic/political stakes (defer to Strategist)
- Tactical decisions beyond terrain influence (defer to Tactician)
- Supply and logistics (defer to Logistician)
- Equipment specifications (defer to Armorer)
- Casualty details (defer to Surgeon)
- Unit compositions or morale (defer to Herald)
- Timeline events (defer to Chronicler)

## YOUR VOICE

You speak as one who trusts dirt more than men. Your tone is observational, almost
meditative, but with sudden sharp insights about what the ground will do to any plan
that ignores it. You think in terms of:
- What the ground allows vs what it forbids
- What looks passable but isn't
- How weather transforms terrain

You use phrases like:
- "The ground here will..."
- "In rain, this becomes..."
- "The approach looks open, but..."
- "Any commander who ignores this slope will discover..."

## CONDITIONAL QUESTION

You ask a question ONLY if:
- The terrain type is specified but the defining feature is generic or missing
- Weather is critical to the scenario but unspecified
- The terrain seems inconsistent with the described action

If terrain is adequately described for the battle's purpose, no question.

## OUTPUT FORMAT

Respond with a JSON object:
```json
{
    "domain_claims": [
        "Terrain assessment and its tactical significance",
        "Weather effect on the battle",
        "Movement or visibility constraint"
    ],
    "assumptions": [
        "What you assumed about terrain because it wasn't specified"
    ],
    "questions_remaining": [
        "Terrain questions that still need answers, if any"
    ],
    "delta_requests": [
        {
            "field": "terrain_weather.features",
            "operation": "append",
            "value": {
                "name": "Feature name",
                "description": "What it is",
                "tactical_impact": "How it affects the battle"
            },
            "rationale": "Why this feature matters"
        }
    ],
    "narrative_fragment": "Optional prose about the terrain for the final output"
}
```

Your delta_requests must ONLY target 'terrain_weather' or terrain-based 'constraints'.
"""


class Geographer(Expert):
    """
    The Geographer - Surveyor of the King's Domains.

    Focuses on terrain, weather, and how the ground shapes battle.
    Sees what others miss in the landscape.
    """

    @property
    def config(self) -> ExpertConfig:
        return ExpertConfig(
            name="The Geographer",
            codename="geographer",
            title="Surveyor of the King's Domains",
            model=ModelType.CLAUDE_SONNET,
            icon="🗺️",
            chamber=Chamber.CONSILIUM,
            description=(
                "Sees what others miss in the landscape. Knows that the ground "
                "decides more battles than generals do."
            ),
        )

    @property
    def jurisdiction(self) -> Jurisdiction:
        return Jurisdiction(
            owns=[
                "terrain_weather",
                "constraints",  # Terrain-based constraints only
            ],
            forbidden=[
                "version",
                "last_modified_by",
                "consistency_hash",
                "stakes",
                "forces",
                "timeline",
                "decision_points",
                "casualty_profile",
                "aftermath",
            ],
        )

    def _build_system_prompt(self, sheet: ScenarioSheet) -> str:
        """Build the Geographer's system prompt."""
        return GEOGRAPHER_SYSTEM_PROMPT

    def get_conditional_question(
        self,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
    ) -> ExpertQuestion | None:
        """
        Ask a question only if terrain is critically underspecified.
        """
        if sheet.terrain_weather:
            tw = sheet.terrain_weather
            # Check if defining feature is too generic
            generic_features = ["flat", "open", "normal", "typical", "standard"]
            if tw.defining_feature and tw.defining_feature.lower() in generic_features:
                return ExpertQuestion(
                    expert=self.config.codename,
                    question=(
                        f"The {tw.terrain_type.value} terrain needs a defining feature. "
                        "What makes THIS battlefield distinct? A ridge? A stream? "
                        "A treeline? Ancient earthworks?"
                    ),
                    context=(
                        "Every historical battlefield has features that shaped the "
                        "fighting. Generic terrain produces generic battles."
                    ),
                    default="A gentle ridge runs across the likely line of contact.",
                )

            # Check for weather-sensitive terrain without weather
            if tw.terrain_type.value in ["marsh", "river_crossing", "forest"]:
                if tw.weather.value == "clear" and not tw.ground_conditions:
                    return ExpertQuestion(
                        expert=self.config.codename,
                        question=(
                            f"For {tw.terrain_type.value} terrain, recent weather matters. "
                            "Has it rained recently? Is the ground firm or soft?"
                        ),
                        context=(
                            "This terrain type is heavily affected by moisture. "
                            "Ground conditions could change everything."
                        ),
                        default="The ground is firm from a dry spell.",
                    )

        return None

    def _build_user_prompt(
        self,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
        prior_contributions: list[ExpertContribution],
    ) -> str:
        """Build the user prompt with scenario context."""
        prompt_parts = [
            "# Current Scenario\n",
            f"**Era:** {sheet.era.value if sheet.era else 'Unspecified'}",
            f"**Theater:** {sheet.theater or 'Unspecified'}",
        ]

        # Add existing terrain info
        if sheet.terrain_weather:
            tw = sheet.terrain_weather
            prompt_parts.append("\n**Current Terrain Description:**")
            prompt_parts.append(f"  Type: {tw.terrain_type.value}")
            prompt_parts.append(f"  Defining Feature: {tw.defining_feature or 'Unspecified'}")
            prompt_parts.append(f"  Weather: {tw.weather.value}")
            prompt_parts.append(f"  Visibility: {tw.visibility}")
            prompt_parts.append(f"  Ground Conditions: {tw.ground_conditions}")
            prompt_parts.append(f"  Time of Day: {tw.time_of_day}")
            prompt_parts.append(f"  Season: {tw.season}")

            if tw.features:
                prompt_parts.append("\n  Existing Features:")
                for f in tw.features:
                    prompt_parts.append(f"    - {f.name}: {f.tactical_impact}")

            if tw.what_matters:
                prompt_parts.append(f"\n  What Matters: {', '.join(tw.what_matters)}")
            if tw.what_doesnt:
                prompt_parts.append(f"  What Doesn't: {', '.join(tw.what_doesnt)}")

        # Add forces (for scale/frontage considerations)
        if sheet.forces:
            total = sum(f.total_strength for f in sheet.forces.values())
            prompt_parts.append(f"\n**Total troops to fit on this ground:** {total:,}")

        # Add relevant answers
        if answers:
            for key in ["terrain_type", "terrain_feature"]:
                if key in answers:
                    prompt_parts.append(f"\n**From interrogation - {key}:** {answers[key]}")

        # Add prior contributions
        if prior_contributions:
            prompt_parts.append("\n**Prior Expert Contributions This Round:**")
            for contrib in prior_contributions:
                if contrib.domain_claims:
                    prompt_parts.append(f"\n*{contrib.expert}:*")
                    for claim in contrib.domain_claims[:3]:
                        prompt_parts.append(f"- {claim}")

        prompt_parts.append(
            "\n\n# Your Task\n"
            "Analyze the terrain and weather. What does the ground allow? What does it forbid? "
            "What features will shape the fighting? How do conditions affect visibility, "
            "movement, and combat?\n\n"
            "Provide your analysis as a JSON object with domain_claims, assumptions, "
            "questions_remaining, delta_requests, and narrative_fragment."
        )

        return "\n".join(prompt_parts)
