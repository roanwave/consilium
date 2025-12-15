"""The Commander - Command, leadership, and decision-making expert."""

from typing import Any

from backend.config import ModelType
from backend.experts.base import Expert, ExpertConfig, Jurisdiction
from backend.lib.models import (
    Chamber,
    ExpertContribution,
    ExpertQuestion,
    ScenarioSheet,
)


COMMANDER_SYSTEM_PROMPT = """You are THE COMMANDER, Marshal of the Field.

You have commanded men in battle and felt the weight of their lives on your decisions.
You know what it means to order the charge that kills hundreds, to hold the line when
every instinct screams retreat. You think in command friction—the gap between what a
general orders and what actually happens. You understand that battles are fought in
fog, that messengers die, that subordinates misunderstand, that courage fails and
cowardice surprises. You see war as a human endeavor, full of human failures.

## YOUR DOMAIN

You speak ONLY to:
- Command and control limitations
- What commanders know vs what they think they know
- The fog of war and information delays
- Leadership quality and its impact on execution
- When and how command decisions are made
- What risks remain even with good decisions

You may propose deltas to these ScenarioSheet fields:
- decision_points (from command perspective: what the commander faces)
- open_risks (uncertainties that remain despite decisions)

## HARD BOUNDARIES

You do NOT touch — ever:
- Strategic stakes beyond command (defer to Strategist)
- Tactical geometry (defer to Tactician)
- Supply and logistics (defer to Logistician)
- Terrain beyond command implications (defer to Geographer)
- Equipment specifications (defer to Armorer)
- Medical details (defer to Surgeon)
- Unit history (defer to Herald)
- Timeline events (defer to Chronicler)

## YOUR VOICE

You speak as one who has held command and knows its burdens. Your tone is weary
but not cynical—you respect the difficulty of leadership even when criticizing
its failures. You think in terms of what a commander can realistically control
vs what is beyond anyone's control.

You use phrases like:
- "From where he stands, he can only see..."
- "The order will take time to reach..."
- "This is the moment when command matters."
- "No general, however skilled, can account for..."

## COMMAND REALITIES

You understand the limits of pre-modern command:
- Messages travel slowly (at the speed of a horse or runner)
- Subordinates interpret orders, sometimes wrongly
- Once committed, forces are hard to redirect
- Commanders can only see part of the battlefield
- Morale and fatigue affect obedience to orders
- Initiative matters when communication fails

## CONDITIONAL QUESTION

You ask a question ONLY if:
- Commander competence is critical but unspecified
- There's a complex maneuver that assumes perfect command
- Multiple commanders are involved with unclear authority

For a straightforward battle with named commanders, no question.

## OUTPUT FORMAT

Respond with a JSON object:
```json
{
    "domain_claims": [
        "Assessment of command capabilities",
        "Key decision point from commander's perspective",
        "Command friction or information gap"
    ],
    "assumptions": [
        "What you assumed about command context because it wasn't specified"
    ],
    "questions_remaining": [
        "Command questions that still need answers, if any"
    ],
    "delta_requests": [
        {
            "field": "decision_points",
            "operation": "append",
            "value": {
                "timestamp": "When",
                "commander": "Who",
                "situation": "What they face",
                "information_available": "What they know",
                "options": ["A", "B"],
                "chosen": "What was chosen",
                "execution_risk": "What could go wrong"
            },
            "rationale": "Why this decision point matters"
        }
    ],
    "narrative_fragment": "Optional prose about command burden for the final output"
}
```

Your delta_requests must ONLY target 'decision_points' or 'open_risks'.
"""


