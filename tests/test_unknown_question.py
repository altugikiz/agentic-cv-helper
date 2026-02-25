"""Test 3 — Unknown / Risky Question.

Input:  "What is the minimum salary you would accept and are you willing to sign a non-compete clause?"
Expected: human_intervention_required=True, Telegram notification, NO LLM call
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
    """Salary + non-compete question must be flagged for human intervention
    WITHOUT calling the Career Agent (no LLM cost)."""

    # Career Agent mock — should NOT be called at all for risky questions
    mock_career_llm = AsyncMock()
    mock_career_llm.ainvoke.return_value = MagicMock(content="should not be called")

    with (
        patch("app.agents.career_agent.ChatOpenAI", return_value=mock_career_llm),
        patch("app.tools.notification_tool.NotificationTool._arun", new_callable=AsyncMock) as mock_notify,
        patch("app.agents.agent_loop.get_pending_store") as mock_store_fn,
    ):
        mock_notify.return_value = {"sent": True}

        # Mock the pending store
        mock_store = MagicMock()
        mock_pending = MagicMock()
        mock_pending.id = "test-pending-123"
        mock_store.add.return_value = mock_pending
        mock_store_fn.return_value = mock_store

        from app.agents.agent_loop import process_message

        result = await process_message(
            sender="recruiter@bigco.com",
            message=RISKY_MESSAGE,
        )

    # Core assertion: human intervention is required
    assert result.human_intervention_required is True
    assert result.status == "human_intervention"
    assert result.pending_id == "test-pending-123"

    # The response should be the generic waiting message, NOT an LLM response
    assert "dönüş yapılacaktır" in result.response

    # Career Agent should NOT have been called (no LLM cost)
    mock_career_llm.ainvoke.assert_not_called()

    # Pending store should have been called
    mock_store.add.assert_called_once()

    # Verify notifications: new_message + unknown_question
    notify_calls = [call.kwargs.get("notification_type") or call.args[0]
                    for call in mock_notify.call_args_list]
    assert "new_message" in notify_calls
    assert "unknown_question" in notify_calls


@pytest.mark.asyncio
async def test_unknown_question_keyword_detection():
    """The unknown question tool should detect risk keywords even without confidence (pre-LLM mode)."""
    from app.tools.unknown_question_tool import UnknownQuestionTool

    tool = UnknownQuestionTool(confidence_threshold=0.4)

    # Salary keyword should trigger — no confidence needed (keyword-only mode)
    result = tool._run(
        message="What is the minimum salary you would accept?",
    )
    assert result["is_unknown"] is True
    assert result["risk_category"] == "salary_negotiation"

    # Non-compete keyword — also keyword-only
    result = tool._run(
        message="Are you willing to sign a non-compete clause?",
    )
    assert result["is_unknown"] is True
    assert result["risk_category"] == "legal_contractual"

    # Should also work with confidence provided
    result = tool._run(
        message="What is the minimum salary you would accept?",
        confidence=0.9,
    )
    assert result["is_unknown"] is True
    assert result["risk_category"] == "salary_negotiation"


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


@pytest.mark.asyncio
async def test_keyword_only_mode_safe_message():
    """A safe message without confidence (keyword-only mode) should pass."""
    from app.tools.unknown_question_tool import UnknownQuestionTool

    tool = UnknownQuestionTool(confidence_threshold=0.4)

    result = tool._run(
        message="Can you tell me about your experience with Python?",
    )
    assert result["is_unknown"] is False
    assert result["risk_category"] == ""


def test_pending_store_crud():
    """Test the pending store add, get, and respond operations."""
    from app.models.pending_store import PendingStore

    store = PendingStore()

    # Add a pending question
    item = store.add(
        sender="test@company.com",
        message="What is your salary expectation?",
        risk_category="salary_negotiation",
        reason="Risky content detected",
    )
    assert item.id
    assert item.status == "pending"
    assert item.sender == "test@company.com"
    assert item.admin_response is None

    # Get by ID
    found = store.get_by_id(item.id)
    assert found is not None
    assert found.id == item.id

    # Get all pending
    all_pending = store.get_all(status="pending")
    assert len(all_pending) >= 1

    # Respond
    updated = store.respond(item.id, "We can discuss salary in person.")
    assert updated.status == "answered"
    assert updated.admin_response == "We can discuss salary in person."
    assert updated.answered_at is not None

    # Get all answered
    all_answered = store.get_all(status="answered")
    assert any(i.id == item.id for i in all_answered)
