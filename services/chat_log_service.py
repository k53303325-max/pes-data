from __future__ import annotations

import html
import re
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import BotMessage, ChatDirection, User
from services.user_service import get_user_by_telegram_id

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(text: str) -> str:
    cleaned = _HTML_TAG_RE.sub("", text)
    return html.unescape(cleaned).strip()


def format_chat_preview(text: str, max_len: int = 120) -> str:
    plain = strip_html(text).replace("\n", " ")
    if len(plain) <= max_len:
        return plain
    return plain[: max_len - 1] + "…"


async def _resolve_user_id(session: AsyncSession, telegram_id: int) -> int | None:
    user = await get_user_by_telegram_id(session, telegram_id)
    if not user:
        return None
    from sqlalchemy import update

    await session.execute(
        update(BotMessage)
        .where(BotMessage.telegram_id == telegram_id, BotMessage.user_id.is_(None))
        .values(user_id=user.id)
    )
    return user.id


async def log_incoming(
    session: AsyncSession,
    *,
    telegram_id: int,
    content: str,
    message_type: str = "text",
    source: str | None = None,
    telegram_message_id: int | None = None,
) -> None:
    user_id = await _resolve_user_id(session, telegram_id)
    session.add(
        BotMessage(
            user_id=user_id,
            telegram_id=telegram_id,
            direction=ChatDirection.IN.value,
            message_type=message_type,
            content=content[:8000],
            source=source,
            telegram_message_id=telegram_message_id,
        )
    )
    await session.commit()


async def log_outgoing(
    session: AsyncSession,
    *,
    telegram_id: int,
    content: str,
    message_type: str = "text",
    source: str | None = None,
) -> None:
    user_id = await _resolve_user_id(session, telegram_id)
    session.add(
        BotMessage(
            user_id=user_id,
            telegram_id=telegram_id,
            direction=ChatDirection.OUT.value,
            message_type=message_type,
            content=content[:8000],
            source=source,
        )
    )
    await session.commit()


async def get_user_chat_messages(
    session: AsyncSession,
    user_id: int,
    *,
    limit: int = 300,
    offset: int = 0,
) -> list[BotMessage]:
    user = await session.get(User, user_id)
    if not user:
        return []
    from sqlalchemy import or_

    result = await session.execute(
        select(BotMessage)
        .where(
            or_(
                BotMessage.user_id == user_id,
                BotMessage.telegram_id == user.telegram_id,
            )
        )
        .order_by(BotMessage.created_at.asc(), BotMessage.id.asc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def count_user_chat_messages(session: AsyncSession, user_id: int) -> int:
    user = await session.get(User, user_id)
    if not user:
        return 0
    from sqlalchemy import or_

    result = await session.execute(
        select(func.count())
        .select_from(BotMessage)
        .where(
            or_(
                BotMessage.user_id == user_id,
                BotMessage.telegram_id == user.telegram_id,
            )
        )
    )
    return int(result.scalar_one())


async def list_recent_chats(session: AsyncSession, *, limit: int = 50) -> list[dict]:
    """Последние диалоги: пользователь + превью последнего сообщения."""
    subq = (
        select(
            BotMessage.user_id,
            func.max(BotMessage.id).label("last_id"),
            func.max(BotMessage.created_at).label("last_at"),
        )
        .where(BotMessage.user_id.isnot(None))
        .group_by(BotMessage.user_id)
        .subquery()
    )
    result = await session.execute(
        select(BotMessage, User)
        .join(subq, BotMessage.id == subq.c.last_id)
        .join(User, User.id == BotMessage.user_id)
        .options(selectinload(User.projects), selectinload(User.payments))
        .order_by(subq.c.last_at.desc())
        .limit(limit)
    )
    rows = result.all()
    chats: list[dict] = []
    for msg, user in rows:
        chats.append(
            {
                "user": user,
                "last_message": msg,
                "preview": format_chat_preview(msg.content),
            }
        )
    return chats