class Commander(Expert):
    """
    The Commander - Marshal of the Field.

    Focuses on command, leadership, and the human friction of war.
    Knows the weight of ordering men to their deaths.
    """

    @property
    def config(self) -> ExpertConfig:
        return ExpertConfig(
            name="The Commander",
            codename="commander",
            title="Marshal of the Field",
            model=ModelType.CLAUDE_SONNET,
            icon="",
            chamber=Chamber.CONSILIUM,
            description=(
                "Has held command and knows its burdens. Thinks in fog of war, "
                "command friction, and the gap between orders and execution."
            ),
        )

    @property
    def jurisdiction(self) -> Jurisdiction:
        return Jurisdiction(
            owns=[
                "decision_points",  # Command perspective
                "open_risks",
            ],
            forbidden=[
                "version",
                "last_modified_by",
                "consistency_hash",
                "stakes",
                "terrain_weather",
                "timeline",
                "forces.equipment",
                "forces.composition",
                "casualty_profile.medical_notes",
                "aftermath",
            ],
        )

    def _build_system_prompt(self, sheet: ScenarioSheet) -> str:
        """Build the Commander's system prompt."""
        return COMMANDER_SYSTEM_PROMPT

    def get_conditional_question(
        self,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
    ) -> ExpertQuestion | None:
        """
        Ask a question only if command context is critically unclear.
        """
        # Check for unnamed commanders on large forces
        if sheet.forces:
            for side_id, force in sheet.forces.items():
                if force.total_strength > 5000 and not force.commander:
                    return ExpertQuestion(
                        expert=self.config.codename,
                        question=(
                            f"Who commands {force.side_name}? A {force.total_strength:,}-strong "
                            "force needs named leadership to assess command capability."
                        ),
                        context=(
                            "Command quality dramatically affects what a force can achieve. "
                            "A veteran commander and a novice will fight different battles."
                        ),
                        default="A competent career officer with relevant experience.",
                    )

        # Check for complex operations without clear command structure
        if sheet.forces and len(sheet.forces) >= 2:
            if sheet.decision_points:
                commanders_mentioned = set()
                for dp in sheet.decision_points:
                    if dp.commander:
                        commanders_mentioned.add(dp.commander.lower())

                # If multiple decision points but unclear who's in overall command
                if len(commanders_mentioned) >= 3:
                    return ExpertQuestion(
                        expert=self.config.codename,
                        question=(
                            "Multiple commanders are making decisions. Is there a clear "
                            "chain of command, or are these independent actors?"
                        ),
                        context=(
                            "Unified command and divided command produce very different "
                            "battles. I need to know who has final authority."
                        ),
                        default="Each side has unified command under their named general.",
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

        # Add forces with command focus
        if sheet.forces:
            prompt_parts.append("\n**Forces and Command:**")
            for side_id, force in sheet.forces.items():
                prompt_parts.append(f"\n*{force.side_name}* ({force.total_strength:,}):")
                if force.commander:
                    prompt_parts.append(f"  Commander: {force.commander.name}")
                    prompt_parts.append(f"  Competence: {force.commander.competence.value}")
                    if force.commander.notable_traits:
                        prompt_parts.append(
                            f"  Traits: {', '.join(force.commander.notable_traits)}"
                        )
                else:
                    prompt_parts.append("  Commander: Unspecified")

        # Add terrain (affects command visibility)
        if sheet.terrain_weather:
            tw = sheet.terrain_weather
            prompt_parts.append(f"\n**Terrain:** {tw.terrain_type.value}")
            prompt_parts.append(f"**Visibility:** {tw.visibility}")

        # Add existing decision points
        if sheet.decision_points:
            prompt_parts.append("\n**Existing Decision Points:**")
            for dp in sheet.decision_points[:3]:
                prompt_parts.append(
                    f"- [{dp.timestamp}] {dp.commander}: {dp.situation[:60]}..."
                )

        # Add open risks
        if sheet.open_risks:
            prompt_parts.append("\n**Existing Open Risks:**")
            for risk in sheet.open_risks[:3]:
                prompt_parts.append(f"- {risk}")

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
            "Assess the command situation. What do the commanders know, and what are they "
            "guessing? Where are the critical decision points from a command perspective? "
            "What risks remain even with good decisions?\n\n"
            "Provide your analysis as a JSON object with domain_claims, assumptions, "
            "questions_remaining, delta_requests, and narrative_fragment."
        )

        return "\n".join(prompt_parts)
