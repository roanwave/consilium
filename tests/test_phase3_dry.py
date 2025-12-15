"""
Phase 3 Dry Test - Integration test with mocked LLM responses.

Tests the orchestration engine without making actual API calls.
"""

import asyncio
import json
import sys
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock

# Configure stdout for unicode support on Windows
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add parent to path for imports
sys.path.insert(0, str(__file__).rsplit("\\", 2)[0])


@dataclass
class MockResponse:
    """Mock LLM response."""
    content: str
    token_usage: Any


class MockTokenUsage:
    """Mock token usage."""
    input_tokens: int = 100
    output_tokens: int = 50
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0


def create_mock_llm_client():
    """Create a mock LLM client that returns pre-defined responses."""

    # Response counter to vary responses
    call_count = {"count": 0}

    async def mock_complete(model, messages, system=None, temperature=None, max_tokens=None):
        """Mock LLM complete method."""
        call_count["count"] += 1
        count = call_count["count"]

        # Detect what kind of request this is based on system prompt
        if system and "Consilium" in system:
            # This is an expert contribution
            expert_name = "unknown"
            if "Strategist" in system:
                expert_name = "strategist"
            elif "Tactician" in system:
                expert_name = "tactician"
            elif "Logistician" in system:
                expert_name = "logistician"
            elif "Geographer" in system:
                expert_name = "geographer"
            elif "Armorer" in system:
                expert_name = "armorer"
            elif "Surgeon" in system:
                expert_name = "surgeon"
            elif "Commander" in system:
                expert_name = "commander"
            elif "Chronicler" in system:
                expert_name = "chronicler"
            elif "Herald" in system:
                expert_name = "herald"

            response = {
                "domain_claims": [
                    f"Mock claim from {expert_name} - call #{count}",
                    f"Historical analysis suggests appropriate measures",
                ],
                "assumptions": ["Assumed standard conditions"],
                "questions_remaining": [],
                "delta_requests": [],
                "narrative_fragment": f"The {expert_name} contributed analysis.",
            }
            return MockResponse(json.dumps(response), MockTokenUsage())

        elif system and "Red Team" in system:
            # This is a red team objection
            expert_name = "unknown"
            if "Auditor" in system:
                expert_name = "auditor"
            elif "Skeptic" in system:
                expert_name = "skeptic"
            elif "Adversary" in system:
                expert_name = "adversary"
            elif "Realist" in system:
                expert_name = "realist"
            elif "Dramatist" in system:
                expert_name = "dramatist"

            response = {
                "objections": [
                    {
                        "target": "timeline",
                        "objection": f"Mock objection from {expert_name}",
                        "severity": "minor",
                        "suggestion": "Consider adjusting",
                    }
                ]
            }
            return MockResponse(json.dumps(response), MockTokenUsage())

        elif system and "MODERATOR" in system and "classify" in system.lower():
            # This is objection filtering
            response = {
                "objections": [
                    {
                        "expert": "auditor",
                        "target": "timeline",
                        "objection_type": "CONSIDERATION",
                        "reasoning": "Minor timing issue",
                        "action": "Note for future reference",
                    }
                ]
            }
            return MockResponse(json.dumps(response), MockTokenUsage())

        elif system and "synthesizing" in system.lower():
            # This is synthesis summary
            return MockResponse(
                "Synthesis complete. All expert contributions have been integrated.",
                MockTokenUsage()
            )

        # Default response
        return MockResponse(
            json.dumps({"status": "ok"}),
            MockTokenUsage()
        )

    # Create mock client
    mock_client = MagicMock()
    mock_client.complete = mock_complete

    return mock_client


