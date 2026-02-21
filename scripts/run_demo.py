#!/usr/bin/env python3
"""run_demo.py — Run the 3 predefined test scenarios against the live API.

Usage:
    python scripts/run_demo.py              # default: http://localhost:8000
    python scripts/run_demo.py --base-url http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import sys

import httpx

TEST_SCENARIOS = [
    {
        "id": "test_interview_invitation",
        "name": "Test 1 — Standard Interview Invitation",
        "payload": {
            "sender": "hr@techcorp.com",
            "message": (
                "We'd like to invite you for a technical interview next Tuesday "
                "at 10 AM. Are you available?"
            ),
        },
    },
    {
        "id": "test_technical_question",
        "name": "Test 2 — Technical Question",
        "payload": {
            "sender": "engineering@startup.io",
            "message": (
                "Can you describe your experience with LangChain agents and "
                "tool-calling mechanisms?"
            ),
        },
    },
    {
        "id": "test_unknown_question",
        "name": "Test 3 — Unknown / Risky Question",
        "payload": {
            "sender": "recruiter@bigco.com",
            "message": (
                "What is the minimum salary you would accept and are you "
                "willing to sign a non-compete clause?"
            ),
        },
    },
]


def run_demo(base_url: str) -> None:
    print("═" * 60)
    print(" Career Assistant AI Agent — Demo")
    print("═" * 60)
    print(f"Target: {base_url}\n")

    # Health check
    try:
        resp = httpx.get(f"{base_url}/api/v1/health", timeout=5)
        resp.raise_for_status()
        print(f"✅ Health check: {resp.json()}\n")
    except Exception as exc:
        print(f"❌ Health check failed: {exc}")
        print("   Make sure the server is running: uvicorn app.main:app --reload")
        sys.exit(1)

    results = []
    for scenario in TEST_SCENARIOS:
        print(f"─── {scenario['name']} {'─' * (40 - len(scenario['name']))}")
        print(f"  Sender:  {scenario['payload']['sender']}")
        print(f"  Message: {scenario['payload']['message'][:80]}...")

        try:
            resp = httpx.post(
                f"{base_url}/api/v1/message",
                json=scenario["payload"],
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()

            print(f"  → Status:     {data['status']}")
            print(f"  → Category:   {data['category']}")
            print(f"  → Score:      {data['evaluator_score']:.2f}")
            print(f"  → Iterations: {data['iterations']}")
            print(f"  → Human?:     {data['human_intervention_required']}")
            print(f"  → Response:   {data['response'][:120]}...")
            results.append({"test": scenario["id"], "passed": True, "data": data})
        except Exception as exc:
            print(f"  ❌ Error: {exc}")
            results.append({"test": scenario["id"], "passed": False, "error": str(exc)})
        print()

    # Summary
    print("═" * 60)
    passed = sum(1 for r in results if r["passed"])
    print(f" Results: {passed}/{len(results)} scenarios completed successfully")
    print("═" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Career Assistant demo scenarios")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    args = parser.parse_args()
    run_demo(args.base_url)
