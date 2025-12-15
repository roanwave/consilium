"""Chamber management for Consilium and Red Team.

Handles expert invocation and result aggregation.
"""

import asyncio
import json
import logging
from typing import Any

from backend.experts.base import Expert, RedTeamExpert
from backend.lib.llm import LLMClient
from backend.lib.models import (
    Chamber,
    ExpertContribution,
    RedTeamObjection,
    ScenarioSheet,
    SessionState,
    TokenUsage,
)
from backend.lib.streaming import EventBuilder, SSEEvent

logger = logging.getLogger(__name__)


# =============================================================================
# Base Chamber Manager
# =============================================================================


class ChamberManager:
    """
    Manages expert chambers.

    Handles:
    - Expert registration and ordering
    - Expert invocation (sequential or parallel)
    - SSE event emission
    - Result aggregation
    """

    def __init__(
        self,
        chamber: Chamber,
        experts: list[Expert] | None = None,
        llm_client: LLMClient | None = None,
    ):
        """
        Initialize chamber.

        Args:
            chamber: Chamber type (CONSILIUM or REDTEAM)
            experts: List of experts in this chamber
            llm_client: LLM client for expert invocations
        """
        self.chamber = chamber
        self.experts = experts or []
        self.llm_client = llm_client

    def set_experts(self, experts: list[Expert]) -> None:
        """Set the experts in this chamber."""
        self.experts = experts

    def set_llm_client(self, client: LLMClient) -> None:
        """Set the LLM client."""
        self.llm_client = client

    async def invoke_all(
        self,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
        event_builder: EventBuilder | None = None,
    ) -> tuple[list[ExpertContribution], TokenUsage]:
        """
        Invoke all experts in this chamber.

        Args:
            sheet: Current ScenarioSheet
            answers: All interrogation answers
            event_builder: Optional event builder for SSE emission

        Returns:
            Tuple of (contributions, total_token_usage)
        """
        raise NotImplementedError("Subclass must implement invoke_all")


# =============================================================================
# Consilium Chamber
# =============================================================================


class ConsiliumChamber(ChamberManager):
    """
    The Consilium chamber of domain experts.

    Experts run SEQUENTIALLY because each expert sees contributions
    from prior experts in the same round.
    """

    def __init__(
        self,
        experts: list[Expert] | None = None,
        llm_client: LLMClient | None = None,
    ):
        super().__init__(Chamber.CONSILIUM, experts, llm_client)

    async def invoke_all(
        self,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
        event_builder: EventBuilder | None = None,
        emit_callback: Any | None = None,
    ) -> tuple[list[ExpertContribution], TokenUsage]:
        """
        Invoke all Consilium experts sequentially.

        Each expert sees contributions from prior experts in this round.

        Args:
            sheet: Current ScenarioSheet
            answers: All interrogation answers
            event_builder: Optional event builder for SSE emission
            emit_callback: Async callback to emit SSE events

        Returns:
            Tuple of (contributions, total_token_usage)
        """
        contributions: list[ExpertContribution] = []
        total_usage = TokenUsage()

        for expert in self.experts:
            codename = expert.config.codename
            logger.info(f"Invoking Consilium expert: {codename}")

            # Emit expert start event
            if event_builder and emit_callback:
                event = event_builder.expert_start(codename, "consilium")
                await emit_callback(event)

            try:
                contribution, usage = await expert.contribute(
                    sheet=sheet,
                    answers=answers,
                    prior_contributions=contributions,  # Pass prior contributions
                    llm_client=self.llm_client,
                )

                contributions.append(contribution)

                # Accumulate token usage
                total_usage.input_tokens += usage.input_tokens
                total_usage.output_tokens += usage.output_tokens
                total_usage.cache_read_tokens += usage.cache_read_tokens
                total_usage.cache_creation_tokens += usage.cache_creation_tokens

                # Emit contribution event
                if event_builder and emit_callback:
                    event = event_builder.expert_contribution(
                        codename,
                        contribution.model_dump(mode="json"),
                        usage,
                    )
                    await emit_callback(event)

                logger.info(f"Expert {codename} contributed successfully")

            except Exception as e:
                logger.error(f"Expert {codename} failed: {e}")

                # Emit error event
                if event_builder and emit_callback:
                    event = event_builder.expert_error(codename, str(e))
                    await emit_callback(event)

                # Create minimal contribution so we can continue
                contributions.append(
                    ExpertContribution(
                        expert=codename,
                        domain_claims=[f"Error: {str(e)}"],
                        assumptions=[],
                        questions_remaining=[],
                        delta_requests=[],
                        narrative_fragment="",
                    )
                )

        return contributions, total_usage


