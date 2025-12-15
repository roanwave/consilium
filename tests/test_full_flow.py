"""
End-to-end integration test for Consilium deliberation flow.
Run with: python -m tests.test_full_flow
"""

import asyncio
import json
from typing import Any

import httpx

BASE_URL = "http://localhost:8001"


async def test_full_flow():
    async with httpx.AsyncClient(timeout=300.0) as client:
        print("=" * 60)
        print("CONSILIUM INTEGRATION TEST")
        print("=" * 60)

        # 1. Health check
        print("\n[1] Health check...")
        r = await client.get(f"{BASE_URL}/health")
        assert r.status_code == 200, f"Health check failed: {r.text}"
        print(f"    OK: {r.json()}")

        # 2. Create scenario
        print("\n[2] Creating scenario...")
        scenario_input = {"prompt": "Two armies meet at a river ford in late autumn."}

        r = await client.post(f"{BASE_URL}/api/scenario", json=scenario_input)
        assert r.status_code == 200, f"Scenario creation failed: {r.text}"
        data = r.json()
        session_id = data["session_id"]
        print(f"    Session: {session_id}")
        print(f"    Status: {data['status']}")
        print(f"    Core questions: {len(data['core_questions'])}")

        # 3. Submit answers
        print("\n[3] Submitting interrogation answers...")
        answers = {
            "core_answers": {
                "era": "high_medieval",
                "theater": "Western European river valley",
                "why_battle_now": "The attackers are a mercenary company that must cross before winter or face starvation. The defenders are local levies protecting their lord's lands.",
                "army_sizes": "Attackers: ~3000 (mixed infantry and cavalry, professional). Defenders: ~1500 (mostly infantry levies with some men-at-arms).",
                "terrain_type": "river_crossing",
                "terrain_feature": "Muddy ford with steep banks on defender side. Woods on attacker's left flank.",
                "commander_competence_side_a": "skilled",
                "commander_competence_side_b": "competent",
                "magic_present": False,
                "magic_constraints": "",
                "narrative_outcome": "pyrrhic_victory",
                "violence_level": "medium",
            },
            "expert_answers": {},
        }

        r = await client.post(
            f"{BASE_URL}/api/scenario/{session_id}/answers", json=answers
        )
        assert r.status_code == 200, f"Answers submission failed: {r.text}"
        data = r.json()
        print(f"    Status: {data['status']}")
        print(f"    Ready to deliberate: {data['ready_to_deliberate']}")

        # 4. Stream deliberation
        print("\n[4] Starting deliberation stream...")
        print("    (This may take several minutes with real LLM calls)")
        print("-" * 60)

        event_count = 0
        current_round = 0
        experts_seen: set[str] = set()
        final_status = None

        async with client.stream(
            "GET", f"{BASE_URL}/api/deliberate/{session_id}"
        ) as response:
            assert response.status_code == 200, f"Stream failed: {response.status_code}"

            event_type = ""
            async for line in response.aiter_lines():
                if not line:
                    continue

                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    data_str = line.split(":", 1)[1].strip()
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        data = {}

                    event_count += 1

                    # Log key events
                    if event_type == "session_start":
                        print(f"\n    SESSION STARTED")

                    elif event_type == "round_start":
                        current_round = data.get("round", current_round + 1)
                        print(f"\n    === ROUND {current_round} ===")

                    elif event_type == "expert_start":
                        expert = data.get("expert", "unknown")
                        chamber = data.get("chamber", "unknown")
                        print(f"    [{chamber}] {expert} starting...")

                    elif event_type == "expert_contribution":
                        expert = data.get("expert", "unknown")
                        experts_seen.add(expert)
                        claims = data.get("domain_claims", [])
                        print(f"    [{expert}] contributed {len(claims)} claims")

                    elif event_type == "expert_error":
                        expert = data.get("expert", "unknown")
                        error = data.get("error", "unknown")
                        print(f"    [{expert}] ERROR: {error}")

                    elif event_type == "moderator_synthesis":
                        print(f"    [moderator] Synthesis complete")

                    elif event_type == "redteam_objection":
                        expert = data.get("expert", "unknown")
                        obj_type = data.get("objection_type", "unknown")
                        print(f"    [RED: {expert}] {obj_type}")

                    elif event_type == "moderator_filter":
                        structural = len(data.get("structural", []))
                        refinable = len(data.get("refinable", []))
                        print(
                            f"    [moderator] Filtered: {structural} structural, {refinable} refinable"
                        )

                    elif event_type == "round_end":
                        certified = data.get("certified", False)
                        print(f"    Round {current_round} complete (certified={certified})")

                    elif event_type == "certified":
                        print(f"\n    CERTIFIED!")
                        final_status = "certified"
                        break

                    elif event_type == "certification_failed":
                        reason = data.get("reason", "unknown")
                        print(f"\n    CERTIFICATION FAILED: {reason}")
                        final_status = "failed"
                        break

                    elif event_type == "session_end":
                        success = data.get("success", False)
                        print(f"\n    Session ended (success={success})")
                        final_status = "certified" if success else "failed"
                        break

                    elif event_type == "session_error":
                        error = data.get("error", "unknown")
                        print(f"\n    SESSION ERROR: {error}")
                        final_status = "error"
                        break

        print("-" * 60)
        print(f"    Total events: {event_count}")
        print(f"    Experts seen: {sorted(experts_seen)}")
        print(f"    Final status: {final_status}")

        # 5. Get output
        print("\n[5] Fetching final output...")
        r = await client.get(f"{BASE_URL}/api/output/{session_id}")

        if r.status_code == 200:
            output = r.json()
            print(f"    Status: {output['status']}")

            sheet = output.get("sheet", {})
            if sheet:
                title = sheet.get("title", "Untitled")
                overview = sheet.get("overview", "N/A")
                print(f"\n    Title: {title}")
                print(f"    Overview: {overview[:200]}...")

                # Save markdown output
                output_path = f"tests/output_{session_id[:8]}.json"
                with open(output_path, "w") as f:
                    json.dump(output, f, indent=2, default=str)
                print(f"\n    Output saved to: {output_path}")

        else:
            print(f"    Output fetch failed: {r.status_code}")
            print(f"    {r.text[:500]}")

        print("\n" + "=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)

        return final_status == "certified"


if __name__ == "__main__":
    success = asyncio.run(test_full_flow())
    exit(0 if success else 1)
