"""Unknown Question Detection Tool.

Detects messages that the Career Agent should NOT answer automatically,
such as salary negotiations, legal/contractual questions, and topics
outside the candidate's CV expertise.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ── Risk keyword patterns (case-insensitive) ─────────────────────────────────

RISK_PATTERNS: list[tuple[str, str]] = [
    # Salary / compensation
    (r"\b(salary|compensation|pay\s?(range|scale|rate)?|wage|remuneration|minimum.*(accept|expect))\b",
     "salary_negotiation"),
    # Legal / contractual
    (r"\b(non[- ]?compete|nda|non[- ]?disclosure|contract\s?clause|legal|lawsuit|litigation|arbitration)\b",
     "legal_contractual"),
    # Relocation pressure
    (r"\b(must\s+relocate|mandatory\s+relocation|visa\s+sponsor)\b",
     "relocation_pressure"),
    # Background / discrimination
    (r"\b(criminal\s+record|background\s+check|marital\s+status|religion|political)\b",
     "sensitive_personal"),
    # Financial details
    (r"\b(bank\s+account|social\s+security|tax\s+id|ssn)\b",
     "financial_personal"),
]


class UnknownQuestionInput(BaseModel):
    """Input schema for the Unknown Question Detection tool."""

    message: str = Field(..., description="The employer's original message")
    confidence: float = Field(
        ..., ge=0, le=1,
        description="Career Agent's self-reported confidence score",
    )


class UnknownQuestionOutput(BaseModel):
    """Output schema for the Unknown Question Detection tool."""

    is_unknown: bool = Field(..., description="Whether the question is flagged as unknown/risky")
    reason: str = Field(default="", description="Human-readable explanation")
    risk_category: str = Field(default="", description="Risk category identified")
    confidence: float = Field(..., ge=0, le=1, description="Original confidence score")


class UnknownQuestionTool(BaseTool):
    """Detects risky or unanswerable employer questions."""

    name: str = "unknown_question_detector"
    description: str = (
        "Analyses an employer message and the Career Agent's confidence score to determine "
        "whether the question is risky, outside the candidate's expertise, or requires human "
        "intervention. Returns {is_unknown, reason, risk_category, confidence}."
    )
    args_schema: Type[BaseModel] = UnknownQuestionInput

    # Configurable threshold — injected from settings
    confidence_threshold: float = 0.4

    def _run(self, message: str, confidence: float) -> dict[str, Any]:
        """Synchronous detection logic."""
        return self._detect(message, confidence)

    async def _arun(self, message: str, confidence: float) -> dict[str, Any]:
        """Async wrapper — detection is CPU-only so just delegates."""
        return self._detect(message, confidence)

    # ── Core logic ────────────────────────────────────────────────────────

    def _detect(self, message: str, confidence: float) -> dict[str, Any]:
        # 1. Check keyword risk patterns
        risk_match = self._match_risk_patterns(message)
        if risk_match:
            reason, category = risk_match
            logger.warning("Unknown-Q detected (keyword): category=%s reason=%s", category, reason)
            return UnknownQuestionOutput(
                is_unknown=True,
                reason=reason,
                risk_category=category,
                confidence=confidence,
            ).model_dump()

        # 2. Check confidence threshold
        if confidence < self.confidence_threshold:
            reason = (
                f"Career Agent confidence ({confidence:.2f}) is below threshold "
                f"({self.confidence_threshold}). The message may be outside the candidate's expertise."
            )
            logger.warning("Unknown-Q detected (low confidence): %.2f < %.2f",
                           confidence, self.confidence_threshold)
            return UnknownQuestionOutput(
                is_unknown=True,
                reason=reason,
                risk_category="low_confidence",
                confidence=confidence,
            ).model_dump()

        # 3. All clear
        return UnknownQuestionOutput(
            is_unknown=False,
            reason="",
            risk_category="",
            confidence=confidence,
        ).model_dump()

    @staticmethod
    def _match_risk_patterns(message: str) -> Optional[tuple[str, str]]:
        """Return (reason, category) for the first matching risk pattern, or None."""
        lower = message.lower()
        for pattern, category in RISK_PATTERNS:
            if re.search(pattern, lower):
                return (
                    f"Message contains risky content related to '{category}'. "
                    f"Human review recommended.",
                    category,
                )
        return None
