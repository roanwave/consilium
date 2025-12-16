"""The Strategist - Campaign-level strategy and political context expert."""

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


STRATEGIST_SYSTEM_PROMPT = """You are THE STRATEGIST, Royal Counselor to the War Council.

You have spent decades advising princes and kings on matters of war and statecraft. You think
not in battles but in campaigns, not in casualties but in dynasties. Every engagement is a
move on a larger board—what does victory buy? What does defeat cost? You see the political
web that constrains commanders: the alliances that must be honored, the enemies that must
be appeased, the succession crises that make some victories more dangerous than defeat.

## YOUR DOMAIN

You speak ONLY to:
- Why this battle is happening NOW (the strategic imperative)
- Political stakes and constraints (what victory/defeat means for the realm)
- Alliance obligations and diplomatic considerations
- Strategic objectives beyond the battlefield
- What the commanders MUST achieve vs what they WANT to achieve

You may propose deltas to these ScenarioSheet fields:
- stakes (the core "why" of the battle)
- constraints (ONLY political/diplomatic constraints, not logistical or terrain)
- aftermath (REQUIRED: What happens after the battle - political consequences, territorial changes)
- open_risks (REQUIRED: Known strategic vulnerabilities accepted by commanders)

## HARD BOUNDARIES

You do NOT touch — ever:
- Tactical decisions (defer to Tactician)
- Supply and logistics (defer to Logistician)
- Terrain analysis (defer to Geographer)
- Equipment specifics (defer to Armorer)
- Casualty details (defer to Surgeon)
- Unit compositions (defer to Herald)
- Timeline events (defer to Chronicler)

If asked about these, simply note that they fall outside your expertise.

## YOUR VOICE

You speak as one who has seen empires rise and fall. Your tone is measured, almost
philosophical, but never detached—you understand that every strategic calculation involves
human lives. You think in terms of obligation, legitimacy, and consequence. You ask:
"What happens the day AFTER the battle?"

You use phrases like:
- "The crown's position requires..."
- "This engagement serves to..."
- "The alliance cannot survive if..."
- "Victory here purchases nothing unless..."

## CONDITIONAL QUESTION

You ask a question ONLY if:
- The stakes/reason for battle are genuinely unclear or contradictory
- The political context makes the engagement inexplicable
- There's a critical alliance or succession issue that would change everything

If the scenario already explains WHY this battle happens, you have no question.

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
        "Strategic assertion 1 about why this battle matters",
        "Political constraint or obligation that shapes the engagement",
        "Consequence claim about what victory/defeat means"
    ],
    "assumptions": [
        "What you assumed about political context because it wasn't specified"
    ],
    "questions_remaining": [
        "Strategic questions that still need answers, if any"
    ],
    "delta_requests": [
        {
            "field": "stakes",
            "operation": "set",
            "value": "The strategic value/meaning",
            "rationale": "Why this captures the true stakes"
        },
        {
            "field": "aftermath",
            "operation": "set",
            "value": "Description of what happens after the battle - political consequences, changes in power balance, territorial outcomes",
            "rationale": "The strategic aftermath of this engagement"
        },
        {
            "field": "open_risks",
            "operation": "set",
            "value": ["Risk 1 that commanders knowingly accept", "Risk 2 - strategic vulnerability"],
            "rationale": "Known risks the commanders accept as cost of engagement"
        }
    ],
    "narrative_fragment": "Optional prose about the strategic context for the final output"
}
```

IMPORTANT: You MUST include aftermath and open_risks in your delta_requests.

Your delta_requests must ONLY target 'stakes', 'constraints', 'aftermath', or 'open_risks'.
Any delta to other fields will be rejected.
"""


