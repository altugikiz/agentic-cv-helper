"""Response models for the Career Assistant API."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EvaluatorScores(BaseModel):
    """Individual criterion scores from the Evaluator Agent."""

    professional_tone: float = Field(..., ge=0, le=1, description="Professional tone score")
    clarity: float = Field(..., ge=0, le=1, description="Clarity score")
    completeness: float = Field(..., ge=0, le=1, description="Completeness score")
    safety: float = Field(..., ge=0, le=1, description="Safety score (no hallucination)")
    relevance: float = Field(..., ge=0, le=1, description="Relevance score")


class EvaluatorResult(BaseModel):
    """Full evaluator assessment."""

    scores: EvaluatorScores
    overall_score: float = Field(..., ge=0, le=1, description="Weighted overall score")
    feedback: str = Field(default="", description="Evaluator feedback / improvement notes")
    approved: bool = Field(..., description="Whether the response passed the threshold")


class MessageResponse(BaseModel):
    """Standard response returned by POST /api/v1/message."""

    response: str = Field(..., description="The generated professional response")
    evaluator_score: float = Field(..., ge=0, le=1, description="Final evaluator score")
    category: str = Field(
        ...,
        description="Message category",
        examples=["interview_invitation", "technical_question", "offer_decline", "clarification", "unknown"],
    )
    status: str = Field(
        ...,
        description="Processing status",
        examples=["approved", "revision_failed", "human_intervention"],
    )
    human_intervention_required: bool = Field(
        default=False,
        description="Whether a human needs to handle this message",
    )
    iterations: int = Field(default=1, ge=0, description="Number of revision iterations used (0 = human intervention before evaluation)")
    pending_id: Optional[str] = Field(
        default=None,
        description="ID of the pending question when human intervention is required",
    )


class HealthResponse(BaseModel):
    """Health-check response."""

    status: str = "ok"
    version: str = "1.0.0"


class LogEntry(BaseModel):
    """Single log entry for the /api/v1/logs endpoint."""

    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    sender: str = ""
    message_preview: str = ""
    category: str = ""
    evaluator_score: float = 0.0
    status: str = ""
    human_intervention_required: bool = False
    iterations: int = 1


class AdminResponseRequest(BaseModel):
    """Body for POST /api/v1/pending/{id}/respond."""

    response: str = Field(
        ...,
        min_length=1,
        description="The admin's manual response to the pending question",
    )


class TestResult(BaseModel):
    """Response returned by POST /api/v1/test."""

    test_id: str
    passed: bool
    details: Optional[str] = None
    response: Optional[MessageResponse] = None
