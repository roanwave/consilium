"""The Logistician - Supply, logistics, and attrition expert."""

from typing import Any

from backend.config import ModelType
from backend.experts.base import Expert, ExpertConfig, Jurisdiction
from backend.lib.models import (
    Chamber,
    ExpertContribution,
    ExpertQuestion,
    ScenarioSheet,
)


LOGISTICIAN_SYSTEM_PROMPT = """You are THE LOGISTICIAN, Quartermaster General.

You are obsessed with numbers that other men find tedious. How many wagons? How many days
of bread? How far can a horse march before it drops? You know that armies do not march on
courage—they march on grain, on fodder, on the slow crawl of the baggage train. You have
seen grand campaigns collapse not to enemy steel but to empty bellies and lame horses.

## YOUR DOMAIN

You speak ONLY to:
- Supply states and logistics constraints
- March rates and movement sustainability
- Attrition from non-combat causes (starvation, disease, desertion)
- Baggage train vulnerabilities
- How long an army can remain in the field
- The logistical feasibility of tactical plans

You may propose deltas to these ScenarioSheet fields:
- forces.*.supply_state (supply situation for each side)
- constraints (ONLY logistical constraints, not political or terrain)
- casualty_profile.casualty_distribution (non-combat attrition)

## HARD BOUNDARIES

You do NOT touch — ever:
- Strategic/political stakes (defer to Strategist)
- Tactical decisions (defer to Tactician)
- Terrain analysis (defer to Geographer)
- Equipment specifications (defer to Armorer)
- Combat wounds (defer to Surgeon)
- Unit compositions or morale (defer to Herald)
- Battle timeline events (defer to Chronicler)

## YOUR VOICE

You speak as one who counts beans while others dream of glory. Your tone is dry, precise,
sometimes pedantic. You find a kind of grim satisfaction in puncturing grandiose plans
with mundane arithmetic. You know that hungry men don't fight well, and starving men
don't fight at all.

You use phrases like:
- "The numbers don't support..."
- "At this consumption rate, they have perhaps..."
- "No army can sustain..."
- "Someone has to feed these men."

## REFERENCE NUMBERS

Use these baselines for your calculations:
- Food: ~1.5 kg per man per day
- Water: ~3 liters per man per day
- Horse fodder: ~5 kg per horse per day
- Mixed army march rate: 15-20 km/day
- Heavy baggage: 8-12 km/day
- Forced march: 30-40 km/day (sustainable 1-2 days max)

## CONDITIONAL QUESTION

You ask a question ONLY if:
- The army size seems unsupportable for the stated campaign duration
- Supply lines are mentioned but not quantified
- A siege or extended operation is implied without supply discussion

If logistics are adequately addressed or the battle is a single engagement, no question.

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
        "Logistical assessment of army sustainability",
        "Supply constraint that affects the battle",
        "Attrition estimate from non-combat factors"
    ],
    "assumptions": [
        "What you assumed about supply context because it wasn't specified"
    ],
    "questions_remaining": [
        "Logistical questions that still need answers, if any"
    ],
    "delta_requests": [
        {
            "field": "forces.side_a.supply_state",
            "operation": "set",
            "value": "Description of supply situation",
            "rationale": "Why this supply state"
        }
    ],
    "narrative_fragment": "Optional prose about logistical realities for the final output"
}
```

Your delta_requests must ONLY target supply-related fields or logistical constraints.
"""


class Logistician(Expert):
    """
    The Logistician - Quartermaster General.

    Focuses on supply, sustainability, and the unglamorous arithmetic of war.
    Knows that armies march on grain, not courage.
    """

    @property
    def config(self) -> ExpertConfig:
        return ExpertConfig(
            name="The Logistician",
            codename="logistician",
            title="Quartermaster General",
            model=ModelType.CLAUDE_SONNET,
            icon="📦",
            chamber=Chamber.CONSILIUM,
            description=(
                "Obsessed with the unglamorous arithmetic of war. Counts wagons, "
                "grain, and fodder while others dream of glory."
            ),
        )

    @property
    def jurisdiction(self) -> Jurisdiction:
        return Jurisdiction(
            owns=[
                "forces.side_a.supply_state",
                "forces.side_b.supply_state",
                "constraints",  # Logistical constraints only
                "casualty_profile.casualty_distribution",
            ],
            forbidden=[
                "version",
                "last_modified_by",
                "consistency_hash",
                "stakes",
                "terrain_weather",
                "timeline",
                "decision_points",
                "casualty_profile.medical_notes",
                "aftermath",
            ],
        )

    def _build_system_prompt(self, sheet: ScenarioSheet) -> str:
        """Build the Logistician's system prompt."""
        return LOGISTICIAN_SYSTEM_PROMPT

    def get_conditional_question(
        self,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
    ) -> ExpertQuestion | None:
        """
        Ask a question only if there's a critical supply ambiguity.
        """
        # Check for large armies without supply discussion
        total_troops = sum(f.total_strength for f in sheet.forces.values()) if sheet.forces else 0

        if total_troops > 30000:
            has_supply_constraint = any(
                "supply" in c.lower() or "forage" in c.lower() or "provision" in c.lower()
                for c in sheet.constraints
            )
            if not has_supply_constraint:
                return ExpertQuestion(
                    expert=self.config.codename,
                    question=(
                        f"With {total_troops:,} troops engaged, how are they being supplied? "
                        "Pre-positioned magazines? Local forage? A baggage train?"
                    ),
                    context=(
                        "An army this size consumes enormous quantities daily. "
                        "Supply method affects what operations are possible."
                    ),
                    default="Both armies have adequate supplies for a single pitched battle.",
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

        # Add forces with supply focus
        if sheet.forces:
            prompt_parts.append("\n**Forces:**")
            total = 0
            for side_id, force in sheet.forces.items():
                total += force.total_strength
                prompt_parts.append(f"\n*{force.side_name}:*")
                prompt_parts.append(f"  Strength: {force.total_strength:,}")
                prompt_parts.append(f"  Supply State: {force.supply_state or 'Unspecified'}")
                # Count cavalry/horses for fodder calculation
                cavalry_count = sum(
                    u.count for u in force.composition
                    if "cavalry" in u.unit_type.lower() or "horse" in u.unit_type.lower()
                )
                if cavalry_count:
                    prompt_parts.append(f"  Mounted troops: ~{cavalry_count:,}")

            prompt_parts.append(f"\n**Total troops engaged:** {total:,}")
            prompt_parts.append(f"**Daily food requirement:** ~{int(total * 1.5):,} kg")
            prompt_parts.append(f"**Daily water requirement:** ~{total * 3:,} liters")

        # Add terrain (affects foraging)
        if sheet.terrain_weather:
            tw = sheet.terrain_weather
            prompt_parts.append(f"\n**Terrain:** {tw.terrain_type.value}")
            prompt_parts.append(f"**Season:** {tw.season}")

        # Add existing constraints
        if sheet.constraints:
            prompt_parts.append("\n**Existing Constraints:**")
            for c in sheet.constraints:
                prompt_parts.append(f"- {c}")

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
            "Assess the logistical situation. How sustainable are these forces? "
            "What supply constraints affect the battle? What non-combat attrition "
            "should we expect?\n\n"
            "Provide your analysis as a JSON object with domain_claims, assumptions, "
            "questions_remaining, delta_requests, and narrative_fragment."
        )

        return "\n".join(prompt_parts)
