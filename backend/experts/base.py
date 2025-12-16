"""Abstract base class for Consilium experts.

Defines the contract that all experts must implement.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from backend.config import ModelType
from backend.lib.exceptions import ExpertError, JurisdictionError, LLMResponseParseError
from backend.lib.llm import LLMClient
from backend.lib.models import (
    Chamber,
    DeltaRequest,
    ExpertContribution,
    ExpertQuestion,
    ScenarioSheet,
    TokenUsage,
)
from backend.lib.utils import enum_value

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration Dataclasses
# =============================================================================


@dataclass
class ExpertConfig:
    """Configuration for an expert."""

    name: str  # Full name (e.g., "The Tactician")
    codename: str  # Short identifier (e.g., "tactician")
    title: str  # Role title (e.g., "Military Tactics Expert")
    model: str | ModelType  # LLM model to use
    icon: str  # Emoji icon for UI
    chamber: Chamber  # Which chamber this expert belongs to
    description: str = ""  # What this expert does


@dataclass
class Jurisdiction:
    """Defines what fields an expert can/cannot modify."""

    owns: list[str] = field(default_factory=list)
    """Fields this expert can propose changes to (dot notation for nested)."""

    forbidden: list[str] = field(default_factory=list)
    """Fields this expert must never touch."""

    @classmethod
    def consilium_default(cls) -> "Jurisdiction":
        """Default jurisdiction for Consilium experts."""
        return cls(
            owns=[],  # Override in subclass
            forbidden=[
                "version",
                "last_modified_by",
                "consistency_hash",
            ],
        )

    @classmethod
    def redteam_default(cls) -> "Jurisdiction":
        """Default jurisdiction for Red Team experts (read-only)."""
        return cls(
            owns=[],  # Red team doesn't propose deltas
            forbidden=["*"],  # Cannot modify anything
        )


# =============================================================================
# System Prompt Templates
# =============================================================================


EXPERT_SYSTEM_PROMPT_TEMPLATE = """You are {name}, {title} in the Consilium.

{description}

## Your Role
You are an expert advisor contributing to the design of a medieval battle scenario.
Your job is to provide domain expertise strictly within your area of knowledge.

## Jurisdiction
You may ONLY make claims and propose changes related to: {jurisdiction_owns}
You must NEVER touch: {jurisdiction_forbidden}

## Output Format
You must respond with a JSON object containing:
```json
{{
    "domain_claims": ["List of factual claims strictly within your domain"],
    "assumptions": ["What you assumed because it was unknown"],
    "questions_remaining": ["What you still need answered"],
    "delta_requests": [
        {{
            "field": "ScenarioSheet field path",
            "operation": "set|append|modify",
            "value": "The new value",
            "rationale": "Why this change"
        }}
    ],
    "narrative_fragment": "Optional prose contribution for the final output"
}}
```

## Rules
1. Stay strictly within your domain - do not comment on areas outside your expertise
2. Be specific and concrete - avoid vague generalizations
3. Ground claims in the scenario context provided
4. Propose delta_requests only for fields in your jurisdiction
5. If you make assumptions, document them clearly
6. Ask clarifying questions for critical ambiguities

## Current Scenario Context
Era: {era}
Theater: {theater}
Stakes: {stakes}
"""


REDTEAM_SYSTEM_PROMPT_TEMPLATE = """You are {name}, {title} in the Red Team.

{description}

## Your Role
You are an adversarial critic. Your job is to find flaws, inconsistencies,
and implausibilities in the scenario being developed. You do NOT propose solutions -
only identify problems.

## Output Format
You must respond with a JSON object containing:
```json
{{
    "objections": [
        {{
            "target": "What element you're objecting to",
            "objection": "The specific problem",
            "severity": "critical|major|minor",
            "suggestion": "Brief hint at what might fix it (optional)"
        }}
    ]
}}
```

## Rules
1. Be specific - point to exact elements, numbers, or claims
2. Severity levels:
   - critical: Breaks scenario plausibility entirely
   - major: Significant issue that needs addressing
   - minor: Nitpick or polish item
3. Stay in your domain - only object to things within your expertise
4. Do NOT propose detailed solutions - just identify problems

