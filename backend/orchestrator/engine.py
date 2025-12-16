"""Main deliberation engine.

Orchestrates the multi-round expert deliberation process.
"""

import logging
from typing import Any, AsyncIterator

from backend.lib.llm import LLMClient
from backend.lib.models import (
    ConsistencyViolation,
    DeliberationRound,
    ExpertContribution,
    FilteredObjection,
    ObjectionType,
    RedTeamObjection,
    ScenarioSheet,
    SessionState,
    SessionStatus,
    SSEEvent,
    TokenUsage,
)
from backend.lib.streaming import EventBuilder, EventType
from backend.moderator.moderator import Moderator
from backend.orchestrator.chambers import (
    ConsiliumChamber,
    RedTeamChamber,
    create_consilium_chamber,
    create_redteam_chamber,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Round Executor
# =============================================================================


class RoundExecutor:
    """
    Executes a single deliberation round.

    Flow per round:
    1. Consilium deliberates (sequential)
    2. Moderator synthesizes contributions
    3. Consistency check
    4. Red Team attacks (can be parallel)
    5. Moderator filters objections
    6. Certification check
    """

    def __init__(
        self,
        consilium: ConsiliumChamber,
        redteam: RedTeamChamber,
        moderator: Moderator,
        llm_client: LLMClient | None = None,
    ):
        """
        Initialize round executor.

        Args:
            consilium: Consilium chamber
            redteam: Red Team chamber
            moderator: Moderator instance
            llm_client: LLM client for all operations
        """
        self.consilium = consilium
        self.redteam = redteam
        self.moderator = moderator
        self.llm_client = llm_client

        # Set LLM client on chambers
        if llm_client:
            self.consilium.set_llm_client(llm_client)
            self.redteam.set_llm_client(llm_client)
            self.moderator.set_llm_client(llm_client)

    async def execute(
        self,
        round_number: int,
        sheet: ScenarioSheet,
        answers: dict[str, Any],
        event_builder: EventBuilder,
        emit_callback: Any,
    ) -> tuple[DeliberationRound, bool, str]:
        """
        Execute a single deliberation round.

        Args:
            round_number: Current round number (1-indexed)
            sheet: Current ScenarioSheet
            answers: All interrogation answers
            event_builder: Event builder for SSE
            emit_callback: Async callback to emit events

        Returns:
            Tuple of (round_result, is_certified, certification_reason)
        """
        logger.info(f"Starting round {round_number}")

        # Initialize round
        round_result = DeliberationRound(
            round_number=round_number,
            sheet_before=sheet.model_copy(deep=True),
        )
        total_usage = TokenUsage()

        # Emit round start
        await emit_callback(event_builder.round_start(round_number))

        # Step 1: Consilium deliberates
        await emit_callback(
            event_builder.progress(f"Round {round_number}: Consilium deliberating...")
        )

        contributions, consilium_usage = await self.consilium.invoke_all(
            sheet=sheet,
            answers=answers,
            event_builder=event_builder,
            emit_callback=emit_callback,
        )
        round_result.consilium_contributions = contributions
        self._accumulate_usage(total_usage, consilium_usage)

        # Step 2: Moderator synthesizes
        await emit_callback(
            event_builder.progress(f"Round {round_number}: Synthesizing contributions...")
        )

        sheet, summary, synthesis_usage = await self.moderator.synthesize(
            sheet=sheet,
            contributions=contributions,
            event_builder=event_builder,
            emit_callback=emit_callback,
        )
        self._accumulate_usage(total_usage, synthesis_usage)

        # Step 3: Consistency check
        await emit_callback(
            event_builder.progress(f"Round {round_number}: Checking consistency...")
        )

        sheet, violations, resolutions = await self.moderator.check_consistency(sheet)

        if resolutions:
            logger.info(f"Auto-resolved {len(resolutions)} issues")

        # Step 4: Red Team attacks
        await emit_callback(
            event_builder.progress(f"Round {round_number}: Red Team reviewing...")
        )

        objections, redteam_usage = await self.redteam.invoke_all(
            sheet=sheet,
            answers=answers,
            consilium_contributions=contributions,
            event_builder=event_builder,
            emit_callback=emit_callback,
            parallel=True,  # Red team can run in parallel
        )
        round_result.redteam_objections = objections
        self._accumulate_usage(total_usage, redteam_usage)

        # Step 5: Moderator filters objections
        await emit_callback(
            event_builder.progress(f"Round {round_number}: Filtering objections...")
        )

        filtered, filter_usage = await self.moderator.filter_objections(
            objections=objections,
            sheet=sheet,
            event_builder=event_builder,
            emit_callback=emit_callback,
        )
        round_result.filtered_objections = filtered
        self._accumulate_usage(total_usage, filter_usage)

        # Step 6: Certification check
        is_certified, reason = self.moderator.is_ready_for_certification(
            violations, filtered
        )

        # Finalize round
        round_result.sheet_after = sheet.model_copy(deep=True)
        round_result.token_usage = total_usage

        # Emit round end
        await emit_callback(event_builder.round_end(round_number, is_certified))

        logger.info(
            f"Round {round_number} complete: certified={is_certified}, reason={reason}"
        )

        return round_result, is_certified, reason

    def _accumulate_usage(self, total: TokenUsage, new: TokenUsage) -> None:
        """Accumulate token usage."""
        total.input_tokens += new.input_tokens
        total.output_tokens += new.output_tokens
        total.cache_read_tokens += new.cache_read_tokens
        total.cache_creation_tokens += new.cache_creation_tokens


# =============================================================================
# Deliberation Engine
# =============================================================================


class DeliberationEngine:
    """
    Main orchestration engine for expert deliberation.

    Manages:
    - Multi-round deliberation loop
    - Expert invocation order
    - Red team challenges
    - Moderator synthesis and certification
    - Session state persistence
    """

    def __init__(
        self,
        session: SessionState,
        llm_client: LLMClient | None = None,
    ):
        """
        Initialize the engine.

        Args:
            session: Session state to operate on
            llm_client: LLM client for all operations
        """
        self.session = session
        self.llm_client = llm_client
        self.builder = EventBuilder(session)

        # Initialize chambers and moderator
        self.consilium = create_consilium_chamber(llm_client)
        self.redteam = create_redteam_chamber(llm_client)
        self.moderator = Moderator(llm_client)

        # Initialize round executor
        self.executor = RoundExecutor(
            consilium=self.consilium,
            redteam=self.redteam,
            moderator=self.moderator,
            llm_client=llm_client,
        )

    def set_llm_client(self, client: LLMClient) -> None:
        """Set the LLM client on all components."""
        self.llm_client = client
        self.consilium.set_llm_client(client)
        self.redteam.set_llm_client(client)
        self.moderator.set_llm_client(client)
        self.executor.llm_client = client

    async def run(self) -> AsyncIterator[SSEEvent]:
        """
        Run the full deliberation process.

        Yields SSE events as deliberation progresses.
        """
        # Emit session start
        yield self.builder.session_start()

        # Validate session state
        if not self.session.sheet:
            yield self.builder.session_error("No scenario sheet in session")
            yield self.builder.session_end(success=False)
            return

        # Update session status
        self.session.status = SessionStatus.DELIBERATING
        self.session.touch()

        # Build answers dict from session
        answers = self._build_answers_dict()

        try:
            # Run deliberation rounds
            certified = False
            final_reason = "max rounds reached"

            for round_num in range(1, self.session.max_rounds + 1):
                self.session.current_round = round_num

                yield self.builder.progress(f"Starting round {round_num}/{self.session.max_rounds}")

                # Execute round
                round_result, certified, reason = await self.executor.execute(
                    round_number=round_num,
                    sheet=self.session.sheet,
                    answers=answers,
                    event_builder=self.builder,
                    emit_callback=self._create_emit_callback(),
                )

                # Store round result
                self.session.rounds.append(round_result)

                # Update sheet in session
                if round_result.sheet_after:
                    self.session.sheet = round_result.sheet_after

                # Accumulate token usage
                self._accumulate_session_usage(round_result.token_usage)

                # Update session
                self.session.touch()

                # Emit round events
                for event in self._yield_round_events(round_result):
                    yield event

                # Check certification - the ONLY valid early exit
                if certified:
                    logger.info(f"Round {round_num} certified, stopping deliberation")
                    final_reason = reason
                    break

                # Continue to next round
                logger.info(f"Round {round_num} not certified (reason: {reason}), continuing to round {round_num + 1}")

            # Final certification
            if certified:
                self.session.status = SessionStatus.CERTIFIED
                yield self.builder.certified(self.session.sheet)
            else:
                self.session.status = SessionStatus.FAILED
                yield self.builder.certification_failed(
                    final_reason,
                    self._get_blocking_issues(round_result if 'round_result' in locals() else None),
                )

            # Emit session end
            yield self.builder.session_end(success=certified)

        except Exception as e:
            logger.exception(f"Deliberation failed: {e}")
            self.session.status = SessionStatus.FAILED
            yield self.builder.session_error(str(e))
            yield self.builder.session_end(success=False)

    def _build_answers_dict(self) -> dict[str, Any]:
        """Build answers dictionary from session state."""
        answers = {}

        if self.session.core_answers:
            # Convert CoreInterrogation to dict
            core_dict = self.session.core_answers.model_dump()
            answers.update(core_dict)

        if self.session.expert_interrogation.answers:
            answers.update(self.session.expert_interrogation.answers)

        return answers

    def _create_emit_callback(self):
        """Create an emit callback that does nothing (events yielded directly)."""
        async def noop(event: SSEEvent) -> None:
            # Events are collected and yielded by the main loop
            pass
        return noop

    def _yield_round_events(self, round_result: DeliberationRound) -> list[SSEEvent]:
        """Generate events for a completed round (placeholder for detailed events)."""
        # Events were already emitted during round execution
        # This is for any summary events
        return []

    def _accumulate_session_usage(self, usage: TokenUsage) -> None:
        """Accumulate token usage into session totals."""
        self.session.total_token_usage.input_tokens += usage.input_tokens
        self.session.total_token_usage.output_tokens += usage.output_tokens
        self.session.total_token_usage.cache_read_tokens += usage.cache_read_tokens
        self.session.total_token_usage.cache_creation_tokens += usage.cache_creation_tokens

    def _get_blocking_issues(
        self,
        round_result: DeliberationRound | None,
    ) -> list[dict[str, Any]]:
        """Get list of blocking issues preventing certification."""
        issues = []

        if not round_result:
            return [{"type": "error", "description": "No rounds completed"}]

        # Add structural objections
        for f in round_result.filtered_objections:
            obj_type = f.objection_type
            if obj_type == ObjectionType.STRUCTURAL or obj_type == "structural":
                # Handle both dict and model for f.original
                orig = f.original
                if isinstance(orig, dict):
                    issues.append({
                        "type": "structural_objection",
                        "expert": orig.get("expert", "unknown"),
                        "target": orig.get("target", "unknown"),
                        "objection": orig.get("objection", "unknown"),
                    })
                else:
                    issues.append({
                        "type": "structural_objection",
                        "expert": getattr(orig, "expert", "unknown"),
                        "target": getattr(orig, "target", "unknown"),
                        "objection": getattr(orig, "objection", "unknown"),
                    })

        return issues


# =============================================================================
# Factory Functions
# =============================================================================


def create_engine(
    session: SessionState,
    llm_client: LLMClient | None = None,
) -> DeliberationEngine:
    """
    Create a DeliberationEngine for a session.

    Args:
        session: Session state
        llm_client: Optional LLM client

    Returns:
        Configured DeliberationEngine
    """
    return DeliberationEngine(session=session, llm_client=llm_client)
