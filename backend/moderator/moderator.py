"""The Moderator - Brain of the Consilium system.

The Moderator has three jobs:
1. SYNTHESIZE: Collect expert contributions, resolve conflicts, apply deltas
2. CHECK: Run consistency pass, flag violations
3. FILTER: Classify red team objections, decide what requires action

Uses CLAUDE_OPUS for its LLM calls due to importance.
"""

import logging
from typing import Any

from backend.config import ModelType, get_settings
from backend.lib.llm import LLMClient
from backend.lib.models import (
    ConsistencyViolation,
    DeltaOperation,
    DeltaRequest,
    ExpertContribution,
    FilteredObjection,
    ObjectionType,
    RedTeamObjection,
    ScenarioSheet,
    SessionState,
    TokenUsage,
)
from backend.lib.streaming import EventBuilder, EventType
from backend.moderator.consistency import (
    is_certified_ready,
    resolve_contradictions,
    run_consistency_pass,
    summarize_violations,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Field Ownership Map
# =============================================================================

# Maps fields to their owning expert(s)
# Some fields are shared between experts
FIELD_OWNERSHIP: dict[str, list[str]] = {
    # Strategist owns
    "stakes": ["strategist", "herald"],  # Shared
    "constraints": ["strategist"],
    "aftermath": ["strategist"],
    "open_risks": ["strategist"],

    # Tactician owns
    "timeline": ["tactician"],
    "decision_points": ["tactician", "commander"],  # Shared

    # Logistician owns
    "forces.*.supply_state": ["logistician"],
    "forces.*.constraints": ["logistician"],

    # Geographer owns
    "terrain_weather": ["geographer"],

    # Armorer owns
    "forces.*.composition": ["armorer"],
    "forces.*.equipment": ["armorer"],
    "forces.*.armor_quality": ["armorer"],

    # Surgeon owns
    "casualty_profile": ["surgeon"],

    # Commander owns
    "forces.*.commander": ["commander"],
    "forces.*.sub_commanders": ["commander"],
    "forces.*.morale": ["commander"],
    "forces.*.morale_factors": ["commander"],

    # Chronicler owns
    "theater": ["chronicler"],
    "magic": ["chronicler"],

    # Herald owns
    "forces.*.side_name": ["herald"],
    "forces.*.objectives": ["herald"],
}


# =============================================================================
# Delta Applicator
# =============================================================================


class DeltaApplicator:
    """
    Applies approved delta requests to the ScenarioSheet.

    Validates jurisdiction before applying any deltas.
    """

    def __init__(self, ownership_map: dict[str, list[str]] | None = None):
        """
        Initialize the applicator.

        Args:
            ownership_map: Field ownership mapping. Uses default if not provided.
        """
        self.ownership_map = ownership_map or FIELD_OWNERSHIP

    def validate_delta(
        self,
        delta: DeltaRequest,
        expert: str,
    ) -> tuple[bool, str]:
        """
        Validate that an expert can modify a field.

        Args:
            delta: The delta request
            expert: The expert codename

        Returns:
            Tuple of (is_valid, reason)
        """
        field = delta.field

        # Check if field has explicit ownership
        for pattern, owners in self.ownership_map.items():
            if self._field_matches_pattern(field, pattern):
                if expert in owners:
                    return True, "within_jurisdiction"
                else:
                    return False, f"field owned by {', '.join(owners)}, not {expert}"

        # Field not in map - allow if no explicit restriction
        return True, "no_explicit_restriction"

    def _field_matches_pattern(self, field: str, pattern: str) -> bool:
        """Check if a field path matches a pattern (supports * wildcard)."""
        field_parts = field.split(".")
        pattern_parts = pattern.split(".")

        if len(field_parts) < len(pattern_parts):
            return False

        for i, pattern_part in enumerate(pattern_parts):
            if pattern_part == "*":
                continue
            if i >= len(field_parts):
                return False
            if field_parts[i] != pattern_part:
                return False

        return True

    def apply_delta(
        self,
        sheet: ScenarioSheet,
        delta: DeltaRequest,
        expert: str,
    ) -> tuple[ScenarioSheet, bool, str]:
        """
        Apply a single delta to the sheet.

        Args:
            sheet: Current ScenarioSheet
            delta: The delta to apply
            expert: Expert proposing the change

        Returns:
            Tuple of (updated_sheet, success, message)
        """
        # Validate jurisdiction
        is_valid, reason = self.validate_delta(delta, expert)
        if not is_valid:
            return sheet, False, f"Rejected: {reason}"

        # Make a copy to avoid mutation
        sheet = sheet.model_copy(deep=True)

        try:
            if delta.operation == DeltaOperation.SET:
                self._apply_set(sheet, delta.field, delta.value)
            elif delta.operation == DeltaOperation.APPEND:
                self._apply_append(sheet, delta.field, delta.value)
            elif delta.operation == DeltaOperation.MODIFY:
                self._apply_modify(sheet, delta.field, delta.value)

            return sheet, True, "applied"

        except Exception as e:
            logger.error(f"Failed to apply delta: {e}")
            return sheet, False, f"Error: {str(e)}"

    def _apply_set(self, sheet: ScenarioSheet, field: str, value: Any) -> None:
        """Apply a SET operation."""
        self._set_nested_field(sheet, field, value)

    def _apply_append(self, sheet: ScenarioSheet, field: str, value: Any) -> None:
        """Apply an APPEND operation to a list field."""
        current = self._get_nested_field(sheet, field)
        if isinstance(current, list):
            if isinstance(value, list):
                current.extend(value)
            else:
                current.append(value)
        else:
            raise ValueError(f"Cannot append to non-list field: {field}")

    def _apply_modify(self, sheet: ScenarioSheet, field: str, value: Any) -> None:
        """Apply a MODIFY operation (partial update)."""
        current = self._get_nested_field(sheet, field)
        if isinstance(current, dict) and isinstance(value, dict):
            current.update(value)
        elif hasattr(current, "model_copy"):
            # Pydantic model - update fields
            for k, v in value.items():
                if hasattr(current, k):
                    setattr(current, k, v)
        else:
            # Fall back to SET
            self._set_nested_field(sheet, field, value)

    def _get_nested_field(self, obj: Any, field: str) -> Any:
        """Get a nested field value using dot notation."""
        parts = field.split(".")
        current = obj

        for part in parts:
            if isinstance(current, dict):
                current = current[part]
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                raise KeyError(f"Field not found: {part} in {field}")

        return current

    def _set_nested_field(self, obj: Any, field: str, value: Any) -> None:
        """Set a nested field value using dot notation."""
        parts = field.split(".")

        # Navigate to parent
        current = obj
        for part in parts[:-1]:
            if isinstance(current, dict):
                current = current[part]
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                raise KeyError(f"Field not found: {part} in {field}")

        # Set the final field
        final_part = parts[-1]
        if isinstance(current, dict):
            current[final_part] = value
        elif hasattr(current, final_part):
            setattr(current, final_part, value)
        else:
            raise KeyError(f"Field not found: {final_part} in {field}")

    def apply_all_deltas(
        self,
        sheet: ScenarioSheet,
        contributions: list[ExpertContribution],
    ) -> tuple[ScenarioSheet, list[dict[str, Any]]]:
        """
        Apply all deltas from all contributions.

        Args:
            sheet: Current ScenarioSheet
            contributions: All expert contributions

        Returns:
            Tuple of (updated_sheet, application_log)
        """
        log: list[dict[str, Any]] = []

        for contribution in contributions:
            expert = contribution.expert

            for delta in contribution.delta_requests:
                sheet, success, message = self.apply_delta(sheet, delta, expert)

                entry = {
                    "expert": expert,
                    "field": delta.field,
                    "operation": delta.operation.value,
                    "success": success,
                    "message": message,
                }
                log.append(entry)
                logger.debug(f"Delta applied: {entry}")

        return sheet, log


# =============================================================================
# Red Team Filter
# =============================================================================


FILTER_SYSTEM_PROMPT = """You are the MODERATOR, arbiter of the Consilium.

Your task is to classify Red Team objections. For each objection, determine its type:

STRUCTURAL: This objection points to a fundamental flaw that requires significant
scenario redesign. The current approach cannot simply be tweaked.
Examples: "The timeline assumes teleportation", "These army sizes would require
a population that didn't exist"

REFINABLE: This objection is valid but can be addressed by refining the scenario
in the next deliberation round. The core structure is sound.
Examples: "The cavalry charge timing needs adjustment", "The supply situation
needs more detail"

CONSIDERATION: This is a valid point to keep in mind, but doesn't require changes.
Add it to open_risks and move on.
Examples: "Rain could make bowstrings unreliable", "The reserve might arrive late"

NITPICK: This is either too minor to matter, outside scope, or incorrect.
Dismiss and move on.
Examples: "The exact number of arrows is unspecified", "This armor wasn't used
in this exact year (but close)", Personal preference for different narrative

For each objection, respond with JSON:
{
    "objections": [
        {
            "expert": "expert codename",
            "target": "what was objected to",
            "objection_type": "STRUCTURAL|REFINABLE|CONSIDERATION|NITPICK",
            "reasoning": "Why this classification",
            "action": "What should be done (if any)"
        }
    ]
}
"""


class RedTeamFilter:
    """
    Filters and classifies Red Team objections.

    Uses LLM to intelligently classify objection severity.
    """

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client

    async def filter_objections(
        self,
        objections: list[RedTeamObjection],
        sheet: ScenarioSheet,
        llm_client: LLMClient | None = None,
    ) -> tuple[list[FilteredObjection], TokenUsage]:
        """
        Filter and classify red team objections.

        Args:
            objections: Raw objections from red team
            sheet: Current ScenarioSheet for context
            llm_client: Optional LLM client override

        Returns:
            Tuple of (filtered_objections, token_usage)
        """
        client = llm_client or self.llm_client
        if not client:
            # No LLM - do simple heuristic filtering
            return self._heuristic_filter(objections), TokenUsage()

        if not objections:
            return [], TokenUsage()

        # Build prompt for LLM
        prompt = self._build_filter_prompt(objections, sheet)

        try:
            response = await client.complete(
                model=ModelType.CLAUDE_SONNET,  # Use Sonnet for filtering
                messages=[{"role": "user", "content": prompt}],
                system=FILTER_SYSTEM_PROMPT,
                temperature=0.3,  # Lower temperature for consistency
            )

            filtered = self._parse_filter_response(objections, response.content)
            return filtered, response.token_usage

        except Exception as e:
            logger.error(f"LLM filtering failed: {e}, using heuristics")
            return self._heuristic_filter(objections), TokenUsage()

    def _build_filter_prompt(
        self,
        objections: list[RedTeamObjection],
        sheet: ScenarioSheet,
    ) -> str:
        """Build the prompt for objection filtering."""
        parts = [
            "# Scenario Context",
            f"Era: {sheet.era.value}",
            f"Stakes: {sheet.stakes}",
            "",
            "# Red Team Objections to Classify",
            "",
        ]

        for i, obj in enumerate(objections, 1):
            parts.append(f"## Objection {i}")
            parts.append(f"**Expert:** {obj.expert}")
            parts.append(f"**Target:** {obj.target}")
            parts.append(f"**Severity claimed:** {obj.severity}")
            parts.append(f"**Objection:** {obj.objection}")
            if obj.suggestion:
                parts.append(f"**Suggestion:** {obj.suggestion}")
            parts.append("")

        parts.append("Classify each objection and respond with JSON.")

        return "\n".join(parts)

    def _parse_filter_response(
        self,
        original_objections: list[RedTeamObjection],
        response: str,
    ) -> list[FilteredObjection]:
        """Parse LLM response into filtered objections."""
        import json

        filtered = []

        try:
            # Extract JSON from response
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "{" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]
            else:
                raise ValueError("No JSON found in response")

            data = json.loads(json_str)
            classifications = data.get("objections", [])

            # Match classifications to original objections
            for i, obj in enumerate(original_objections):
                if i < len(classifications):
                    cls = classifications[i]
                    obj_type = self._parse_objection_type(cls.get("objection_type", "NITPICK"))

                    filtered.append(
                        FilteredObjection(
                            original=obj,
                            objection_type=obj_type,
                            moderator_notes=cls.get("reasoning", ""),
                            action_required=cls.get("action", ""),
                        )
                    )
                else:
                    # No classification - default to REFINABLE
                    filtered.append(
                        FilteredObjection(
                            original=obj,
                            objection_type=ObjectionType.REFINABLE,
                            moderator_notes="No classification from LLM",
                            action_required="Review manually",
                        )
                    )

        except Exception as e:
            logger.error(f"Failed to parse filter response: {e}")
            # Fall back to heuristics
            return self._heuristic_filter(original_objections)

        return filtered

    def _parse_objection_type(self, type_str: str) -> ObjectionType:
        """Parse objection type string to enum."""
        type_str = type_str.upper().strip()
        mapping = {
            "STRUCTURAL": ObjectionType.STRUCTURAL,
            "REFINABLE": ObjectionType.REFINABLE,
            "CONSIDERATION": ObjectionType.COSMETIC,  # Map to cosmetic
            "NITPICK": ObjectionType.DISMISSED,
        }
        return mapping.get(type_str, ObjectionType.REFINABLE)

    def _heuristic_filter(
        self,
        objections: list[RedTeamObjection],
    ) -> list[FilteredObjection]:
        """Simple heuristic filtering when LLM is unavailable."""
        filtered = []

        for obj in objections:
            severity = obj.severity.lower()

            if severity == "critical":
                obj_type = ObjectionType.STRUCTURAL
            elif severity == "major":
                obj_type = ObjectionType.REFINABLE
            else:
                obj_type = ObjectionType.COSMETIC

            filtered.append(
                FilteredObjection(
                    original=obj,
                    objection_type=obj_type,
                    moderator_notes=f"Heuristic classification based on severity: {severity}",
                    action_required="",
                )
            )

        return filtered


