"""Test 1 — Standard Interview Invitation.

Input:  "We'd like to invite you for a technical interview next Tuesday at 10 AM. Are you available?"
Expected: Polite acceptance, date confirmation, professional tone
Min. Evaluator Score: 0.80
Notifications: ✅ New message + ✅ Response approved
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from tests.conftest import _make_career_response, _make_evaluator_response

INTERVIEW_MESSAGE = (
    "We'd like to invite you for a technical interview next Tuesday at 10 AM. "
    "Are you available?"
)


@pytest.mark.asyncio
async def test_interview_invitation_approved():
    """Career Agent should produce an approved response for a standard interview invite."""

    career_reply = _make_career_response(
        response=(
            "Thank you for the invitation! I would be happy to attend the technical "
            "interview next Tuesday at 10 AM. Could you please share the meeting "
            "details (location or video link)? I look forward to speaking with your team."
        ),
        confidence=0.92,
        category="interview_invitation",
    )

    evaluator_reply = _make_evaluator_response(
        overall_score=0.91,
        approved=True,
        feedback="Professional and complete response. Confirms date and asks for logistics.",
    )

    mock_career_llm = AsyncMock()
    mock_career_llm.ainvoke.return_value = MagicMock(content=career_reply)

    mock_eval_llm = AsyncMock()
    mock_eval_llm.ainvoke.return_value = MagicMock(content=evaluator_reply)

    with (
        patch("app.agents.career_agent.ChatOpenAI", return_value=mock_career_llm),
        patch("app.agents.evaluator_agent.ChatOpenAI", return_value=mock_eval_llm),
        patch("app.tools.notification_tool.NotificationTool._arun", new_callable=AsyncMock) as mock_notify,
    ):
        mock_notify.return_value = {"sent": True}

        from app.agents.agent_loop import process_message

        result = await process_message(
            sender="hr@company.com",
            message=INTERVIEW_MESSAGE,
        )

    # Assertions
    assert result.status == "approved"
    assert result.human_intervention_required is False
    assert result.evaluator_score >= 0.80
    assert result.category == "interview_invitation"
    assert result.iterations >= 1

    # Verify notifications were sent
    notify_calls = [call.kwargs.get("notification_type") or call.args[0]
                    for call in mock_notify.call_args_list]
    assert "new_message" in notify_calls
    assert "response_approved" in notify_calls


@pytest.mark.asyncio
async def test_interview_invitation_response_is_polite():
    """The generated response text should contain polite/accepting language."""

    career_reply = _make_career_response(
        response=(
            "Thank you so much for considering me. I am available next Tuesday at 10 AM "
            "and would be delighted to attend the interview. Please let me know the format "
            "and any preparation materials I should review."
        ),
        confidence=0.95,
        category="interview_invitation",
    )

    evaluator_reply = _make_evaluator_response(overall_score=0.93, approved=True)

    mock_career_llm = AsyncMock()
    mock_career_llm.ainvoke.return_value = MagicMock(content=career_reply)

    mock_eval_llm = AsyncMock()
    mock_eval_llm.ainvoke.return_value = MagicMock(content=evaluator_reply)

    with (
        patch("app.agents.career_agent.ChatOpenAI", return_value=mock_career_llm),
        patch("app.agents.evaluator_agent.ChatOpenAI", return_value=mock_eval_llm),
        patch("app.tools.notification_tool.NotificationTool._arun", new_callable=AsyncMock) as mock_notify,
    ):
        mock_notify.return_value = {"sent": True}

        from app.agents.agent_loop import process_message

        result = await process_message(
            sender="hr@techcorp.com",
            message=INTERVIEW_MESSAGE,
        )

    response_lower = result.response.lower()
    # Response should contain polite / accepting elements
    assert any(word in response_lower for word in ["thank", "happy", "delighted", "pleased", "available"])