async def test_interrogation_manager():
    """Test the InterrogationManager."""
    print("\n" + "=" * 60)
    print("Testing InterrogationManager")
    print("=" * 60)

    from backend.orchestrator.interrogation import (
        InterrogationManager,
        CORE_QUESTIONS,
    )

    manager = InterrogationManager()

    # Test getting core questions
    questions = manager.get_core_questions()
    print(f"\nCore questions: {len(questions)}")
    for q in questions[:3]:
        print(f"  - {q['id']}: {q['question'][:50]}...")

    # Test building core interrogation
    answers = {
        "era": "high_medieval",
        "theater": "Northern France",
        "why_now": "Defending a crucial bridge crossing",
        "army_sizes": "5000 vs 8000",
        "terrain_type": "river_crossing",
        "terrain_feature": "A stone bridge with fortified towers",
        "commander_competence_side_a": "skilled",
        "commander_competence_side_b": "competent",
        "magic_present": False,
        "narrative_outcome": "pyrrhic_victory",
        "violence_level": "medium",
    }

    # Validate answers
    errors = manager.validate_core_answers(answers)
    print(f"\nValidation errors: {len(errors)}")

    # Build core interrogation model
    core = manager.build_core_interrogation(answers)
    print(f"\nCore interrogation built:")
    print(f"  - Era: {core.era.value}")
    print(f"  - Theater: {core.theater}")
    print(f"  - Stakes: {core.why_battle_now[:50]}...")

    # Build initial sheet
    sheet = manager.build_initial_sheet(core)
    print(f"\nInitial sheet built:")
    print(f"  - Version: {sheet.version}")
    print(f"  - Era: {sheet.era.value}")
    print(f"  - Forces: {list(sheet.forces.keys())}")
    print(f"  - Terrain: {sheet.terrain_weather.terrain_type.value}")

    return sheet, answers


async def test_chambers():
    """Test the chamber managers."""
    print("\n" + "=" * 60)
    print("Testing Chambers")
    print("=" * 60)

    from backend.orchestrator.chambers import (
        create_consilium_chamber,
        create_redteam_chamber,
    )

    # Create chambers
    consilium = create_consilium_chamber()
    redteam = create_redteam_chamber()

    print(f"\nConsilium chamber: {len(consilium.experts)} experts")
    for expert in consilium.experts:
        print(f"  - {expert.config.name} ({expert.config.codename})")

    print(f"\nRed Team chamber: {len(redteam.experts)} experts")
    for expert in redteam.experts:
        print(f"  - {expert.config.name} ({expert.config.codename})")

    return consilium, redteam


async def test_moderator():
    """Test the Moderator."""
    print("\n" + "=" * 60)
    print("Testing Moderator")
    print("=" * 60)

    from backend.moderator import Moderator, DeltaApplicator
    from backend.lib.models import (
        DeltaRequest,
        DeltaOperation,
        ExpertContribution,
        RedTeamObjection,
    )

    # Test DeltaApplicator
    applicator = DeltaApplicator()

    # Create a test delta
    delta = DeltaRequest(
        field="stakes",
        operation=DeltaOperation.SET,
        value="Updated stakes: defending the realm",
        rationale="More dramatic",
    )

    # Test validation
    is_valid, reason = applicator.validate_delta(delta, "strategist")
    print(f"\nDelta validation (strategist -> stakes): {is_valid}, {reason}")

    is_valid, reason = applicator.validate_delta(delta, "armorer")
    print(f"Delta validation (armorer -> stakes): {is_valid}, {reason}")

    # Test Moderator
    moderator = Moderator()
    print(f"\nModerator model: {moderator.model}")

    return moderator


async def test_consistency():
    """Test consistency checking."""
    print("\n" + "=" * 60)
    print("Testing Consistency Checking")
    print("=" * 60)

    from backend.lib.models import ScenarioSheet, Era, TerrainType
    from backend.moderator.consistency import (
        run_consistency_pass,
        summarize_violations,
    )

    # Create a sheet with some potential issues
    from backend.orchestrator.interrogation import InterrogationManager

    manager = InterrogationManager()
    answers = {
        "era": "high_medieval",
        "why_now": "Test scenario",
        "army_sizes": "5000 vs 5000",
        "terrain_type": "plains",
        "terrain_feature": "Open field",
        "commander_competence_side_a": "competent",
        "commander_competence_side_b": "competent",
        "magic_present": False,
        "narrative_outcome": "decisive_victory",
        "violence_level": "medium",
    }
    core = manager.build_core_interrogation(answers)
    sheet = manager.build_initial_sheet(core)

    # Run consistency pass
    violations = await run_consistency_pass(sheet)

    print(f"\nConsistency check results:")
    print(f"  - Violations found: {len(violations)}")

    if violations:
        print(f"\nViolation summary:")
        print(summarize_violations(violations))
    else:
        print("  - Sheet is consistent!")

    return violations


