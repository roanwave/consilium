"""The Surgeon - Medical, wounds, and casualty expert."""

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


SURGEON_SYSTEM_PROMPT = """You are THE SURGEON, Chief Physician to the Royal Army.

You have cut more arrows from flesh than you can count. You have seen what every weapon
does to a man's body, and you have learned—through screaming and death—what can be
saved and what cannot. You think in wounds and recovery, in the terrible mathematics
of who dies immediately, who dies that night, and who might survive if the wound
doesn't fester. You know that battles are won by the living, but the dead have
lessons to teach.

## YOUR DOMAIN

You speak ONLY to:
- Casualty patterns based on weapons and tactics used
- What wounds different weapons inflict
- Medical treatment capabilities of the era
- Who dies on the field vs who dies later
- The ratio of killed to wounded to incapacitated
- How terrain and weather affect wound survival

You may propose deltas to these ScenarioSheet fields:
- casualty_profile (wound types, death patterns, medical capacity)
- casualty_profile.medical_notes (specific medical observations)

## HARD BOUNDARIES

You do NOT touch — ever:
- Strategic stakes (defer to Strategist)
- Tactical decisions (defer to Tactician)
- Supply logistics (defer to Logistician)
- Terrain analysis (defer to Geographer)
- Equipment specifications (defer to Armorer)
- Unit compositions or morale (defer to Herald)
- Timeline events (defer to Chronicler)

## YOUR VOICE

You speak as one who has held dying men. Your tone is clinical but not cold—you
have learned detachment to function, but you never forget these were lives. You
think in terms of anatomy and probability. You are matter-of-fact about death
because you have no other choice.

You use phrases like:
- "A wound like that, in this era, means..."
- "They'll lose more to fever than to steel."
- "The real killing happens when the line breaks."
- "If a man survives the first hour..."

## ERA MEDICAL CONSTRAINTS

You know what can and cannot be treated:
- ANCIENT: Basic wound binding, amputation, herbal remedies
- MEDIEVAL: Cauterization, crude surgery, no infection control
- EARLY MODERN: Slightly better surgery, laudanum, still high mortality
- INDUSTRIAL: Chloroform, beginning of antiseptics
- MODERN: Blood transfusion, antibiotics, trauma surgery

## CONDITIONAL QUESTION

You ask a question ONLY if:
- The casualty estimate seems wildly implausible for the forces described
- A massacre is implied but medical consequences aren't addressed
- There's a siege or extended operation where disease matters

For a straightforward battle, you can infer casualties from context.

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
        "Assessment of expected wound types",
        "Killed vs wounded ratio estimate",
        "Medical capacity or treatment limitations"
    ],
    "assumptions": [
        "What you assumed about casualties because it wasn't specified"
    ],
    "questions_remaining": [
        "Medical questions that still need answers, if any"
    ],
    "delta_requests": [
        {
            "field": "casualty_profile",
            "operation": "set",
            "value": {
                "winner_casualties_percent": 15,
                "loser_casualties_percent": 45,
                "total_casualties": 2500,
                "killed": 800,
                "wounded": 1700,
                "casualty_distribution": "Description of how casualties distributed across units",
                "notable_deaths": ["Notable casualty 1", "Notable casualty 2"],
                "medical_notes": "Detailed notes on wound types, treatment limitations, and post-battle mortality"
            },
            "rationale": "Based on weapons, tactics, and era medical capabilities"
        }
    ],
    "narrative_fragment": "Optional prose about the human cost for the final output"
}
```

IMPORTANT: You MUST include winner_casualties_percent and loser_casualties_percent as numbers (not strings).
Typical ranges: victor 5-20%, defeated force 20-60% depending on whether they rout or surrender.

Your delta_requests must ONLY target 'casualty_profile' fields.
"""


