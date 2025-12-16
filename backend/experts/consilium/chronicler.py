"""The Chronicler - Historical context and narrative expert."""

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


CHRONICLER_SYSTEM_PROMPT = """You are THE CHRONICLER, Keeper of the Kingdom's Histories.

You have spent decades in the archives, reading accounts of battles fought and kingdoms
fallen. You see patterns that others miss—how this engagement echoes that ancient defeat,
how these commanders repeat the mistakes of their predecessors. You know that history
does not repeat, but it rhymes. You think in parallels and precedents, in the long arc
of cause and effect that extends beyond any single battle.

## YOUR DOMAIN

You speak ONLY to:
- Historical parallels and precedents
- How this battle fits into the larger sweep of history
- What sources would record about this engagement
- The narrative arc from cause to consequence
- The theater and geographic context
- Magic systems and their historical constraints (if present)

You may propose deltas to these ScenarioSheet fields:
- theater (geographic/regional context)
- magic (if magic is present in the scenario)

## HARD BOUNDARIES

You do NOT touch — ever:
- Strategic stakes (defer to Strategist)
- Aftermath and open risks (defer to Strategist)
- Tactical decisions and timeline (defer to Tactician)
- Supply and logistics (defer to Logistician)
- Terrain analysis (defer to Geographer)
- Equipment specifications (defer to Armorer)
- Medical details (defer to Surgeon)
- Command decisions (defer to Commander)
- Unit compositions (defer to Herald)

## YOUR VOICE

You speak as one who has read a thousand accounts of war. Your tone is scholarly but
not dry—you find meaning in patterns and lessons in failures. You think across time,
connecting this battle to others centuries apart. You see the present as history
being written.

You use phrases like:
- "This echoes the engagement at..."
- "History suggests that such circumstances lead to..."
- "The chroniclers will record this as..."
- "Like [historical figure], this commander faces..."

## HISTORICAL PATTERNS

You draw on patterns across military history:
- Defending forces in strong terrain succeed more often than attackers expect
- Pursuit after victory often causes more casualties than the battle itself
- Supply failures have broken more campaigns than enemy action
- New weapons take time to be used effectively
- Overconfidence after early success leads to catastrophe

## CONDITIONAL QUESTION

You ask a question ONLY if:
- The historical setting is unclear or inconsistent
- The outcome seems to contradict historical patterns without explanation
- There's a claimed historical basis that seems implausible

If the scenario is internally consistent, you can work with the provided framework.

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
        "Historical parallel or precedent",
        "How this echoes past engagements",
        "What the chronicles will record"
    ],
    "assumptions": [
        "What you assumed about historical context because it wasn't specified"
    ],
    "questions_remaining": [
        "Historical questions that still need answers, if any"
    ],
    "delta_requests": [
        {
            "field": "theater",
            "operation": "set",
            "value": "Geographic and regional context",
            "rationale": "Based on historical patterns"
        }
    ],
    "narrative_fragment": "Prose about historical significance for the final output - THIS IS YOUR MAIN CONTRIBUTION"
}
```

IMPORTANT: Your main contribution is the narrative_fragment - provide rich historical context and narrative prose.

Your delta_requests may ONLY target 'theater' or 'magic'.
"""


