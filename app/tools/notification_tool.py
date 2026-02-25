"""Telegram Notification Tool.

Sends mobile notifications via the Telegram Bot API for key events:
- New employer message received
- Response approved and sent
- Unknown question detected (human intervention needed)
- Evaluator max iterations reached (revision failed)
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Type

import httpx
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


class NotificationType(str, Enum):
    """Supported notification types."""

    NEW_MESSAGE = "new_message"
    RESPONSE_APPROVED = "response_approved"
    UNKNOWN_QUESTION = "unknown_question"
    EVALUATION_FAILED = "evaluation_failed"
    ADMIN_RESPONSE = "admin_response"


# ── Message templates (Markdown) ─────────────────────────────────────────────

TEMPLATES: dict[NotificationType, str] = {
    NotificationType.NEW_MESSAGE: (
        "📩 *New Employer Message*\n\n"
        "**From:** {sender}\n"
        "**Message:**\n{message}"
    ),
    NotificationType.RESPONSE_APPROVED: (
        "✅ *Response Approved*\n\n"
        "**To:** {sender}\n"
        "**Category:** {category}\n"
        "**Evaluator Score:** {score:.2f}\n"
        "**Iterations:** {iterations}\n\n"
        "**Response:**\n{response}"
    ),
    NotificationType.UNKNOWN_QUESTION: (
        "⚠️ *Human Intervention Required*\n\n"
        "**From:** {sender}\n"
        "**Reason:** {reason}\n"
        "**Risk Category:** {risk_category}\n"
        "**Pending ID:** `{pending_id}`\n\n"
        "**Original Message:**\n{message}\n\n"
        "💡 Web panelden yanıtlayın."
    ),
    NotificationType.EVALUATION_FAILED: (
        "❌ *Evaluation Failed — Human Review Needed*\n\n"
        "**From:** {sender}\n"
        "**Final Score:** {score:.2f} (threshold: {threshold:.2f})\n"
        "**Iterations Used:** {iterations}\n\n"
        "**Last Response:**\n{response}\n\n"
        "**Feedback:**\n{feedback}"
    ),
    NotificationType.ADMIN_RESPONSE: (
        "✍️ *Admin Response Submitted*\n\n"
        "**Original Sender:** {sender}\n"
        "**Pending ID:** `{pending_id}`\n\n"
        "**Original Message:**\n{message}\n\n"
        "**Admin Response:**\n{response}"
    ),
}


class NotificationInput(BaseModel):
    """Input schema for the Notification Tool."""

    notification_type: str = Field(
        ...,
        description="Type of notification: new_message | response_approved | unknown_question | evaluation_failed",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value payload for the notification template",
    )


class NotificationTool(BaseTool):
    """Sends Telegram notifications for Career Assistant events."""

    name: str = "telegram_notifier"
    description: str = (
        "Sends a Telegram notification about career assistant events. "
        "Supports types: new_message, response_approved, unknown_question, evaluation_failed."
    )
    args_schema: Type[BaseModel] = NotificationInput

    # Injected from settings
    bot_token: str = ""
    chat_id: str = ""

    def _run(self, notification_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Synchronous send — uses httpx sync client."""
        import asyncio

        payload = payload or {}
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # We're inside an event loop (e.g. FastAPI) — schedule coroutine
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(self._send_sync, notification_type, payload)
                return future.result()
        else:
            return self._send_sync(notification_type, payload)

    async def _arun(self, notification_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Async send — uses httpx async client."""
        payload = payload or {}
        return await self._send_async(notification_type, payload)

    # ── Internal helpers ──────────────────────────────────────────────────

    def _build_message(self, notification_type: str, payload: dict[str, Any]) -> str:
        """Render notification template with payload values."""
        try:
            ntype = NotificationType(notification_type)
        except ValueError:
            return f"🔔 *Notification*\n\nType: {notification_type}\nPayload: {payload}"

        template = TEMPLATES[ntype]
        try:
            return template.format(**payload)
        except KeyError as exc:
            logger.warning("Template key missing: %s — falling back to raw payload", exc)
            return f"🔔 *{ntype.value}*\n\n{payload}"

    def _send_sync(self, notification_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Send via synchronous HTTP request."""
        if not self.bot_token or not self.chat_id:
            logger.info("Telegram not configured — skipping notification: %s", notification_type)
            return {"sent": False, "reason": "telegram_not_configured"}

        text = self._build_message(notification_type, payload)
        url = TELEGRAM_API_URL.format(token=self.bot_token)

        try:
            with httpx.Client(timeout=10) as client:
                resp = client.post(url, json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                })
                resp.raise_for_status()
                logger.info("Telegram notification sent: %s", notification_type)
                return {"sent": True, "notification_type": notification_type}
        except httpx.HTTPError as exc:
            logger.error("Telegram send failed: %s", exc)
            return {"sent": False, "error": str(exc)}

    async def _send_async(self, notification_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Send via async HTTP request."""
        if not self.bot_token or not self.chat_id:
            logger.info("Telegram not configured — skipping notification: %s", notification_type)
            return {"sent": False, "reason": "telegram_not_configured"}

        text = self._build_message(notification_type, payload)
        url = TELEGRAM_API_URL.format(token=self.bot_token)

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                })
                resp.raise_for_status()
                logger.info("Telegram notification sent: %s", notification_type)
                return {"sent": True, "notification_type": notification_type}
        except httpx.HTTPError as exc:
            logger.error("Telegram send failed: %s", exc)
            return {"sent": False, "error": str(exc)}