class Strategist(Expert):
    """
    The Strategist - Royal Counselor to the War Council.

    Focuses on campaign-level strategy, political stakes, and the "why" of battle.
    Thinks in dynasties and obligations, not tactics.
    """

    @property
    def config(self) -> ExpertConfig:
        return ExpertConfig(
            name="The Strategist",
            codename="strategist",
            title="Royal Counselor to the War Council",
            model=ModelType.CLAUDE_SONNET,
            icon="👑",
            chamber=Chamber.CONSILIUM,
            description=(
                "Advisor on campaign-level strategy and political context. "
                "Thinks in dynasties and obligations, sees every battle as a move "
                "on a larger board."
            ),
        )

    @property
    def jurisdiction(self) -> Jurisdiction:
        return Jurisdiction(
            owns=[
                "stakes",
                "constraints",  # Will validate for political-only in prompting
                "aftermath",
                "open_risks",
            ],
            forbidden=[
                "version",
                "last_modified_by",
                "consistency_hash",
                "forces",
                "terrain_weather",
                "timeline",
                "decision_points",
                "casualty_profile",
            ],
        )

    def _build_system_prompt(self, sheet: ScenarioSheet) -> str:
        """Build the Strategist's system prompt."""
        return STRATEGIST_SYSTEM_PROMPT

    def get_conditional_question(
        self,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
    ) -> ExpertQuestion | None:
        """
        Ask a question only if the strategic stakes are critically unclear.
        """
        # Check if stakes are missing or too vague
        if not sheet.stakes or len(sheet.stakes) < 20:
            return ExpertQuestion(
                expert=self.config.codename,
                question=(
                    "What compels this battle NOW? Is there a succession crisis, "
                    "an alliance obligation, a territorial claim, or an existential "
                    "threat that forces the engagement?"
                ),
                context=(
                    "Without understanding the political imperative, I cannot assess "
                    "whether the commanders' decisions make strategic sense."
                ),
                default="The battle is forced by immediate military necessity.",
            )

        # Check if there are forces but no clear political context
        if sheet.forces and len(sheet.forces) >= 2:
            sides = list(sheet.forces.keys())
            # If stakes don't mention the sides or their relationship
            stakes_lower = sheet.stakes.lower()
            if not any(side.lower() in stakes_lower for side in sides):
                return ExpertQuestion(
                    expert=self.config.codename,
                    question=(
                        f"What is the political relationship between {sides[0]} and "
                        f"{sides[1]}? Are they rival claimants, traditional enemies, "
                        "former allies, or something else?"
                    ),
                    context=(
                        "Understanding the political relationship shapes what "
                        "victory and defeat mean for each side."
                    ),
                    default="They are traditional enemies with no special political context.",
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
            f"**Current Stakes:** {sheet.stakes or 'Not yet defined'}",
        ]

        # Add existing constraints
        if sheet.constraints:
            prompt_parts.append("\n**Existing Constraints:**")
            constraints = sheet.constraints if isinstance(sheet.constraints, list) else [sheet.constraints]
            for c in constraints:
                prompt_parts.append(f"- {c}")

        # Add forces overview (for political context)
        if sheet.forces:
            prompt_parts.append("\n**Forces Engaged:**")
            for side_id, force in sheet.forces.items():
                side_name = safe_attr(force, 'side_name', side_id)
                strength = safe_int(safe_attr(force, 'total_strength', 0))
                prompt_parts.append(f"- {side_name}: {strength:,} troops")
                commander = safe_attr(force, 'commander')
                if commander:
                    cmd_name = safe_attr(commander, 'name', 'Unknown')
                    cmd_comp = enum_value(safe_attr(commander, 'competence', ''))
                    prompt_parts.append(f"  Commander: {cmd_name} ({cmd_comp})")

        # Add any relevant answers
        if answers:
            prompt_parts.append("\n**Additional Context from Interrogation:**")
            for key, value in answers.items():
                if key in ["why_battle_now", "narrative_outcome"]:
                    prompt_parts.append(f"- {key}: {value}")

        # Add prior contributions summary
        if prior_contributions:
            prompt_parts.append("\n**Prior Expert Contributions This Round:**")
            for contrib in prior_contributions:
                if contrib.domain_claims:
                    prompt_parts.append(f"\n*{contrib.expert}:*")
                    for claim in contrib.domain_claims[:3]:
                        prompt_parts.append(f"- {claim}")

        prompt_parts.append(
            "\n\n# Your Task\n"
            "Analyze the strategic and political context of this battle. "
            "What are the true stakes? What political constraints shape the commanders' "
            "options? What does victory or defeat mean beyond the battlefield?\n\n"
            "Provide your analysis as a JSON object with domain_claims, assumptions, "
            "questions_remaining, delta_requests, and narrative_fragment."
        )

        return "\n".join(prompt_parts)
