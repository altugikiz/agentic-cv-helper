"""Message router — /api/v1 endpoints for the Career Assistant."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.agents.agent_loop import process_message
from app.models.request_models import MessageRequest, TestRequest
from app.models.response_models import (
    HealthResponse,
    LogEntry,
    MessageResponse,
    TestResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["career-assistant"])

# ── Predefined test scenarios ────────────────────────────────────────────────

TEST_SCENARIOS: dict[str, dict[str, str]] = {
    "test_interview_invitation": {
        "sender": "hr@techcorp.com",
        "message": (
            "We'd like to invite you for a technical interview next Tuesday "
            "at 10 AM. Are you available?"
        ),
    },
    "test_technical_question": {
        "sender": "engineering@startup.io",
        "message": (
            "Can you describe your experience with LangChain agents and "
            "tool-calling mechanisms?"
        ),
    },
    "test_unknown_question": {
        "sender": "recruiter@bigco.com",
        "message": (
            "What is the minimum salary you would accept and are you "
            "willing to sign a non-compete clause?"
        ),
    },
}


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/message", response_model=MessageResponse)
async def handle_message(req: MessageRequest) -> MessageResponse:
    """Receive an employer message, run the agent loop, return the result."""
    logger.info("Incoming message from %s", req.sender)
    try:
        result = await process_message(sender=req.sender, message=req.message)
        return result
    except Exception as exc:
        logger.exception("Agent loop failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Simple liveness probe."""
    return HealthResponse()


@router.get("/logs", response_model=list[LogEntry])
async def get_logs(limit: int = 20) -> list[LogEntry]:
    """Return the most recent log entries (newest first)."""
    settings = get_settings()
    log_file = Path(settings.log_dir) / "events.jsonl"

    if not log_file.exists():
        return []

    entries: list[LogEntry] = []
    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in reversed(lines[-limit:]):
        try:
            data = json.loads(line.strip())
            entries.append(LogEntry(**data))
        except (json.JSONDecodeError, Exception):
            continue

    return entries


@router.post("/test", response_model=TestResult)
async def run_test(req: TestRequest) -> TestResult:
    """Execute a predefined test scenario and report pass/fail."""
    scenario = TEST_SCENARIOS.get(req.test_id)
    if not scenario:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown test_id '{req.test_id}'. Available: {list(TEST_SCENARIOS.keys())}",
        )

    logger.info("Running test scenario: %s", req.test_id)
    settings = get_settings()

    try:
        result = await process_message(
            sender=scenario["sender"],
            message=scenario["message"],
        )
    except Exception as exc:
        return TestResult(
            test_id=req.test_id,
            passed=False,
            details=f"Agent loop error: {exc}",
        )

    # Determine pass/fail based on test type
    if req.test_id == "test_unknown_question":
        passed = result.human_intervention_required is True
        details = (
            "PASS: human_intervention_required=True"
            if passed
            else "FAIL: expected human_intervention_required=True"
        )
    elif req.test_id == "test_interview_invitation":
        passed = result.evaluator_score >= 0.80 and result.status == "approved"
        details = (
            f"Score: {result.evaluator_score:.2f} (min 0.80), status: {result.status}"
        )
    elif req.test_id == "test_technical_question":
        passed = result.evaluator_score >= 0.75 and result.status == "approved"
        details = (
            f"Score: {result.evaluator_score:.2f} (min 0.75), status: {result.status}"
        )
    else:
        passed = result.status == "approved"
        details = f"Status: {result.status}"

    return TestResult(
        test_id=req.test_id,
        passed=passed,
        details=details,
        response=result,
    )
