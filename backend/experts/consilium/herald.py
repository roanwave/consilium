"""The Herald - Unit compositions, morale, and honor expert."""

from typing import Any

from backend.config import ModelType
from backend.experts.base import Expert, ExpertConfig, Jurisdiction
from backend.lib.models import (
    Chamber,
    ExpertContribution,
    ExpertQuestion,
    ScenarioSheet,
)


HERALD_SYSTEM_PROMPT = """You are THE HERALD, Master of Arms and Honor.

You know every banner on the field, every unit's lineage, every grudge that spans
generations. You understand that men don't fight for kings—they fight for their
comrades, for their honor, for the standards they march beneath. You think in
pride and shame, in the ancient enmities and debts of blood that make men stand
when reason screams retreat. You know which units will die where they stand and
which will break at the first serious pressure.

## YOUR DOMAIN

You speak ONLY to:
- Unit compositions and their characteristics
- Morale factors that affect fighting ability
- Honor obligations that constrain behavior
- Which units will stand and which might break
- The human factors that turn numbers into fighting men
- Regimental histories and rivalries

You may propose deltas to these ScenarioSheet fields:
- forces.*.composition (unit types and counts)
- forces.*.morale_factors (what affects their willingness to fight)
- stakes (ONLY honor/obligation aspects of stakes)

## HARD BOUNDARIES

You do NOT touch — ever:
- Strategic politics beyond honor (defer to Strategist)
- Tactical decisions (defer to Tactician)
- Supply and logistics (defer to Logistician)
- Terrain analysis (defer to Geographer)
- Equipment specifications (defer to Armorer)
- Medical details (defer to Surgeon)
- Command decisions (defer to Commander)
- Timeline events (defer to Chronicler)

## YOUR VOICE

You speak as one who has witnessed the extremes of human courage and cowardice.
Your tone mixes pride and melancholy—you celebrate valor but know its cost. You
think in terms of what makes men fight: loyalty, honor, fear of shame, love of
comrades. You understand that wars are fought by humans, not numbers.

You use phrases like:
- "These men carry three generations of grievance..."
- "They'll stand. Their fathers' fathers stood at..."
- "Mercenaries fight until the money runs out."
- "This unit has never retreated. That's a weight they carry."

## MORALE FACTORS

You consider:
- Professional soldiers vs conscripts vs mercenaries
- Units with proud histories vs green recruits
- Religious or ideological motivation
- Personal stake (defending home vs foreign adventure)
- Recent history (fresh from victory vs bloodied)
- Leadership loyalty (beloved commander vs hated one)
- Tribal/ethnic cohesion within units

## CONDITIONAL QUESTION

You ask a question ONLY if:
- Force composition is critically underspecified
- Morale situation seems implausible (elite troops routing easily)
- Honor constraints would change the battle significantly

If forces are adequately described, no question.

## OUTPUT FORMAT

Respond with a JSON object:
```json
{
    "domain_claims": [
        "Assessment of unit quality or morale",
        "Honor obligation or constraint",
        "Which units will stand or break"
    ],
    "assumptions": [
        "What you assumed about unit character because it wasn't specified"
    ],
    "questions_remaining": [
        "Questions about forces or morale that still need answers, if any"
    ],
    "delta_requests": [
        {
            "field": "forces.side_a.morale_factors",
            "operation": "set",
            "value": ["List of morale factors"],
            "rationale": "Why these factors apply"
        }
    ],
    "narrative_fragment": "Optional prose about the human element for the final output"
}
```

Your delta_requests must ONLY target force composition, morale factors, or honor-related stakes.
"""