# =============================================================================
# Synthesis Prompts
# =============================================================================


SYNTHESIS_SYSTEM_PROMPT = """You are the MODERATOR, synthesizing expert contributions.

Your job is to identify conflicts between expert proposals and resolve them sensibly.
When experts disagree, prefer:
1. The expert with jurisdiction over the field in question
2. Physical constraints over narrative preferences
3. Consistency with established era/setting

Output a brief synthesis summary explaining:
- Key contributions accepted
- Any conflicts resolved
- What was changed and why

Keep it concise - focus on what matters.
"""


# =============================================================================
# Main Moderator Class
# =============================================================================


class Moderator:
    """
    The Moderator - brain of the Consilium system.

    Orchestrates:
    1. Delta synthesis and application
    2. Consistency checking
    3. Red team objection filtering
    """

    def __init__(self, llm_client: LLMClient | None = None):
        """
        Initialize the Moderator.

        Args:
            llm_client: LLM client for synthesis and filtering
        """
        self._llm_client = llm_client
        self.settings = get_settings()
        self.model = self.settings.moderator_model
        self.delta_applicator = DeltaApplicator()
        self.filter = RedTeamFilter(llm_client)

    def set_llm_client(self, client: LLMClient) -> None:
        """Set the LLM client."""
        self._llm_client = client
        self.filter.llm_client = client

    async def synthesize(
        self,
        sheet: ScenarioSheet,
        contributions: list[ExpertContribution],
        event_builder: EventBuilder | None = None,
        emit_callback: Any | None = None,
    ) -> tuple[ScenarioSheet, str, TokenUsage]:
        """
        Synthesize expert contributions into the sheet.

        Args:
            sheet: Current ScenarioSheet
            contributions: Expert contributions to synthesize
            event_builder: Optional event builder for SSE
            emit_callback: Optional callback to emit events

        Returns:
            Tuple of (updated_sheet, synthesis_summary, token_usage)
        """
        total_usage = TokenUsage()

        # Apply all deltas
        sheet, delta_log = self.delta_applicator.apply_all_deltas(sheet, contributions)

        # Emit delta events async
        if event_builder and emit_callback:
            for entry in delta_log:
                event = event_builder.moderator_delta(
                    entry["field"],
                    entry["operation"],
                    entry["success"],
                    entry["message"],
                )
                await emit_callback(event)

        # Generate synthesis summary if we have an LLM
        summary = self._generate_local_summary(contributions, delta_log)

        if self._llm_client and contributions:
            try:
                llm_summary, usage = await self._generate_llm_summary(
                    sheet, contributions, delta_log
                )
                summary = llm_summary
                total_usage = usage
            except Exception as e:
                logger.error(f"LLM synthesis failed: {e}")

        # Update sheet metadata
        sheet.increment_version("moderator")

        # Emit synthesis event
        if event_builder and emit_callback:
            event = event_builder.moderator_synthesis(summary)
            await emit_callback(event)

        return sheet, summary, total_usage

    async def check_consistency(
        self,
        sheet: ScenarioSheet,
    ) -> tuple[ScenarioSheet, list[ConsistencyViolation], list[str]]:
        """
        Run consistency check and attempt auto-resolution.

        Args:
            sheet: ScenarioSheet to check

        Returns:
            Tuple of (updated_sheet, remaining_violations, resolutions_made)
        """
        # Run consistency pass
        violations = await run_consistency_pass(sheet)

        # Attempt auto-resolution
        sheet, resolutions = await resolve_contradictions(sheet, violations)

        # Re-check after resolution
        if resolutions:
            violations = await run_consistency_pass(sheet)

        return sheet, violations, resolutions

    async def filter_objections(
        self,
        objections: list[RedTeamObjection],
        sheet: ScenarioSheet,
        event_builder: EventBuilder | None = None,
        emit_callback: Any | None = None,
    ) -> tuple[list[FilteredObjection], TokenUsage]:
        """
        Filter and classify red team objections.

        Args:
            objections: Raw objections from red team
            sheet: Current ScenarioSheet
            event_builder: Optional event builder for SSE
            emit_callback: Optional callback to emit events

        Returns:
            Tuple of (filtered_objections, token_usage)
        """
        filtered, usage = await self.filter.filter_objections(
            objections, sheet, self._llm_client
        )

        # Emit filter event
        if event_builder and emit_callback:
            breakdown = self._count_by_type(filtered)
            event = event_builder.moderator_filter(
                len(objections),
                len([f for f in filtered if f.objection_type != ObjectionType.DISMISSED]),
                breakdown,
            )
            await emit_callback(event)

        return filtered, usage

    async def apply_deltas(
        self,
        sheet: ScenarioSheet,
        deltas: list[DeltaRequest],
        expert: str = "unknown",
    ) -> tuple[ScenarioSheet, list[dict]]:
        """
        Apply delta requests to the sheet.

        Args:
            sheet: Current ScenarioSheet
            deltas: List of delta requests
            expert: Expert proposing the changes

        Returns:
            Tuple of (updated_sheet, application_log)
        """
        log = []
        for delta in deltas:
            sheet, success, message = self.delta_applicator.apply_delta(sheet, delta, expert)
            log.append({
                "field": delta.field,
                "operation": delta.operation.value,
                "success": success,
                "message": message,
            })
        return sheet, log

    async def certify(
        self,
        sheet: ScenarioSheet,
        violations: list[ConsistencyViolation],
        filtered_objections: list[FilteredObjection],
    ) -> tuple[bool, str]:
        """
        Determine if the scenario can be certified.

        Args:
            sheet: Current ScenarioSheet
            violations: Remaining consistency violations
            filtered_objections: Filtered red team objections

        Returns:
            Tuple of (certified, reason)
        """
        ready, reason = self.is_ready_for_certification(violations, filtered_objections)
        return ready, reason

    def _count_by_type(self, filtered: list[FilteredObjection]) -> dict[str, int]:
        """Count filtered objections by type."""
        counts: dict[str, int] = {}
        for f in filtered:
            key = f.objection_type.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _generate_local_summary(
        self,
        contributions: list[ExpertContribution],
        delta_log: list[dict[str, Any]],
    ) -> str:
        """Generate a local summary without LLM."""
        accepted = sum(1 for d in delta_log if d["success"])
        rejected = len(delta_log) - accepted

        lines = [
            f"Synthesis complete: {accepted} deltas applied, {rejected} rejected.",
            "",
        ]

        if contributions:
            lines.append("Key contributions:")
            for contrib in contributions[:5]:  # Top 5
                if contrib.domain_claims:
                    lines.append(f"- {contrib.expert}: {contrib.domain_claims[0][:80]}...")

        return "\n".join(lines)

    async def _generate_llm_summary(
        self,
        sheet: ScenarioSheet,
        contributions: list[ExpertContribution],
        delta_log: list[dict[str, Any]],
    ) -> tuple[str, TokenUsage]:
        """Generate synthesis summary using LLM."""
        # Build prompt
        prompt_parts = [
            "# Expert Contributions to Synthesize",
            "",
        ]

        for contrib in contributions:
            prompt_parts.append(f"## {contrib.expert}")
            if contrib.domain_claims:
                prompt_parts.append("Claims:")
                for claim in contrib.domain_claims[:5]:
                    prompt_parts.append(f"- {claim}")
            if contrib.delta_requests:
                prompt_parts.append(f"Proposed {len(contrib.delta_requests)} changes")
            prompt_parts.append("")

        prompt_parts.append("# Delta Application Results")
        for entry in delta_log:
            status = "Accepted" if entry["success"] else "Rejected"
            prompt_parts.append(
                f"- {entry['expert']}: {entry['field']} ({entry['operation']}) - {status}"
            )

        prompt_parts.append("")
        prompt_parts.append("Provide a brief synthesis summary.")

        prompt = "\n".join(prompt_parts)

        response = await self._llm_client.complete(
            model=ModelType.CLAUDE_SONNET,  # Use Sonnet for synthesis summary
            messages=[{"role": "user", "content": prompt}],
            system=SYNTHESIS_SYSTEM_PROMPT,
            temperature=0.5,
            max_tokens=500,
        )

        return response.content, response.token_usage

    def is_ready_for_certification(
        self,
        violations: list[ConsistencyViolation],
        filtered_objections: list[FilteredObjection],
    ) -> tuple[bool, str]:
        """
        Check if the scenario is ready for certification.

        Args:
            violations: Remaining consistency violations
            filtered_objections: Filtered red team objections

        Returns:
            Tuple of (is_ready, reason)
        """
        # Check for blocking consistency violations
        if not is_certified_ready(violations):
            error_count = sum(1 for v in violations if v.severity == "error")
            return False, f"{error_count} blocking consistency errors remain"

        # Check for structural objections
        structural = [
            f for f in filtered_objections
            if f.objection_type == ObjectionType.STRUCTURAL
        ]
        if structural:
            return False, f"{len(structural)} structural objections require scenario redesign"

        return True, "ready for certification"
