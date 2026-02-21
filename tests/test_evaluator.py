"""Test 2 — Technical Question.

Input:  "Can you describe your experience with LangChain agents and tool-calling mechanisms?"
Expected: CV-based, accurate, concise technical explanation
Min. Evaluator Score: 0.75
Notifications: ✅ New message + ✅ Response approved
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from tests.conftest import _make_career_response, _make_evaluator_response

TECHNICAL_MESSAGE = (
    "Can you describe your experience with LangChain agents and "
    "tool-calling mechanisms?"
)


@pytest.mark.asyncio
async def test_technical_question_approved():
    """Career Agent should produce an approved technical answer grounded in CV."""

    career_reply = _make_career_response(
        response=(
            "Certainly! At TechCorp, I designed and deployed a multi-agent system using "
            "LangChain's tool-calling agent framework with OpenAI GPT-4. The system uses "
            "ReAct-style reasoning where each agent has access to custom tools—such as "
            "database lookups, API integrations, and a notification service. I leveraged "
            "`create_tool_calling_agent` for structured tool invocation and "
            "`AgentExecutor` for orchestration. This reduced customer ticket resolution "
            "time by 40%. I'm well-versed in prompt engineering, function calling, and "
            "building reliable agent loops with retry logic."
        ),
        confidence=0.88,
        category="technical_question",
    )

    evaluator_reply = _make_evaluator_response(
        overall_score=0.87,
        approved=True,
        feedback=(
            "Strong technical answer grounded in real experience. "
            "Mentions specific tools and quantifiable impact."
        ),
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
            sender="engineering@startup.io",
            message=TECHNICAL_MESSAGE,
        )

    assert result.status == "approved"
    assert result.human_intervention_required is False
    assert result.evaluator_score >= 0.75
    assert result.category == "technical_question"

    # Verify notifications
    notify_calls = [call.kwargs.get("notification_type") or call.args[0]
                    for call in mock_notify.call_args_list]
    assert "new_message" in notify_calls
    assert "response_approved" in notify_calls


@pytest.mark.asyncio
async def test_technical_question_revision_cycle():
    """If evaluator score is below threshold, a revision should be triggered."""

    # First attempt — below threshold
    career_reply_v1 = _make_career_response(
        response="I have used LangChain.",
        confidence=0.70,
        category="technical_question",
    )
    # Revised attempt — improved
    career_reply_v2 = _make_career_response(
        response=(
            "At TechCorp, I built a multi-agent customer support system using LangChain's "
            "tool-calling framework. Each agent had structured tools for database queries, "
            "API calls, and notifications, orchestrated via AgentExecutor."
        ),
        confidence=0.88,
        category="technical_question",
    )

    eval_fail = _make_evaluator_response(
        overall_score=0.60,
        approved=False,
        feedback="Response is too vague. Add specific projects, tools, and outcomes.",
    )
    eval_pass = _make_evaluator_response(overall_score=0.85, approved=True)

    mock_career_llm = AsyncMock()
    mock_career_llm.ainvoke.side_effect = [
        MagicMock(content=career_reply_v1),
        MagicMock(content=career_reply_v2),
    ]

    mock_eval_llm = AsyncMock()
    mock_eval_llm.ainvoke.side_effect = [
        MagicMock(content=eval_fail),
        MagicMock(content=eval_pass),
    ]

    with (
        patch("app.agents.career_agent.ChatOpenAI", return_value=mock_career_llm),
        patch("app.agents.evaluator_agent.ChatOpenAI", return_value=mock_eval_llm),
        patch("app.tools.notification_tool.NotificationTool._arun", new_callable=AsyncMock) as mock_notify,
    ):
        mock_notify.return_value = {"sent": True}

        from app.agents.agent_loop import process_message

        result = await process_message(
            sender="engineering@startup.io",
            message=TECHNICAL_MESSAGE,
        )

    assert result.status == "approved"
    assert result.iterations == 2  # Took a revision
    assert result.evaluator_score >= 0.75
