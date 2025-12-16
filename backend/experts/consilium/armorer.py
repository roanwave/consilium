"""The Armorer - Equipment, weapons, and armor expert."""

from typing import Any

from backend.config import ModelType
from backend.experts.base import Expert, ExpertConfig, Jurisdiction
from backend.lib.models import (
    Chamber,
    ExpertContribution,
    ExpertQuestion,
    ScenarioSheet,
)
from backend.lib.utils import enum_value, safe_attr, safe_int


ARMORER_SYSTEM_PROMPT = """You are THE ARMORER, Master of the King's Forges.

You have spent your life among the ringing of hammers and the hiss of quenching steel. You know
what a blade can do to mail, what a lance can do to plate, what a bodkin point can do to
anything. You think in metal and leather, in the weight a man carries and the protection he
gains. You know that equipment is not about technology—it's about the trade-offs a commander
makes between protection, mobility, and cost.

## YOUR DOMAIN

You speak ONLY to:
- Weapon types and their effectiveness against various armor
- Armor quality and its impact on casualties
- Equipment mismatches that will decide engagements
- What each side is carrying, and what it means
- The practical limits of what equipment allows
- Era-appropriate technology and its battlefield implications

You may propose deltas to these ScenarioSheet fields:
- forces.*.equipment (equipment descriptions for each side)
- forces.*.armor_quality (armor quality ratings)

## HARD BOUNDARIES

You do NOT touch — ever:
- Strategic/political stakes (defer to Strategist)
- Tactical decisions (defer to Tactician)
- Supply and logistics (defer to Logistician)
- Terrain analysis (defer to Geographer)
- Wound patterns (defer to Surgeon)
- Unit compositions beyond equipment (defer to Herald)
- Timeline events (defer to Chronicler)

## YOUR VOICE

You speak as a craftsman who respects good work and despises shoddy gear. Your tone is
technical but passionate—you can talk about the weight distribution of a hauberk or the
tempering of a blade with genuine enthusiasm. You take offense at anachronisms and
impossibilities. You think in terms of:
- What the gear allows vs what it forbids
- The trade-offs inherent in every choice
- What happens when steel meets steel

You use phrases like:
- "That mail won't stop a bodkin at thirty paces."
- "The weight alone will exhaust them before noon."
- "Whoever equipped these men understood that..."
- "No smith of this era could produce..."

## ERA CONSTRAINTS

You enforce technological plausibility:
- ANCIENT: Bronze/iron weapons, no plate, shields dominant
- EARLY_MEDIEVAL: Mail begins appearing, pattern-welded swords
- HIGH_MEDIEVAL: Mail standard, early plate elements, crossbows
- LATE_MEDIEVAL: Full plate, longbows, early firearms
- PIKE_AND_SHOT: Plate declining, arquebus/musket emerging
- MUSKET_ERA: Bayonets, no armor except cavalry cuirass
- RIFLE_ERA: Rifled muskets, percussion caps, no body armor
- MODERN: Automatic weapons, tanks, body armor returns

## CONDITIONAL QUESTION

You ask a question ONLY if:
- Equipment is specified that's clearly anachronistic for the era
- An equipment mismatch seems to guarantee one-sided slaughter without explanation
- Critical gear (like siege equipment) is implied but unspecified

If equipment is reasonably inferred from era and force types, no question.

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
        "Equipment assessment for one side",
        "Armor effectiveness analysis",
        "Critical equipment mismatch or advantage"
    ],
    "assumptions": [
        "What you assumed about equipment because it wasn't specified"
    ],
    "questions_remaining": [
        "Equipment questions that still need answers, if any"
    ],
    "delta_requests": [
        {
            "field": "forces.side_a.equipment",
            "operation": "set",
            "value": "Detailed equipment description",
            "rationale": "Why this equipment for this force"
        }
    ],
    "narrative_fragment": "Optional prose about arms and armor for the final output"
}
```

Your delta_requests must ONLY target equipment-related fields under 'forces'.
"""


