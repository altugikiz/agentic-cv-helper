# Career Assistant AI Agent

Multi-agent AI system that automatically evaluates employer messages, generates professional responses, and ensures quality via an LLM-as-Judge evaluator before delivery.

## Overview

`agentic-cv-helper` is a multi-agent system built with **FastAPI**, **LangChain**, and **OpenAI GPT-4o** that:

1. **Receives** employer messages via REST API
2. **Detects** risky/unknown questions (salary, legal, etc.) and flags them for human review
3. **Generates** professional responses grounded in your CV/profile
4. **Evaluates** responses using an LLM-as-Judge agent (5 quality criteria)
5. **Revises** responses up to 3 times if quality is below threshold
6. **Notifies** you via Telegram at every key step

## Architecture

```
Employer Message (POST /api/v1/message)
        │
        ▼
┌───────────────────────┐
│ Unknown Question Tool │  ← confidence < 0.4 → Telegram + Human Intervention
└───────────────────────┘
        │ (clean)
        ▼
┌───────────────────────┐
│     Career Agent      │  ← CV/Profile context + GPT-4o
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│  Evaluator Agent      │  ← LLM-as-Judge (5 criteria, 0-1 score)
└───────────────────────┘
        │
   score ≥ 0.75?
   ┌────┴────┐
  YES       NO
   │         │
   │    revision (max 3 iterations)
   │         │
   │    still failing → Telegram notification
   │
   ▼
Response Approved → Logged → Telegram Notification
```

## Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/<username>/agentic-cv-helper.git
cd agentic-cv-helper

# Automated setup
chmod +x scripts/setup_env.sh
./scripts/setup_env.sh

# — OR manual —
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp data/cv_profile_sample.json data/cv_profile.json
```

### 2. Configure

Edit `.env` with your credentials:

```env
OPENAI_API_KEY=sk-...
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=your_chat_id
```

Edit `data/cv_profile.json` with your real CV data.

### 3. Run

```bash
uvicorn app.main:app --reload
```

API docs available at: http://localhost:8000/docs

### 4. Test

```bash
# Unit tests
pytest tests/ -v

# Live demo (server must be running)
python scripts/run_demo.py
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/message` | Send an employer message for processing |
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/api/v1/logs` | Recent event logs |
| `POST` | `/api/v1/test` | Run a predefined test scenario |

### Example Request

```bash
curl -X POST http://localhost:8000/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "sender": "hr@company.com",
    "message": "We would like to invite you for a technical interview next Tuesday."
  }'
```

### Example Response

```json
{
  "response": "Thank you for the invitation! I would be happy to attend...",
  "evaluator_score": 0.91,
  "category": "interview_invitation",
  "status": "approved",
  "human_intervention_required": false,
  "iterations": 1
}
```

## Project Structure

```
agentic-cv-helper/
├── app/
│   ├── main.py                  # FastAPI entry point
│   ├── config.py                # Settings & environment
│   ├── agents/
│   │   ├── career_agent.py      # Primary Career Agent (GPT-4o + LangChain)
│   │   ├── evaluator_agent.py   # LLM-as-Judge Evaluator
│   │   └── agent_loop.py        # Orchestration pipeline
│   ├── tools/
│   │   ├── notification_tool.py # Telegram notifications
│   │   └── unknown_question_tool.py  # Risk detection
│   ├── models/                  # Pydantic request/response models
│   ├── prompts/                 # Prompt templates
│   └── routers/                 # FastAPI routers
├── data/
│   ├── cv_profile.json          # Your CV (gitignored)
│   └── cv_profile_sample.json   # Example schema
├── tests/                       # Pytest test suite
├── scripts/                     # Setup & demo scripts
├── logs/                        # Event logs (gitignored)
└── docs/                        # Documentation
```

## Evaluator Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Professional Tone | 25% | Formal, respectful language |
| Clarity | 20% | Clear and well-structured |
| Completeness | 20% | All questions addressed |
| Safety | 25% | No hallucinations or false claims |
| Relevance | 10% | Directly relevant to the message |

## Tech Stack

- **Python 3.11+** — Core language
- **FastAPI** — REST API framework
- **LangChain + OpenAI** — Agent framework with GPT-4o
- **Pydantic** — Data validation
- **Telegram Bot API** — Mobile notifications
- **pytest** — Testing framework

## License

MIT