## Current Scenario Context
Era: {era}
Theater: {theater}
Stakes: {stakes}
"""


# =============================================================================
# Abstract Base Class
# =============================================================================


class Expert(ABC):
    """
    Abstract base class for all experts.

    Subclasses must implement:
    - config: ExpertConfig property
    - jurisdiction: Jurisdiction property
    - get_conditional_question(): Returns question if domain has critical ambiguity
    - _build_user_prompt(): Builds the prompt for this expert
    """

    def __init__(self, llm_client: LLMClient | None = None):
        """
        Initialize expert.

        Args:
            llm_client: Optional LLM client. If not provided, will be created on demand.
        """
        self._llm_client = llm_client

    @property
    @abstractmethod
    def config(self) -> ExpertConfig:
        """Expert configuration."""
        pass

    @property
    @abstractmethod
    def jurisdiction(self) -> Jurisdiction:
        """Expert's jurisdiction over ScenarioSheet fields."""
        pass

    @abstractmethod
    def get_conditional_question(
        self,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
    ) -> ExpertQuestion | None:
        """
        Return a question only if this domain has critical ambiguity.

        Most experts should return None most of the time. Only return a question
        if there's a critical piece of information missing that this expert
        absolutely needs to provide useful input.

        Args:
            sheet: Current scenario sheet
            answers: Answers provided so far

        Returns:
            ExpertQuestion if needed, None otherwise
        """
        pass

    @abstractmethod
    def _build_user_prompt(
        self,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
        prior_contributions: list[ExpertContribution],
    ) -> str:
        """
        Build the user prompt for this expert.

        Args:
            sheet: Current scenario sheet
            answers: All interrogation answers
            prior_contributions: Contributions from experts earlier in this round

        Returns:
            User prompt string
        """
        pass

    def _build_system_prompt(self, sheet: ScenarioSheet) -> str:
        """Build the system prompt for this expert."""
        template = (
            REDTEAM_SYSTEM_PROMPT_TEMPLATE
            if self.config.chamber == Chamber.REDTEAM
            else EXPERT_SYSTEM_PROMPT_TEMPLATE
        )

        return template.format(
            name=self.config.name,
            title=self.config.title,
            description=self.config.description,
            jurisdiction_owns=", ".join(self.jurisdiction.owns) or "none",
            jurisdiction_forbidden=", ".join(self.jurisdiction.forbidden) or "none",
            era=enum_value(sheet.era, "unspecified"),
            theater=sheet.theater or "unspecified",
            stakes=sheet.stakes or "unspecified",
        )

    def _validate_deltas(self, deltas: list[DeltaRequest]) -> list[DeltaRequest]:
        """
        Validate that all delta requests are within jurisdiction.

        Args:
            deltas: List of proposed delta requests

        Returns:
            Validated deltas (unchanged if valid)

        Raises:
            JurisdictionError: If a delta touches a forbidden field
        """
        valid_deltas = []

        for delta in deltas:
            field = delta.field

            # Check forbidden fields
            for forbidden in self.jurisdiction.forbidden:
                if forbidden == "*" or field.startswith(forbidden):
                    logger.warning(
                        f"Expert {self.config.codename} tried to modify "
                        f"forbidden field: {field}"
                    )
                    continue  # Skip this delta

            # Check if field is in jurisdiction (if jurisdiction has specific owns)
            if self.jurisdiction.owns:
                in_jurisdiction = any(
                    field.startswith(owned) for owned in self.jurisdiction.owns
                )
                if not in_jurisdiction:
                    logger.warning(
                        f"Expert {self.config.codename} tried to modify "
                        f"field outside jurisdiction: {field}"
                    )
                    continue  # Skip this delta

            valid_deltas.append(delta)

        return valid_deltas

    def _parse_response(self, content: str) -> dict[str, Any]:
        """
        Parse LLM response into structured data.

        Args:
            content: Raw response content

        Returns:
            Parsed JSON dict

        Raises:
            LLMResponseParseError: If parsing fails
        """
        content = content.strip()

        # Try to extract JSON from response
        try:
            # Look for JSON block
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                json_str = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                json_str = content[start:end].strip()
            elif content.startswith("{"):
                json_str = content
            else:
                # Try to find JSON object in content
                start = content.find("{")
                end = content.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = content[start:end]
                else:
                    raise LLMResponseParseError(
                        "No JSON found in response", raw_response=content
                    )

            return json.loads(json_str)

        except json.JSONDecodeError as e:
            raise LLMResponseParseError(
                f"Invalid JSON in response: {e}", raw_response=content
            )

    async def contribute(
        self,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
        prior_contributions: list[ExpertContribution],
        llm_client: LLMClient | None = None,
    ) -> tuple[ExpertContribution, TokenUsage]:
        """
        Generate expert contribution.

        Args:
            sheet: Current scenario sheet
            answers: All interrogation answers
            prior_contributions: Contributions from experts earlier in this round
            llm_client: LLM client to use (uses instance client if not provided)

        Returns:
            Tuple of (ExpertContribution, TokenUsage)

        Raises:
            ExpertError: If contribution generation fails
        """
        client = llm_client or self._llm_client
        if client is None:
            raise ExpertError(
                "No LLM client available", expert=self.config.codename
            )

        system_prompt = self._build_system_prompt(sheet)
        user_prompt = self._build_user_prompt(sheet, answers, prior_contributions)

        try:
            response = await client.complete(
                model=self.config.model,
                messages=[{"role": "user", "content": user_prompt}],
                system=system_prompt,
                temperature=0.7,
            )

            parsed = self._parse_response(response.content)

            # Build contribution
            delta_requests = []
            for dr in parsed.get("delta_requests", []):
                delta_requests.append(
                    DeltaRequest(
                        field=dr.get("field", ""),
                        operation=dr.get("operation", "set"),
                        value=dr.get("value"),
                        rationale=dr.get("rationale", ""),
                    )
                )

            # Validate deltas
            delta_requests = self._validate_deltas(delta_requests)

            contribution = ExpertContribution(
                expert=self.config.codename,
                domain_claims=parsed.get("domain_claims", []),
                assumptions=parsed.get("assumptions", []),
                questions_remaining=parsed.get("questions_remaining", []),
                delta_requests=delta_requests,
                narrative_fragment=parsed.get("narrative_fragment", ""),
            )

            return contribution, response.token_usage

        except LLMResponseParseError:
            raise
        except Exception as e:
            raise ExpertError(str(e), expert=self.config.codename)


