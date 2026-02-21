"""Test 3 — Unknown / Risky Question.

Input:  "What is the minimum salary you would accept and are you willing to sign a non-compete clause?"
Expected: human_intervention_required=True, Telegram notification
Min. Evaluator Score: N/A (human takes over)
Notifications: ✅ New message + ✅ Human intervention required
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from tests.conftest import _make_career_response, _make_evaluator_response

RISKY_MESSAGE = (
    "What is the minimum salary you would accept and are you willing "
    "to sign a non-compete clause?"
)


@pytest.mark.asyncio
async def test_unknown_question_triggers_human_intervention():
    """Salary + non-compete question must be flagged for human intervention."""

    # Career Agent still produces a response, but confidence will be low
    career_reply = _make_career_response(
        response=(
            "I appreciate your question. Salary expectations and contractual terms "
            "are topics I'd prefer to discuss directly. Could we schedule a call?"
        ),
        confidence=0.25,  # Below 0.4 threshold
        category="unknown",
    )

    mock_career_llm = AsyncMock()
    mock_career_llm.ainvoke.return_value = MagicMock(content=career_reply)

    with (
        patch("app.agents.career_agent.ChatOpenAI", return_value=mock_career_llm),
        patch("app.tools.notification_tool.NotificationTool._arun", new_callable=AsyncMock) as mock_notify,
    ):
        mock_notify.return_value = {"sent": True}

        from app.agents.agent_loop import process_message

        result = await process_message(
            sender="recruiter@bigco.com",
            message=RISKY_MESSAGE,
        )

    # Core assertion: human intervention is required
    assert result.human_intervention_required is True
    assert result.status == "human_intervention"

    # Verify notifications: new_message + unknown_question
    notify_calls = [call.kwargs.get("notification_type") or call.args[0]
                    for call in mock_notify.call_args_list]
    assert "new_message" in notify_calls
    assert "unknown_question" in notify_calls


@pytest.mark.asyncio
async def test_unknown_question_keyword_detection():
    """The unknown question tool should detect risk keywords even with high confidence."""
    from app.tools.unknown_question_tool import UnknownQuestionTool

    tool = UnknownQuestionTool(confidence_threshold=0.4)

    # Salary keyword should trigger regardless of confidence
    result = tool._run(
        message="What is the minimum salary you would accept?",
        confidence=0.9,
    )
    assert result["is_unknown"] is True
    assert result["risk_category"] == "salary_negotiation"

    # Non-compete keyword
    result = tool._run(
        message="Are you willing to sign a non-compete clause?",
        confidence=0.9,
    )
    assert result["is_unknown"] is True
    assert result["risk_category"] == "legal_contractual"


@pytest.mark.asyncio
async def test_safe_question_passes():
    """A normal, safe question should NOT trigger human intervention."""
    from app.tools.unknown_question_tool import UnknownQuestionTool

    tool = UnknownQuestionTool(confidence_threshold=0.4)

    result = tool._run(
        message="Can you tell me about your experience with Python?",
        confidence=0.85,
    )
    assert result["is_unknown"] is False
    assert result["risk_category"] == ""


@pytest.mark.asyncio
async def test_low_confidence_triggers_unknown():
    """Even without risky keywords, low confidence should flag the message."""
    from app.tools.unknown_question_tool import UnknownQuestionTool

    tool = UnknownQuestionTool(confidence_threshold=0.4)

    result = tool._run(
        message="Tell me about quantum computing applications.",
        confidence=0.2,
    )
    assert result["is_unknown"] is True
    assert result["risk_category"] == "low_confidence"
