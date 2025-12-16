"""The Tactician - Military tactics and battlefield decisions expert."""

from typing import Any

from backend.config import ModelType
from backend.experts.base import Expert, ExpertConfig, Jurisdiction
from backend.lib.models import (
    Chamber,
    ExpertContribution,
    ExpertQuestion,
    ScenarioSheet,
)


TACTICIAN_SYSTEM_PROMPT = """You are THE TACTICIAN, Veteran Commander of the Line.

You have survived thirty years of war. You have stood in the shield wall when it broke,
ridden in charges that should have died, and watched good plans dissolve in the chaos of
contact. You think in steel and blood, in the geometry of death. Where others see armies,
you see formations, angles of attack, killing grounds, and the terrible arithmetic of
who can bring more blades to bear.

## YOUR DOMAIN

You speak ONLY to:
- Tactical phases of the battle (what happens, in what order, why)
- Decision points where commanders must choose under uncertainty
- Formation choices and their consequences
- The geometry of the battlefield (how terrain shapes tactical options)
- What information commanders have vs what they THINK they have
- The friction of combat (what goes wrong, and why)

You may propose deltas to these ScenarioSheet fields:
- decision_points (when, who, what options, what's chosen)
- timeline (tactical phases and events)

## HARD BOUNDARIES

You do NOT touch — ever:
- Strategic/political stakes (defer to Strategist)
- Supply and logistics (defer to Logistician)
- Terrain details beyond tactical relevance (defer to Geographer)
- Equipment specifications (defer to Armorer)
- Wound patterns and medical details (defer to Surgeon)
- Unit histories and morale factors (defer to Herald)
- Campaign consequences (defer to Chronicler)

## YOUR VOICE

You speak as one who has paid the blood price for other men's plans. Your tone is blunt,
practical, sometimes bitter. You have no patience for theorists who have never heard the
sound a man makes when the spear finds his belly. You think in terms of:
- What CAN be done vs what SHOULD be done
- What the commander knows vs what he thinks he knows
- How plans fail (they always do)

You use phrases like:
- "The line won't hold if..."
- "That's when the killing starts."
- "No plan survives first contact."
- "The question isn't whether it fails, but when and how badly."

## CONDITIONAL QUESTION

You ask a question ONLY if:
- There's a critical tactical ambiguity (open field vs constrained terrain?)
- Commander competence gap is extreme and unexplained
- The force ratio makes the battle inexplicable without special circumstances

If the tactical setup is clear enough to work with, you have no question.

## DELTA OPERATIONS (MUST USE EXACTLY)
When proposing changes via delta_requests, use ONLY these operation values:
- "set": Replace the entire field value
- "append": Add to a list field
- "modify": Update specific nested properties

DO NOT use "add", "replace", "update", or any other operation names.

## OUTPUT FORMAT

Respond with a JSON object:
```json
{
    "domain_claims": [
        "Tactical assertion about how the battle unfolds",
        "Decision point analysis",
        "Formation or maneuver assessment"
    ],
    "assumptions": [
        "What you assumed about tactical context because it wasn't specified"
    ],
    "questions_remaining": [
        "Tactical questions that still need answers, if any"
    ],
    "delta_requests": [
        {
            "field": "decision_points",
            "operation": "append",
            "value": {
                "timestamp": "When",
                "commander": "Who decides",
                "situation": "What they face",
                "options": ["Option A", "Option B"],
                "chosen": "What was chosen",
                "rationale": "Why",
                "consequences": "What resulted"
            },
            "rationale": "Why this decision point matters"
        }
    ],
    "narrative_fragment": "Optional prose about the tactical flow for the final output"
}
```

Your delta_requests must ONLY target 'decision_points' or 'timeline'.
Any delta to other fields will be rejected.
"""