class Herald(Expert):
    """
    The Herald - Master of Arms and Honor.

    Focuses on unit compositions, morale, honor obligations, and what makes men fight.
    Knows every banner and the weight of history each unit carries.
    """

    @property
    def config(self) -> ExpertConfig:
        return ExpertConfig(
            name="The Herald",
            codename="herald",
            title="Master of Arms and Honor",
            model=ModelType.CLAUDE_SONNET,
            icon="",
            chamber=Chamber.CONSILIUM,
            description=(
                "Knows every banner on the field. Understands that men fight for "
                "comrades and honor, not kings. Knows who will stand and who will break."
            ),
        )

    @property
    def jurisdiction(self) -> Jurisdiction:
        return Jurisdiction(
            owns=[
                "forces.side_a.composition",
                "forces.side_b.composition",
                "forces.side_a.morale_factors",
                "forces.side_b.morale_factors",
                "stakes",  # Honor/obligation aspects only
            ],
            forbidden=[
                "version",
                "last_modified_by",
                "consistency_hash",
                "terrain_weather",
                "timeline",
                "decision_points",
                "forces.equipment",
                "forces.supply_state",
                "casualty_profile.medical_notes",
                "aftermath",
            ],
        )

    def _build_system_prompt(self, sheet: ScenarioSheet) -> str:
        """Build the Herald's system prompt."""
        return HERALD_SYSTEM_PROMPT

    def get_conditional_question(
        self,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
    ) -> ExpertQuestion | None:
        """
        Ask a question only if force composition or morale is critically unclear.
        """
        # Check for forces without composition
        if sheet.forces:
            for side_id, force in sheet.forces.items():
                if force.total_strength > 3000 and not force.composition:
                    return ExpertQuestion(
                        expert=self.config.codename,
                        question=(
                            f"What types of troops make up {force.side_name}'s "
                            f"{force.total_strength:,} soldiers? Heavy infantry? Cavalry? "
                            "Archers? Levied peasants? The composition determines what "
                            "they can and cannot do."
                        ),
                        context=(
                            "An army's composition shapes every tactical option. "
                            "10,000 knights fight differently than 10,000 levies."
                        ),
                        default="A balanced force appropriate to the era and theater.",
                    )

            # Check for mixed professional/levy forces without morale clarity
            for side_id, force in sheet.forces.items():
                if force.composition:
                    has_elite = any(
                        "guard" in u.unit_type.lower()
                        or "elite" in u.unit_type.lower()
                        or "knight" in u.unit_type.lower()
                        for u in force.composition
                    )
                    has_levy = any(
                        "levy" in u.unit_type.lower()
                        or "peasant" in u.unit_type.lower()
                        or "militia" in u.unit_type.lower()
                        for u in force.composition
                    )
                    if has_elite and has_levy and not force.morale_factors:
                        return ExpertQuestion(
                            expert=self.config.codename,
                            question=(
                                f"{force.side_name} has both elite and levy troops. "
                                "How cohesive is this force? Do the elites fight alongside "
                                "the levies or consider them expendable?"
                            ),
                            context=(
                                "Mixed-quality forces often have internal tensions. "
                                "How they work together affects what they can achieve."
                            ),
                            default="The force operates as a unified whole under central command.",
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

        # Add forces with composition and morale focus
        if sheet.forces:
            prompt_parts.append("\n**Forces:**")
            for side_id, force in sheet.forces.items():
                prompt_parts.append(f"\n*{force.side_name}* ({force.total_strength:,}):")
                if force.commander:
                    prompt_parts.append(f"  Commander: {force.commander.name}")

                if force.composition:
                    prompt_parts.append("  Composition:")
                    for unit in force.composition:
                        quality = f" ({unit.quality})" if unit.quality else ""
                        prompt_parts.append(f"    - {unit.count:,} {unit.unit_type}{quality}")
                else:
                    prompt_parts.append("  Composition: Unspecified")

                if force.morale_factors:
                    prompt_parts.append(f"  Morale Factors: {', '.join(force.morale_factors)}")
                else:
                    prompt_parts.append("  Morale Factors: Unspecified")

        # Add terrain (affects morale in some cases)
        if sheet.terrain_weather:
            tw = sheet.terrain_weather
            prompt_parts.append(f"\n**Terrain:** {tw.terrain_type.value}")

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
            "Assess the human element of these forces. What is the quality and morale "
            "of each unit? What honor obligations constrain them? Which units will "
            "stand and which might break? What human factors will shape this battle?\n\n"
            "Provide your analysis as a JSON object with domain_claims, assumptions, "
            "questions_remaining, delta_requests, and narrative_fragment."
        )

        return "\n".join(prompt_parts)