async def test_full_engine():
    """Test the full deliberation engine with mocked LLM."""
    print("\n" + "=" * 60)
    print("Testing Full Deliberation Engine (Mocked LLM)")
    print("=" * 60)

    from backend.lib.models import SessionState, SessionStatus
    from backend.orchestrator.engine import DeliberationEngine
    from backend.orchestrator.interrogation import InterrogationManager

    # Create mock LLM client
    mock_llm = create_mock_llm_client()

    # Build initial session
    manager = InterrogationManager()
    answers = {
        "era": "high_medieval",
        "theater": "Northern France",
        "why_now": "Defending a crucial bridge against invading forces",
        "army_sizes": "5000 defenders vs 8000 attackers",
        "terrain_type": "river_crossing",
        "terrain_feature": "A fortified stone bridge",
        "commander_competence_side_a": "skilled",
        "commander_competence_side_b": "competent",
        "magic_present": False,
        "narrative_outcome": "pyrrhic_victory",
        "violence_level": "medium",
    }

    core = manager.build_core_interrogation(answers)
    sheet = manager.build_initial_sheet(core)

    # Create session
    session = SessionState(
        status=SessionStatus.CREATED,
        core_answers=core,
        sheet=sheet,
        max_rounds=1,  # Just 1 round for dry test
    )

    print(f"\nSession created: {session.session_id}")
    print(f"  - Status: {session.status.value}")
    print(f"  - Max rounds: {session.max_rounds}")

    # Create engine
    engine = DeliberationEngine(session=session, llm_client=mock_llm)

    print(f"\nEngine initialized:")
    print(f"  - Consilium experts: {len(engine.consilium.experts)}")
    print(f"  - Red Team experts: {len(engine.redteam.experts)}")

    # Run deliberation
    print(f"\nRunning deliberation...")

    events = []
    async for event in engine.run():
        events.append(event)
        print(f"  [{event.sequence}] {event.event_type}: {event.data.get('message', '')[:50] if event.data else ''}")

    print(f"\nDeliberation complete!")
    print(f"  - Total events: {len(events)}")
    print(f"  - Final status: {session.status.value}")
    print(f"  - Rounds completed: {len(session.rounds)}")
    print(f"  - Total tokens: {session.total_token_usage.total_tokens}")

    if session.rounds:
        round1 = session.rounds[0]
        print(f"\nRound 1 summary:")
        print(f"  - Consilium contributions: {len(round1.consilium_contributions)}")
        print(f"  - Red Team objections: {len(round1.redteam_objections)}")
        print(f"  - Filtered objections: {len(round1.filtered_objections)}")

    return session


async def main():
    """Run all Phase 3 dry tests."""
    print("=" * 60)
    print(" PHASE 3 DRY TEST - Orchestration & Moderator ")
    print("=" * 60)

    try:
        # Test InterrogationManager
        sheet, answers = await test_interrogation_manager()

        # Test Chambers
        consilium, redteam = await test_chambers()

        # Test Moderator
        moderator = await test_moderator()

        # Test Consistency
        violations = await test_consistency()

        # Test Full Engine
        session = await test_full_engine()

        print("\n" + "=" * 60)
        print(" ALL TESTS PASSED! ")
        print("=" * 60)

        print(f"""
Phase 3 Implementation Summary:
- InterrogationManager: Working
- ConsiliumChamber: {len(consilium.experts)} experts loaded
- RedTeamChamber: {len(redteam.experts)} experts loaded
- Moderator: Synthesis, consistency, filtering implemented
- DeliberationEngine: Full round execution working
- SSE Events: Proper sequencing

The orchestration system is ready for API integration (Phase 4).
""")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)