class Tactician(Expert):
    """
    The Tactician - Veteran Commander of the Line.

    Focuses on battlefield decisions, tactical phases, and the geometry of combat.
    Thinks in steel and blood, not politics.
    """

    @property
    def config(self) -> ExpertConfig:
        return ExpertConfig(
            name="The Tactician",
            codename="tactician",
            title="Veteran Commander of the Line",
            model=ModelType.CLAUDE_SONNET,
            icon="⚔️",
            chamber=Chamber.CONSILIUM,
            description=(
                "Thirty years of war experience. Thinks in formations, angles of attack, "
                "and the terrible arithmetic of who brings more blades to bear."
            ),
        )

    @property
    def jurisdiction(self) -> Jurisdiction:
        return Jurisdiction(
            owns=[
                "decision_points",
                "timeline",
            ],
            forbidden=[
                "version",
                "last_modified_by",
                "consistency_hash",
                "stakes",
                "forces.supply_state",
                "terrain_weather",
                "casualty_profile.medical_notes",
                "aftermath",
            ],
        )

    def _build_system_prompt(self, sheet: ScenarioSheet) -> str:
        """Build the Tactician's system prompt."""
        return TACTICIAN_SYSTEM_PROMPT

    def get_conditional_question(
        self,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
    ) -> ExpertQuestion | None:
        """
        Ask a question only if there's a critical tactical ambiguity.
        """
        # Check for extreme force ratio without explanation
        if sheet.forces and len(sheet.forces) >= 2:
            strengths = [f.total_strength for f in sheet.forces.values()]
            if len(strengths) >= 2:
                ratio = max(strengths) / max(min(strengths), 1)
                if ratio > 3:
                    return ExpertQuestion(
                        expert=self.config.codename,
                        question=(
                            f"The force ratio is roughly {ratio:.1f}:1. What circumstances "
                            "allow the smaller force to even consider battle? Defensive "
                            "terrain? Desperation? Relief force coming?"
                        ),
                        context=(
                            "At this ratio, battle only makes sense with significant "
                            "mitigating factors."
                        ),
                        default="The smaller force is defending critical terrain they cannot abandon.",
                    )

        # Check if terrain is critical but unclear
        if sheet.terrain_weather:
            terrain = sheet.terrain_weather.terrain_type.value
            if terrain in ["river_crossing", "mountains", "marsh"] and not sheet.decision_points:
                return ExpertQuestion(
                    expert=self.config.codename,
                    question=(
                        f"The {terrain} terrain heavily constrains tactics. Is the attacker "
                        "committed to forcing the position, or could they maneuver around it?"
                    ),
                    context=(
                        "This terrain type demands specific tactical approaches that "
                        "shape the entire battle."
                    ),
                    default="The attacker must force the position; no practical alternative exists.",
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
            f"**Stakes:** {sheet.stakes or 'Unspecified'}",
        ]

        # Add terrain (critical for tactics)
        if sheet.terrain_weather:
            tw = sheet.terrain_weather
            prompt_parts.append(f"\n**Terrain:** {tw.terrain_type.value}")
            prompt_parts.append(f"**Defining Feature:** {tw.defining_feature}")
            if tw.weather:
                prompt_parts.append(f"**Weather:** {tw.weather.value}")
            if tw.ground_conditions:
                prompt_parts.append(f"**Ground:** {tw.ground_conditions}")

        # Add forces (essential for tactical analysis)
        if sheet.forces:
            prompt_parts.append("\n**Forces:**")
            for side_id, force in sheet.forces.items():
                prompt_parts.append(f"\n*{force.side_name}* ({force.total_strength:,} total):")
                if force.commander:
                    prompt_parts.append(
                        f"  Commander: {force.commander.name} ({force.commander.competence.value})"
                    )
                if force.composition:
                    for unit in force.composition[:5]:
                        prompt_parts.append(f"  - {unit.count:,} {unit.unit_type}")

        # Add existing decision points
        if sheet.decision_points:
            prompt_parts.append("\n**Existing Decision Points:**")
            for dp in sheet.decision_points:
                prompt_parts.append(f"- [{dp.timestamp}] {dp.commander}: {dp.situation[:80]}...")

        # Add existing timeline
        if sheet.timeline:
            prompt_parts.append("\n**Existing Timeline:**")
            for event in sheet.timeline[:5]:
                prompt_parts.append(f"- [{event.timestamp}] {event.event[:80]}...")

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
            "Analyze the tactical flow of this battle. What are the critical decision points? "
            "How do formations meet and break? What does each commander know, and what do they "
            "think they know? Where does the plan fail?\n\n"
            "Provide your analysis as a JSON object with domain_claims, assumptions, "
            "questions_remaining, delta_requests, and narrative_fragment."
        )

        return "\n".join(prompt_parts)
