"""Agent Loop — orchestrates the full message-processing pipeline.

Flow:
1. Send "new message" notification
2. Run Unknown Question Detection (keyword-only, NO LLM call)
   → if risky → add to pending queue → notify via Telegram → return
     human_intervention with "Yanıtınız hazırlanıyor" message
3. Career Agent generates response
4. Evaluator Agent scores the response
   → if approved → notify + return
   → if not → revision loop (max N iterations)
   → if still not approved → notify failure + return human_intervention_required
5. Log every event
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import get_settings, load_cv_profile
from app.agents.career_agent import CareerAgent
from app.agents.evaluator_agent import EvaluatorAgent
from app.tools.unknown_question_tool import UnknownQuestionTool
from app.tools.notification_tool import NotificationTool
from app.models.response_models import MessageResponse
from app.models.pending_store import get_pending_store

logger = logging.getLogger(__name__)


def _create_tools() -> tuple[UnknownQuestionTool, NotificationTool]:
    """Instantiate tools with current settings."""
    settings = get_settings()
    unknown_tool = UnknownQuestionTool(
        confidence_threshold=settings.unknown_confidence_threshold,
    )
    notify_tool = NotificationTool(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
    )
    return unknown_tool, notify_tool


async def process_message(sender: str, message: str) -> MessageResponse:
    """End-to-end pipeline: receive employer message → return approved response.

    Parameters
    ----------
    sender  : identifier of the employer (email, name, etc.)
    message : the employer's raw message text

    Returns
    -------
    MessageResponse (Pydantic model)
    """
    settings = get_settings()
    unknown_tool, notify_tool = _create_tools()

    # ── 1. Notify: new message ────────────────────────────────────────────
    await notify_tool._arun(
        notification_type="new_message",
        payload={"sender": sender, "message": message},
    )

    # ── 2. Unknown Question Detection (keyword-only, NO LLM cost) ─────────
    uq_result = await unknown_tool._arun(message=message)

    if uq_result["is_unknown"]:
        # Add to pending queue
        store = get_pending_store()
        pending = store.add(
            sender=sender,
            message=message,
            risk_category=uq_result["risk_category"],
            reason=uq_result["reason"],
        )

        # Notify human via Telegram
        await notify_tool._arun(
            notification_type="unknown_question",
            payload={
                "sender": sender,
                "message": message,
                "reason": uq_result["reason"],
                "risk_category": uq_result["risk_category"],
                "pending_id": pending.id,
            },
        )

        result = MessageResponse(
            response="Sorunuz alınmıştır. En kısa sürede size dönüş yapılacaktır.",
            evaluator_score=0.0,
            category=uq_result["risk_category"] or "unknown",
            status="human_intervention",
            human_intervention_required=True,
            iterations=0,
            pending_id=pending.id,
        )
        _log_event(sender, message, result)
        return result

    # ── 3. Career Agent — first pass ──────────────────────────────────────
    career_agent = CareerAgent()
    agent_output = await career_agent.generate_response(message)

    response_text: str = agent_output["response"]
    confidence: float = agent_output["confidence"]
    category: str = agent_output["category"]
    # ── 4. Evaluator loop ─────────────────────────────────────────────────
    evaluator = EvaluatorAgent()
    iterations = 0
    max_iter = settings.max_revision_iterations

    for iteration in range(1, max_iter + 1):
        iterations = iteration
        eval_result = await evaluator.evaluate(message, response_text)

        logger.info(
            "Evaluator iteration %d/%d — score=%.3f approved=%s",
            iteration, max_iter, eval_result.overall_score, eval_result.approved,
        )

        if eval_result.approved:
            # ── 5a. Approved — notify and return ──────────────────────────
            await notify_tool._arun(
                notification_type="response_approved",
                payload={
                    "sender": sender,
                    "category": category,
                    "score": eval_result.overall_score,
                    "iterations": iterations,
                    "response": response_text,
                },
            )
            result = MessageResponse(
                response=response_text,
                evaluator_score=eval_result.overall_score,
                category=category,
                status="approved",
                human_intervention_required=False,
                iterations=iterations,
            )
            _log_event(sender, message, result)
            return result

        # ── 5b. Not approved — request revision ──────────────────────────
        if iteration < max_iter:
            logger.info("Requesting revision (iteration %d)…", iteration)
            revised = await career_agent.revise_response(
                employer_message=message,
                previous_response=response_text,
                feedback=eval_result.feedback,
                score=eval_result.overall_score,
                category=category,
            )
            response_text = revised["response"]
            confidence = revised["confidence"]
            category = revised.get("category", category)

    # ── 6. Max iterations exhausted ───────────────────────────────────────
    await notify_tool._arun(
        notification_type="evaluation_failed",
        payload={
            "sender": sender,
            "score": eval_result.overall_score,
            "threshold": settings.evaluator_threshold,
            "iterations": iterations,
            "response": response_text,
            "feedback": eval_result.feedback,
        },
    )

    result = MessageResponse(
        response=response_text,
        evaluator_score=eval_result.overall_score,
        category=category,
        status="revision_failed",
        human_intervention_required=True,
        iterations=iterations,
    )
    _log_event(sender, message, result)
    return result


# ── Logging helper ────────────────────────────────────────────────────────────

def _log_event(sender: str, message: str, result: MessageResponse) -> None:
    """Persist a JSON log entry under logs/."""
    settings = get_settings()
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sender": sender,
        "message_preview": message[:120],
        "category": result.category,
        "evaluator_score": result.evaluator_score,
        "status": result.status,
        "human_intervention_required": result.human_intervention_required,
        "iterations": result.iterations,
        "pending_id": result.pending_id,
        "response_preview": result.response[:200],
    }

    log_file = log_dir / "events.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    logger.info("Event logged: sender=%s status=%s score=%.3f",
                sender, result.status, result.evaluator_score)