class Chronicler(Expert):
    """
    The Chronicler - Keeper of the Kingdom's Histories.

    Focuses on historical parallels, timeline, and aftermath.
    Sees patterns across centuries and connects battles to their precedents.
    """

    @property
    def config(self) -> ExpertConfig:
        return ExpertConfig(
            name="The Chronicler",
            codename="chronicler",
            title="Keeper of the Kingdom's Histories",
            model=ModelType.CLAUDE_SONNET,
            icon="",
            chamber=Chamber.CONSILIUM,
            description=(
                "Has spent decades in the archives. Sees patterns others miss, "
                "connects this battle to precedents across centuries."
            ),
        )

    @property
    def jurisdiction(self) -> Jurisdiction:
        return Jurisdiction(
            owns=[
                "theater",
                "magic",
            ],
            forbidden=[
                "version",
                "last_modified_by",
                "consistency_hash",
                "stakes",
                "terrain_weather",
                "decision_points",
                "forces.equipment",
                "forces.composition",
                "casualty_profile.medical_notes",
                "timeline",  # Tactician owns this
                "aftermath",  # Strategist owns this
            ],
        )

    def _build_system_prompt(self, sheet: ScenarioSheet) -> str:
        """Build the Chronicler's system prompt."""
        return CHRONICLER_SYSTEM_PROMPT

    def get_conditional_question(
        self,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
    ) -> ExpertQuestion | None:
        """
        Ask a question only if historical context is critically unclear.
        """
        # Check for missing era
        if not sheet.era:
            return ExpertQuestion(
                expert=self.config.codename,
                question=(
                    "What era is this battle set in? The historical context shapes "
                    "everything from available weapons to tactical expectations."
                ),
                context=(
                    "Without knowing the era, I cannot identify appropriate parallels "
                    "or assess whether the scenario is historically plausible."
                ),
                default="High Medieval (roughly 1100-1300 CE)",
            )

        # Check for outcome that contradicts forces
        if sheet.forces and sheet.aftermath:
            strengths = list(sheet.forces.values())
            if len(strengths) >= 2:
                larger = max(strengths, key=lambda f: safe_int(safe_attr(f, 'total_strength', 0)))
                smaller = min(strengths, key=lambda f: safe_int(safe_attr(f, 'total_strength', 0)))
                larger_strength = safe_int(safe_attr(larger, 'total_strength', 0))
                smaller_strength = safe_int(safe_attr(smaller, 'total_strength', 0))
                ratio = larger_strength / max(smaller_strength, 1)

                aftermath_lower = sheet.aftermath.lower() if sheet.aftermath else ""
                smaller_name = safe_attr(smaller, 'side_name', '').lower()
                larger_name = safe_attr(larger, 'side_name', '').lower()

                # Check if smaller force wins decisively against the odds
                smaller_display_name = safe_attr(smaller, 'side_name', 'Unknown')
                if ratio > 2.5 and smaller_name in aftermath_lower and "victory" in aftermath_lower:
                    return ExpertQuestion(
                        expert=self.config.codename,
                        question=(
                            f"The aftermath suggests {smaller_display_name} achieves victory "
                            f"against {ratio:.1f}:1 odds. What historical circumstance "
                            "enables this? Terrain advantage? Superior quality? Surprise?"
                        ),
                        context=(
                            "Such outcomes occur historically but always have specific causes. "
                            "Understanding why helps construct the narrative."
                        ),
                        default="Defensive terrain advantage and superior troop quality.",
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
            f"**Stakes:** {sheet.stakes or 'Unspecified'}",
        ]

        # Add forces overview
        if sheet.forces:
            prompt_parts.append("\n**Forces:**")
            for side_id, force in sheet.forces.items():
                side_name = safe_attr(force, 'side_name', side_id)
                strength = safe_int(safe_attr(force, 'total_strength', 0))
                prompt_parts.append(f"- {side_name}: {strength:,}")
                commander = safe_attr(force, 'commander', None)
                if commander:
                    cmd_name = safe_attr(commander, 'name', 'Unknown')
                    prompt_parts.append(f"  Led by {cmd_name}")

        # Add terrain
        if sheet.terrain_weather:
            tw = sheet.terrain_weather
            prompt_parts.append(f"\n**Terrain:** {enum_value(safe_attr(tw, 'terrain_type', ''))}")
            prompt_parts.append(f"**Defining Feature:** {safe_attr(tw, 'defining_feature', 'Unspecified')}")

        # Add existing timeline
        if sheet.timeline:
            prompt_parts.append("\n**Current Timeline:**")
            for event in sheet.timeline:
                evt_ts = safe_attr(event, 'timestamp', '')
                evt_name = safe_attr(event, 'event', '')
                prompt_parts.append(f"- [{evt_ts}] {evt_name}")

        # Add existing aftermath
        if sheet.aftermath:
            prompt_parts.append(f"\n**Current Aftermath:** {sheet.aftermath}")

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
            "Place this battle in historical context. What parallels exist in history? "
            "What phases will the battle pass through? What will be the aftermath "
            "beyond the immediate result? What will the chronicles record?\n\n"
            "Provide your analysis as a JSON object with domain_claims, assumptions, "
            "questions_remaining, delta_requests, and narrative_fragment."
        )

        return "\n".join(prompt_parts)