class Armorer(Expert):
    """
    The Armorer - Master of the King's Forges.

    Focuses on equipment, weapons, armor, and the trade-offs of martial gear.
    Thinks in steel and leather, weight and protection.
    """

    @property
    def config(self) -> ExpertConfig:
        return ExpertConfig(
            name="The Armorer",
            codename="armorer",
            title="Master of the King's Forges",
            model=ModelType.CLAUDE_SONNET,
            icon="",
            chamber=Chamber.CONSILIUM,
            description=(
                "Master craftsman who thinks in steel and leather. Knows what "
                "a blade can do to mail and enforces technological plausibility."
            ),
        )

    @property
    def jurisdiction(self) -> Jurisdiction:
        return Jurisdiction(
            owns=[
                "forces.side_a.equipment",
                "forces.side_b.equipment",
                "forces.side_a.armor_quality",
                "forces.side_b.armor_quality",
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
                "forces.supply_state",
                "forces.morale_factors",
                "aftermath",
            ],
        )

    def _build_system_prompt(self, sheet: ScenarioSheet) -> str:
        """Build the Armorer's system prompt."""
        return ARMORER_SYSTEM_PROMPT

    def get_conditional_question(
        self,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
    ) -> ExpertQuestion | None:
        """
        Ask a question only if there's a critical equipment ambiguity.
        """
        # Check for equipment anachronisms
        if sheet.era and sheet.forces:
            era = enum_value(sheet.era)
            for side_id, force in sheet.forces.items():
                equipment = safe_attr(force, 'equipment', '') or ""
                equipment_lower = equipment.lower()
                side_name = safe_attr(force, 'side_name', side_id)

                # Check for obvious anachronisms
                if era in ["ancient", "early_medieval"]:
                    if any(
                        word in equipment_lower
                        for word in ["plate armor", "longbow", "crossbow"]
                    ):
                        return ExpertQuestion(
                            expert=self.config.codename,
                            question=(
                                f"The equipment described for {side_name} seems too advanced "
                                f"for the {era} era. Can you clarify what armor and weapons they "
                                "actually have?"
                            ),
                            context=(
                                "Full plate and longbows don't exist yet. I need to know what "
                                "era-appropriate gear they're actually carrying."
                            ),
                            default=f"Standard {era} equipment appropriate to their force type.",
                        )

                if era in ["ancient", "early_medieval", "high_medieval", "late_medieval"]:
                    if any(
                        word in equipment_lower
                        for word in ["musket", "rifle", "firearm", "gun"]
                    ):
                        return ExpertQuestion(
                            expert=self.config.codename,
                            question=(
                                f"Firearms are mentioned for {side_name}, but the era is "
                                f"{era}. Are we using firearms, or should I assume era-appropriate "
                                "missile weapons?"
                            ),
                            context=(
                                "Gunpowder weapons fundamentally change the battlefield. "
                                "I need to know what's actually being used."
                            ),
                            default="Era-appropriate missile weapons (bows, crossbows) instead of firearms.",
                        )

        # Check for completely unspecified equipment on large forces
        if sheet.forces:
            for side_id, force in sheet.forces.items():
                strength = safe_int(safe_attr(force, 'total_strength', 0))
                equipment = safe_attr(force, 'equipment', '')
                side_name = safe_attr(force, 'side_name', side_id)
                if strength > 5000 and not equipment:
                    return ExpertQuestion(
                        expert=self.config.codename,
                        question=(
                            f"What arms and armor does {side_name} carry? "
                            "Professional soldiers with quality gear? Levies with whatever "
                            "they brought?"
                        ),
                        context=(
                            "Equipment quality dramatically affects casualties. A force in mail "
                            "against one in gambeson is a very different battle."
                        ),
                        default="Mixed quality appropriate to the force composition.",
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
            f"**Era:** {enum_value(sheet.era, 'Unspecified')}",
            f"**Theater:** {sheet.theater or 'Unspecified'}",
        ]

        # Add forces with equipment focus
        if sheet.forces:
            prompt_parts.append("\n**Forces:**")
            for side_id, force in sheet.forces.items():
                side_name = safe_attr(force, 'side_name', side_id)
                strength = safe_int(safe_attr(force, 'total_strength', 0))
                equipment = safe_attr(force, 'equipment', 'Unspecified')
                armor_quality = safe_attr(force, 'armor_quality', 'Unspecified')
                prompt_parts.append(f"\n*{side_name}:*")
                prompt_parts.append(f"  Strength: {strength:,}")
                prompt_parts.append(f"  Equipment: {equipment or 'Unspecified'}")
                prompt_parts.append(f"  Armor Quality: {armor_quality or 'Unspecified'}")

                # Show composition for equipment inference
                composition = safe_attr(force, 'composition', []) or []
                if composition:
                    prompt_parts.append("  Composition:")
                    for unit in composition[:5]:
                        unit_count = safe_int(safe_attr(unit, 'count', 0))
                        unit_type = safe_attr(unit, 'unit_type', '')
                        prompt_parts.append(f"    - {unit_count:,} {unit_type}")

        # Add terrain (affects equipment utility)
        if sheet.terrain_weather:
            tw = sheet.terrain_weather
            prompt_parts.append(f"\n**Terrain:** {enum_value(safe_attr(tw, 'terrain_type', ''))}")
            prompt_parts.append(f"**Weather:** {enum_value(safe_attr(tw, 'weather', ''))}")
            prompt_parts.append(f"**Ground:** {safe_attr(tw, 'ground_conditions', 'Unspecified')}")

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
            "Assess the equipment of both forces. What are they carrying? What does "
            "their gear allow them to do, and what does it forbid? Are there critical "
            "equipment mismatches that will decide the battle?\n\n"
            "Provide your analysis as a JSON object with domain_claims, assumptions, "
            "questions_remaining, delta_requests, and narrative_fragment."
        )

        return "\n".join(prompt_parts)
