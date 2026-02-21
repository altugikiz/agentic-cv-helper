"""Evaluator Agent — LLM-as-a-Judge for response quality control.

Scores the Career Agent's response on 5 weighted criteria before it is sent
to the employer.  If the score is below the configured threshold the agent
returns actionable feedback so the Career Agent can revise.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import get_settings
from app.models.response_models import EvaluatorResult, EvaluatorScores
from app.prompts.evaluator_prompt import build_evaluator_prompt

logger = logging.getLogger(__name__)


class EvaluatorAgent:
    """Stateless judge that evaluates a candidate response."""

    def __init__(self) -> None:
        settings = get_settings()
        self._threshold = settings.evaluator_threshold
        self._system_prompt = build_evaluator_prompt(self._threshold)
        self._llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.1,  # Low temperature for consistent judgement
            model_kwargs={"response_format": {"type": "json_object"}},
        )

    # ── Public API ────────────────────────────────────────────────────────

    async def evaluate(
        self, employer_message: str, candidate_response: str
    ) -> EvaluatorResult:
        """Score a candidate response against the 5 quality criteria.

        Returns
        -------
        EvaluatorResult  with scores, overall_score, feedback, approved
        """
        user_content = (
            f"EMPLOYER MESSAGE:\n{employer_message}\n\n"
            f"CANDIDATE RESPONSE:\n{candidate_response}"
        )

        messages = [
            SystemMessage(content=self._system_prompt),
            HumanMessage(content=user_content),
        ]

        raw = await self._llm.ainvoke(messages)
        data = self._parse_output(raw.content)
        return self._build_result(data)

    # ── Helpers ───────────────────────────────────────────────────────────

    def _build_result(self, data: dict[str, Any]) -> EvaluatorResult:
        """Convert raw LLM output dict into a validated EvaluatorResult."""
        scores_raw = data.get("scores", {})

        scores = EvaluatorScores(
            professional_tone=float(scores_raw.get("professional_tone", 0)),
            clarity=float(scores_raw.get("clarity", 0)),
            completeness=float(scores_raw.get("completeness", 0)),
            safety=float(scores_raw.get("safety", 0)),
            relevance=float(scores_raw.get("relevance", 0)),
        )

        # Recompute overall score from weights to avoid LLM arithmetic errors
        overall = (
            scores.professional_tone * 0.25
            + scores.clarity * 0.20
            + scores.completeness * 0.20
            + scores.safety * 0.25
            + scores.relevance * 0.10
        )
        overall = round(overall, 4)

        approved = overall >= self._threshold

        return EvaluatorResult(
            scores=scores,
            overall_score=overall,
            feedback=data.get("feedback", ""),
            approved=approved,
        )

    @staticmethod
    def _parse_output(content: str) -> dict[str, Any]:
        """Parse LLM JSON output robustly."""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            logger.error("Failed to parse Evaluator Agent output: %s", content[:200])
            # Return conservative fallback — will trigger revision
            return {
                "scores": {
                    "professional_tone": 0.5,
                    "clarity": 0.5,
                    "completeness": 0.5,
                    "safety": 0.5,
                    "relevance": 0.5,
                },
                "overall_score": 0.5,
                "feedback": "Could not parse evaluator output; manual review recommended.",
                "approved": False,
            }