# =============================================================================
# Red Team Expert Base
# =============================================================================


class RedTeamExpert(Expert):
    """
    Base class for Red Team experts.

    Red Team experts produce objections, not contributions.
    They have read-only access to the scenario.
    """

    @property
    def jurisdiction(self) -> Jurisdiction:
        """Red team has read-only access."""
        return Jurisdiction.redteam_default()

    def get_conditional_question(
        self,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
    ) -> ExpertQuestion | None:
        """Red team doesn't ask questions."""
        return None

    def _parse_objections(self, content: str) -> list[dict[str, Any]]:
        """Parse objections from LLM response."""
        parsed = self._parse_response(content)
        return parsed.get("objections", [])

    async def contribute(
        self,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
        prior_contributions: list[ExpertContribution],
        llm_client: LLMClient | None = None,
    ) -> tuple[ExpertContribution, TokenUsage]:
        """
        Red team contribution is stored as domain_claims (the objections).

        The actual objections are parsed separately for processing.
        """
        client = llm_client or self._llm_client
        if client is None:
            raise ExpertError(
                "No LLM client available", expert=self.config.codename
            )

        system_prompt = self._build_system_prompt(sheet)
        user_prompt = self._build_user_prompt(sheet, answers, prior_contributions)

        try:
            response = await client.complete(
                model=self.config.model,
                messages=[{"role": "user", "content": user_prompt}],
                system=system_prompt,
                temperature=0.7,
            )

            objections = self._parse_objections(response.content)

            # Store objections as domain_claims for now
            # The orchestrator will extract them properly
            contribution = ExpertContribution(
                expert=self.config.codename,
                domain_claims=[json.dumps(obj) for obj in objections],
                assumptions=[],
                questions_remaining=[],
                delta_requests=[],
                narrative_fragment="",
            )

            return contribution, response.token_usage

        except Exception as e:
            raise ExpertError(str(e), expert=self.config.codename)