# =============================================================================
# Red Team Chamber
# =============================================================================


class RedTeamChamber(ChamberManager):
    """
    The Red Team chamber of critics.

    Experts CAN run in PARALLEL since they don't depend on each other.
    Each expert independently critiques the scenario.
    """

    def __init__(
        self,
        experts: list[RedTeamExpert] | None = None,
        llm_client: LLMClient | None = None,
    ):
        super().__init__(Chamber.REDTEAM, experts, llm_client)

    async def invoke_all(
        self,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
        consilium_contributions: list[ExpertContribution] | None = None,
        event_builder: EventBuilder | None = None,
        emit_callback: Any | None = None,
        parallel: bool = True,
    ) -> tuple[list[RedTeamObjection], TokenUsage]:
        """
        Invoke all Red Team experts.

        Can run in parallel since critics don't depend on each other.

        Args:
            sheet: Current ScenarioSheet
            answers: All interrogation answers
            consilium_contributions: Contributions from Consilium round
            event_builder: Optional event builder for SSE emission
            emit_callback: Async callback to emit SSE events
            parallel: Whether to run experts in parallel (default: True)

        Returns:
            Tuple of (objections, total_token_usage)
        """
        objections: list[RedTeamObjection] = []
        total_usage = TokenUsage()
        prior_contributions = consilium_contributions or []

        # Emit red team start event
        if event_builder and emit_callback:
            event = event_builder.build(
                "redteam_start",
                {"expert_count": len(self.experts)},
            )
            await emit_callback(event)

        if parallel and len(self.experts) > 1:
            # Run experts in parallel
            tasks = []
            for expert in self.experts:
                tasks.append(
                    self._invoke_expert(
                        expert,
                        sheet,
                        answers,
                        prior_contributions,
                        event_builder,
                        emit_callback,
                    )
                )

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Red team expert failed: {result}")
                    continue

                expert_objections, usage = result
                objections.extend(expert_objections)

                # Accumulate token usage
                total_usage.input_tokens += usage.input_tokens
                total_usage.output_tokens += usage.output_tokens
                total_usage.cache_read_tokens += usage.cache_read_tokens
                total_usage.cache_creation_tokens += usage.cache_creation_tokens

        else:
            # Run sequentially
            for expert in self.experts:
                try:
                    expert_objections, usage = await self._invoke_expert(
                        expert,
                        sheet,
                        answers,
                        prior_contributions,
                        event_builder,
                        emit_callback,
                    )
                    objections.extend(expert_objections)

                    # Accumulate token usage
                    total_usage.input_tokens += usage.input_tokens
                    total_usage.output_tokens += usage.output_tokens
                    total_usage.cache_read_tokens += usage.cache_read_tokens
                    total_usage.cache_creation_tokens += usage.cache_creation_tokens

                except Exception as e:
                    logger.error(f"Red team expert failed: {e}")

        # Emit red team complete event
        if event_builder and emit_callback:
            event = event_builder.build(
                "redteam_complete",
                {"objection_count": len(objections)},
            )
            await emit_callback(event)

        return objections, total_usage

    async def _invoke_expert(
        self,
        expert: Expert,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
        prior_contributions: list[ExpertContribution],
        event_builder: EventBuilder | None,
        emit_callback: Any | None,
    ) -> tuple[list[RedTeamObjection], TokenUsage]:
        """
        Invoke a single red team expert.

        Args:
            expert: The expert to invoke
            sheet: Current ScenarioSheet
            answers: All interrogation answers
            prior_contributions: Consilium contributions
            event_builder: Optional event builder
            emit_callback: Async callback to emit events

        Returns:
            Tuple of (objections, token_usage)
        """
        codename = expert.config.codename
        logger.info(f"Invoking Red Team expert: {codename}")

        # Emit expert start event
        if event_builder and emit_callback:
            event = event_builder.expert_start(codename, "redteam")
            await emit_callback(event)

        try:
            contribution, usage = await expert.contribute(
                sheet=sheet,
                answers=answers,
                prior_contributions=prior_contributions,
                llm_client=self.llm_client,
            )

            # Parse objections from contribution
            # Red team stores objections as JSON strings in domain_claims
            objections = self._parse_objections(codename, contribution)

            # Emit objection events
            if event_builder and emit_callback:
                for obj in objections:
                    event = event_builder.redteam_objection(
                        codename,
                        obj.model_dump(mode="json"),
                    )
                    await emit_callback(event)

            logger.info(f"Red Team expert {codename}: {len(objections)} objections")
            return objections, usage

        except Exception as e:
            logger.error(f"Red Team expert {codename} failed: {e}")

            # Emit error event
            if event_builder and emit_callback:
                event = event_builder.expert_error(codename, str(e))
                await emit_callback(event)

            raise

    def _parse_objections(
        self,
        expert_codename: str,
        contribution: ExpertContribution,
    ) -> list[RedTeamObjection]:
        """
        Parse objections from a red team contribution.

        Red team experts store objections as JSON strings in domain_claims.

        Args:
            expert_codename: The expert's codename
            contribution: The expert's contribution

        Returns:
            List of RedTeamObjection objects
        """
        objections = []

        for claim in contribution.domain_claims:
            try:
                # Try to parse as JSON
                obj_data = json.loads(claim)

                objection = RedTeamObjection(
                    expert=expert_codename,
                    target=obj_data.get("target", "unknown"),
                    objection=obj_data.get("objection", claim),
                    severity=obj_data.get("severity", "minor"),
                    suggestion=obj_data.get("suggestion", ""),
                )
                objections.append(objection)

            except json.JSONDecodeError:
                # Not JSON - treat as raw objection text
                objection = RedTeamObjection(
                    expert=expert_codename,
                    target="general",
                    objection=claim,
                    severity="minor",
                    suggestion="",
                )
                objections.append(objection)

        return objections


# =============================================================================
# Factory Functions
# =============================================================================


def create_consilium_chamber(llm_client: LLMClient | None = None) -> ConsiliumChamber:
    """
    Create a ConsiliumChamber with all experts.

    Args:
        llm_client: LLM client for expert invocations

    Returns:
        Configured ConsiliumChamber
    """
    from backend.experts.consilium import CONSILIUM_EXPERTS

    # Instantiate all expert classes
    experts = [expert_cls() for expert_cls in CONSILIUM_EXPERTS]

    return ConsiliumChamber(experts=experts, llm_client=llm_client)


def create_redteam_chamber(llm_client: LLMClient | None = None) -> RedTeamChamber:
    """
    Create a RedTeamChamber with all experts.

    Args:
        llm_client: LLM client for expert invocations

    Returns:
        Configured RedTeamChamber
    """
    from backend.experts.redteam import REDTEAM_EXPERTS

    # Instantiate all expert classes
    experts = [expert_cls() for expert_cls in REDTEAM_EXPERTS]

    return RedTeamChamber(experts=experts, llm_client=llm_client)
