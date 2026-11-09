from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from config.settings import settings
from services.telegram_notify import _telegram_post
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

RATE_LIMIT = 8
RATE_WINDOW_SEC = 3600
_hits: dict[str, list[float]] = defaultdict(list)

CALLER_LABELS = {
    "sales_team": "Есть отдел продаж",
    "self": "Звоню сам",
    "nobody": "Пока некому звонить",
}


class SiteLeadPayload(BaseModel):
    contact: str = Field(..., min_length=2, max_length=200)
    business: str = Field(..., min_length=2, max_length=4000)
    caller: str = Field(..., min_length=1, max_length=50)
    competitors: str = Field(default="", max_length=4000)
    consent: bool
    source: str = Field(default="direct", max_length=32)
    website: str = Field(default="", max_length=200)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _rate_limit_ok(ip: str) -> bool:
    now = time.time()
    window_start = now - RATE_WINDOW_SEC
    bucket = [t for t in _hits[ip] if t > window_start]
    _hits[ip] = bucket
    if len(bucket) >= RATE_LIMIT:
        return False
    bucket.append(now)
    return True


def _trim(value: str, limit: int) -> str:
    v = value.strip()
    if len(v) <= limit:
        return v
    return v[: limit - 1] + "…"


@router.post("/api/site-lead")
async def site_lead(request: Request, body: SiteLeadPayload):
    if body.website.strip():
        return {"ok": True}

    if not body.consent:
        raise HTTPException(status_code=400, detail="consent_required")

    ip = _client_ip(request)
    if not _rate_limit_ok(ip):
        logger.warning("site-lead rate limit (ip_hash=%s)", hash(ip) % 10_000)
        raise HTTPException(status_code=429, detail="rate_limit")

    if not settings.bot_token or not settings.admin_telegram_id:
        logger.error("site-lead: telegram not configured")
        raise HTTPException(status_code=503, detail="unavailable")

    caller_label = CALLER_LABELS.get(body.caller, body.caller)
    now = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    text = (
        "Новое обращение с сайта\n"
        f"· {now}\n"
        f"· контакт: {_trim(body.contact, 120)}\n"
        f"· бизнес: {_trim(body.business, 500)}\n"
        f"· кто звонит: {caller_label}\n"
    )
    comp = body.competitors.strip()
    if comp:
        text += f"· конкуренты: {_trim(comp, 800)}\n"
    text += f"· источник: {_trim(body.source, 32)}\n· статус: новое"

    ok, _ = await _telegram_post(
        "sendMessage",
        json={
            "chat_id": settings.admin_telegram_id,
            "text": text,
            "disable_web_page_preview": True,
        },
    )
    if not ok:
        raise HTTPException(status_code=502, detail="notify_failed")

    logger.info("site-lead accepted (ip_hash=%s)", hash(ip) % 10_000)
    return {"ok": True}
