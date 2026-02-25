"""Admin router — /api/v1/pending endpoints for human-in-the-loop responses."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.models.pending_store import PendingQuestion, get_pending_store
from app.models.response_models import AdminResponseRequest
from app.tools.notification_tool import NotificationTool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["admin"])


@router.get("/pending", response_model=list[PendingQuestion])
async def list_pending(status: Optional[str] = None) -> list[PendingQuestion]:
    """List all pending questions, optionally filtered by status.

    Query params:
        status: "pending" | "answered" | None (all)
    """
    store = get_pending_store()
    return store.get_all(status=status)


@router.get("/pending/{item_id}", response_model=PendingQuestion)
async def get_pending(item_id: str) -> PendingQuestion:
    """Get a single pending question by ID."""
    store = get_pending_store()
    item = store.get_by_id(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Pending question '{item_id}' not found")
    return item


@router.post("/pending/{item_id}/respond", response_model=PendingQuestion)
async def respond_to_pending(item_id: str, req: AdminResponseRequest) -> PendingQuestion:
    """Submit the admin's manual response for a pending question."""
    store = get_pending_store()
    item = store.get_by_id(item_id)

    if item is None:
        raise HTTPException(status_code=404, detail=f"Pending question '{item_id}' not found")

    if item.status == "answered":
        raise HTTPException(status_code=400, detail="This question has already been answered")

    updated = store.respond(item_id, req.response)

    # Send Telegram notification about admin response
    settings = get_settings()
    notify_tool = NotificationTool(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
    )
    await notify_tool._arun(
        notification_type="admin_response",
        payload={
            "sender": updated.sender,
            "message": updated.message,
            "response": req.response,
            "pending_id": item_id,
        },
    )

    # Log the admin response event
    _log_admin_response(updated)

    return updated


def _log_admin_response(item: PendingQuestion) -> None:
    """Persist an admin-response log entry."""
    settings = get_settings()
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "admin_response",
        "pending_id": item.id,
        "sender": item.sender,
        "message_preview": item.message[:120],
        "risk_category": item.risk_category,
        "admin_response_preview": (item.admin_response or "")[:200],
    }

    log_file = log_dir / "events.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    logger.info("Admin response logged: pending_id=%s", item.id)