class Surgeon(Expert):
    """
    The Surgeon - Chief Physician to the Royal Army.

    Focuses on wounds, casualties, and medical realities of combat.
    Thinks in anatomy and probability, knows what each weapon does to flesh.
    """

    @property
    def config(self) -> ExpertConfig:
        return ExpertConfig(
            name="The Surgeon",
            codename="surgeon",
            title="Chief Physician to the Royal Army",
            model=ModelType.CLAUDE_SONNET,
            icon="",
            chamber=Chamber.CONSILIUM,
            description=(
                "Has cut more arrows from flesh than can be counted. Knows what "
                "each weapon does to a body and the terrible mathematics of survival."
            ),
        )

    @property
    def jurisdiction(self) -> Jurisdiction:
        return Jurisdiction(
            owns=[
                "casualty_profile",
                "casualty_profile.winner_casualties_percent",
                "casualty_profile.loser_casualties_percent",
                "casualty_profile.total_casualties",
                "casualty_profile.killed",
                "casualty_profile.wounded",
                "casualty_profile.casualty_distribution",
                "casualty_profile.notable_deaths",
                "casualty_profile.medical_notes",
            ],
            forbidden=[
                "version",
                "last_modified_by",
                "consistency_hash",
                "stakes",
                "terrain_weather",
                "timeline",
                "decision_points",
                "forces.equipment",
                "forces.composition",
                "forces.morale_factors",
                "aftermath",
            ],
        )

    def _build_system_prompt(self, sheet: ScenarioSheet) -> str:
        """Build the Surgeon's system prompt."""
        return SURGEON_SYSTEM_PROMPT

    def get_conditional_question(
        self,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
    ) -> ExpertQuestion | None:
        """
        Ask a question only if casualty implications are critically unclear.
        """
        # Check for implausible casualty estimates
        if sheet.casualty_profile:
            cp = sheet.casualty_profile
            if sheet.forces:
                total_engaged = sum(safe_int(safe_attr(f, 'total_strength', 0)) for f in sheet.forces.values())

                # Check for impossibly high casualties
                total_cas = safe_int(safe_attr(cp, 'total_casualties', 0))
                if total_cas and total_cas > total_engaged * 0.8:
                    return ExpertQuestion(
                        expert=self.config.codename,
                        question=(
                            f"The casualty estimate ({total_cas:,}) exceeds 80% of "
                            f"forces engaged ({total_engaged:,}). Is this an annihilation or "
                            "massacre scenario? Even catastrophic defeats rarely approach this."
                        ),
                        context=(
                            "Historical battles rarely exceed 50% casualties even in total "
                            "defeats. Higher requires special circumstances."
                        ),
                        default="Casualties reflect a severe defeat but not total annihilation.",
                    )

        # Check for siege without disease consideration
        if sheet.constraints:
            if any("siege" in c.lower() for c in sheet.constraints):
                if not sheet.casualty_profile or not sheet.casualty_profile.medical_notes:
                    return ExpertQuestion(
                        expert=self.config.codename,
                        question=(
                            "A siege is mentioned. Disease typically kills more than combat "
                            "in sieges. Are we accounting for dysentery, typhus, and fever?"
                        ),
                        context=(
                            "In pre-modern sieges, disease casualties often exceed combat "
                            "casualties by 3:1 or more."
                        ),
                        default="Disease is a significant factor; losses from illness exceed combat.",
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

        # Add forces (for casualty estimation)
        if sheet.forces:
            prompt_parts.append("\n**Forces:**")
            total = 0
            for side_id, force in sheet.forces.items():
                strength = safe_int(safe_attr(force, 'total_strength', 0))
                total += strength
                side_name = safe_attr(force, 'side_name', side_id)
                equipment = safe_attr(force, 'equipment', 'Unspecified')
                prompt_parts.append(f"\n*{side_name}:*")
                prompt_parts.append(f"  Strength: {strength:,}")
                prompt_parts.append(f"  Equipment: {equipment or 'Unspecified'}")
                composition = safe_attr(force, 'composition', [])
                if composition:
                    prompt_parts.append("  Composition:")
                    for unit in composition[:4]:
                        unit_count = safe_int(safe_attr(unit, 'count', 0))
                        unit_type = safe_attr(unit, 'unit_type', '')
                        prompt_parts.append(f"    - {unit_count:,} {unit_type}")
            prompt_parts.append(f"\n**Total engaged:** {total:,}")

        # Add terrain (affects wound treatment)
        if sheet.terrain_weather:
            tw = sheet.terrain_weather
            prompt_parts.append(f"\n**Terrain:** {enum_value(safe_attr(tw, 'terrain_type', ''))}")
            prompt_parts.append(f"**Weather:** {enum_value(safe_attr(tw, 'weather', ''))}")
            ground = safe_attr(tw, 'ground_conditions')
            if ground:
                prompt_parts.append(f"**Ground:** {ground}")

        # Add existing casualty profile
        if sheet.casualty_profile:
            cp = sheet.casualty_profile
            prompt_parts.append("\n**Current Casualty Profile:**")
            total_cas = safe_int(safe_attr(cp, 'total_casualties', 0))
            if total_cas:
                prompt_parts.append(f"  Total Casualties: {total_cas:,}")
            cas_dist = safe_attr(cp, 'casualty_distribution')
            if cas_dist:
                prompt_parts.append(f"  Distribution: {cas_dist}")
            med_notes = safe_attr(cp, 'medical_notes')
            if med_notes:
                prompt_parts.append(f"  Medical Notes: {med_notes}")

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
            "Assess the medical realities of this battle. What wounds will the weapons "
            "inflict? What's the ratio of killed to wounded? What can be treated and what "
            "cannot? How many will die after the battle from their wounds?\n\n"
            "Provide your analysis as a JSON object with domain_claims, assumptions, "
            "questions_remaining, delta_requests, and narrative_fragment."
        )

        return "\n".join(prompt_parts)
