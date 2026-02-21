"""Career Agent — generates professional responses to employer messages.

Uses LangChain with OpenAI GPT-4o and tool-calling to:
1. Classify the employer's message
2. Generate a professional response grounded in the candidate's CV
3. Report a self-assessed confidence score
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import get_settings, load_cv_profile
from app.prompts.career_agent_prompt import build_career_agent_system_prompt

logger = logging.getLogger(__name__)


class CareerAgent:
    """Stateless agent that produces a single professional response per call."""

    def __init__(self, cv_profile: dict | None = None) -> None:
        settings = get_settings()
        self._cv_profile = cv_profile if cv_profile is not None else load_cv_profile()
        self._system_prompt = build_career_agent_system_prompt(self._cv_profile)
        self._llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.4,
            model_kwargs={"response_format": {"type": "json_object"}},
        )

    # ── Public API ────────────────────────────────────────────────────────

    async def generate_response(self, employer_message: str) -> dict[str, Any]:
        """Generate a response for the given employer message.

        Returns
        -------
        dict with keys: response (str), confidence (float), category (str)
        """
        messages = [
            SystemMessage(content=self._system_prompt),
            HumanMessage(content=employer_message),
        ]

        raw = await self._llm.ainvoke(messages)
        return self._parse_output(raw.content)

    async def revise_response(
        self,
        employer_message: str,
        previous_response: str,
        feedback: str,
        score: float,
        category: str,
    ) -> dict[str, Any]:
        """Generate an improved response based on evaluator feedback.

        Returns
        -------
        dict with keys: response (str), confidence (float), category (str)
        """
        from app.prompts.evaluator_prompt import build_revision_request

        settings = get_settings()
        revision_prompt = build_revision_request(
            employer_message=employer_message,
            previous_response=previous_response,
            feedback=feedback,
            score=score,
            threshold=settings.evaluator_threshold,
            category=category,
        )

        messages = [
            SystemMessage(content=self._system_prompt),
            HumanMessage(content=revision_prompt),
        ]

        raw = await self._llm.ainvoke(messages)
        return self._parse_output(raw.content)

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _parse_output(content: str) -> dict[str, Any]:
        """Parse LLM JSON output robustly."""
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
            else:
                logger.error("Failed to parse Career Agent output: %s", content[:200])
                data = {
                    "response": content,
                    "confidence": 0.3,
                    "category": "unknown",
                }

        # Ensure required keys
        data.setdefault("response", "")
        data.setdefault("confidence", 0.5)
        data.setdefault("category", "unknown")
        data["confidence"] = float(data["confidence"])

        return data
