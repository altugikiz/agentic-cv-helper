"""In-memory + JSON-file pending question store.

When a risky / unknown question is detected, the question is added here
instead of being answered by the LLM.  The candidate (admin) can then
review and respond via the web UI or API.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
PENDING_FILE = DATA_DIR / "pending_questions.json"


# ── Models ────────────────────────────────────────────────────────────────────


class PendingQuestion(BaseModel):
    """A question awaiting human review."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    sender: str = ""
    message: str = ""
    risk_category: str = ""
    reason: str = ""
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    status: str = "pending"  # pending | answered
    admin_response: Optional[str] = None
    answered_at: Optional[str] = None


# ── Store singleton ───────────────────────────────────────────────────────────


class PendingStore:
    """Thread-safe in-memory store backed by a JSON file."""

    def __init__(self) -> None:
        self._items: dict[str, PendingQuestion] = {}
        self._load()

    # ── Public API ────────────────────────────────────────────────────────

    def add(
        self,
        sender: str,
        message: str,
        risk_category: str,
        reason: str = "",
    ) -> PendingQuestion:
        """Create a new pending question and persist."""
        item = PendingQuestion(
            sender=sender,
            message=message,
            risk_category=risk_category,
            reason=reason,
        )
        self._items[item.id] = item
        self._save()
        logger.info("Pending question added: id=%s category=%s", item.id, risk_category)
        return item

    def get_all(self, status: Optional[str] = None) -> list[PendingQuestion]:
        """Return all items, optionally filtered by status."""
        items = list(self._items.values())
        if status:
            items = [i for i in items if i.status == status]
        # newest first
        items.sort(key=lambda i: i.timestamp, reverse=True)
        return items

    def get_by_id(self, item_id: str) -> Optional[PendingQuestion]:
        """Return a single item by ID, or None."""
        return self._items.get(item_id)

    def respond(self, item_id: str, response: str) -> Optional[PendingQuestion]:
        """Record the admin's response for a pending question."""
        item = self._items.get(item_id)
        if item is None:
            return None
        item.admin_response = response
        item.status = "answered"
        item.answered_at = datetime.now(timezone.utc).isoformat()
        self._save()
        logger.info("Pending question answered: id=%s", item_id)
        return item

    # ── Persistence helpers ───────────────────────────────────────────────

    def _load(self) -> None:
        """Load from JSON file if it exists."""
        if not PENDING_FILE.exists():
            return
        try:
            raw = json.loads(PENDING_FILE.read_text(encoding="utf-8"))
            for entry in raw:
                item = PendingQuestion(**entry)
                self._items[item.id] = item
            logger.info("Loaded %d pending questions from disk", len(self._items))
        except Exception as exc:
            logger.warning("Failed to load pending store: %s", exc)

    def _save(self) -> None:
        """Persist current state to JSON file."""
        DATA_DIR.mkdir(exist_ok=True)
        payload = [item.model_dump() for item in self._items.values()]
        PENDING_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


# Module-level singleton
_store: Optional[PendingStore] = None


def get_pending_store() -> PendingStore:
    """Return the singleton PendingStore instance."""
    global _store
    if _store is None:
        _store = PendingStore()
    return _store
