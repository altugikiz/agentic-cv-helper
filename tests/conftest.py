"""Shared pytest fixtures for the Career Assistant test suite."""

from __future__ import annotations

import os
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# Ensure test environment variables are set BEFORE importing app modules
os.environ.setdefault("OPENAI_API_KEY", "test-key-not-real")
os.environ.setdefault("OPENAI_MODEL", "gpt-4o")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "")
os.environ.setdefault("TELEGRAM_CHAT_ID", "")
os.environ.setdefault("EVALUATOR_THRESHOLD", "0.75")
os.environ.setdefault("MAX_REVISION_ITERATIONS", "3")
os.environ.setdefault("UNKNOWN_CONFIDENCE_THRESHOLD", "0.4")
os.environ.setdefault("LOG_LEVEL", "DEBUG")


SAMPLE_CV_PROFILE = {
    "name": "John Doe",
    "title": "Senior Software Engineer",
    "summary": "Experienced software engineer with 7+ years in backend, cloud, and AI/ML.",
    "contact": {
        "email": "john.doe@email.com",
        "linkedin": "https://linkedin.com/in/johndoe",
        "github": "https://github.com/johndoe",
        "location": "Istanbul, Turkey",
    },
    "experience": [
        {
            "company": "TechCorp Inc.",
            "role": "Senior Software Engineer",
            "period": "2021 – Present",
            "description": (
                "Leading backend team. Built LLM-powered automation with LangChain. "
                "Microservices architecture serving 2M+ requests/day."
            ),
            "technologies": ["Python", "FastAPI", "LangChain", "OpenAI", "PostgreSQL", "Docker", "AWS"],
        },
    ],
    "education": [
        {
            "institution": "Istanbul Technical University",
            "degree": "M.Sc.",
            "field": "Computer Engineering",
            "period": "2014 – 2016",
        },
    ],
    "skills": {
        "languages": ["Python", "TypeScript", "Go", "SQL"],
        "frameworks": ["FastAPI", "Django", "LangChain"],
        "ai_ml": ["OpenAI API", "LangChain", "FAISS", "Prompt Engineering", "RAG"],
    },
    "certifications": [
        {"name": "AWS Solutions Architect – Associate", "issuer": "AWS", "year": 2022},
    ],
    "languages": [
        {"language": "Turkish", "level": "Native"},
        {"language": "English", "level": "Fluent (C1)"},
    ],
    "projects": [
        {
            "name": "LLM Customer Support Agent",
            "description": "Multi-agent system using LangChain for automated customer ticket triage.",
            "technologies": ["Python", "LangChain", "OpenAI", "FastAPI"],
        },
    ],
    "preferences": {
        "work_type": "Remote or Hybrid",
        "notice_period": "1 month",
        "willing_to_relocate": False,
        "preferred_roles": ["Senior Software Engineer", "AI/ML Engineer"],
    },
}


@pytest.fixture
def cv_profile() -> dict:
    """Return a sample CV profile dict for tests."""
    return SAMPLE_CV_PROFILE.copy()


@pytest.fixture
def client() -> TestClient:
    """FastAPI synchronous test client."""
    from app.main import app

    return TestClient(app)


def _make_career_response(
    response: str = "Thank you for your message.",
    confidence: float = 0.9,
    category: str = "interview_invitation",
) -> str:
    """Helper to build a mock Career Agent JSON response string."""
    return json.dumps({
        "response": response,
        "confidence": confidence,
        "category": category,
    })


def _make_evaluator_response(
    overall_score: float = 0.90,
    approved: bool = True,
    feedback: str = "Good response.",
) -> str:
    """Helper to build a mock Evaluator Agent JSON response string."""
    return json.dumps({
        "scores": {
            "professional_tone": overall_score,
            "clarity": overall_score,
            "completeness": overall_score,
            "safety": overall_score,
            "relevance": overall_score,
        },
        "overall_score": overall_score,
        "feedback": feedback,
        "approved": approved,
    })
