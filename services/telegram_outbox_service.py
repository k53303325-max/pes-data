from __future__ import annotations

from datetime import datetime, timezone

from aiogram import Bot
from aiogram.enums import ParseMode
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import TelegramOutbox, TelegramOutboxStatus, User
from services.chat_log_service import log_outgoing
from utils.logger import get_logger

logger = get_logger(__name__)


async def enqueue_telegram_message(
    session: AsyncSession,
    user: User,
    text: str,
    *,
    source: str = "admin.chat",
) -> TelegramOutbox:
    row = TelegramOutbox(
        user_id=user.id,
        telegram_id=user.telegram_id,
        text=text[:4000],
        source=source,
        status=TelegramOutboxStatus.PENDING.value,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    logger.info("Telegram outbox queued id=%s user_id=%s", row.id, user.id)
    return row


async def process_outbox_batch(bot: Bot, *, limit: int = 15) -> int:
    from database.database import async_session

    sent = 0
    for _ in range(limit):
        async with async_session() as session:
            row = await session.scalar(
                select(TelegramOutbox)
                .where(TelegramOutbox.status == TelegramOutboxStatus.PENDING.value)
                .order_by(TelegramOutbox.id.asc())
                .limit(1)
            )
            if not row:
                break
            try:
                await bot.send_message(
                    chat_id=row.telegram_id,
                    text=row.text,
                    parse_mode=ParseMode.HTML,
                )
                row.status = TelegramOutboxStatus.SENT.value
                row.sent_at = datetime.now(timezone.utc)
                row.error = None
                await session.commit()
                async with async_session() as log_session:
                    await log_outgoing(
                        log_session,
                        telegram_id=row.telegram_id,
                        content=row.text,
                        message_type="text",
                        source=row.source,
                    )
                sent += 1
            except Exception as exc:
                logger.exception("Outbox send failed id=%s", row.id)
                row.status = TelegramOutboxStatus.FAILED.value
                row.error = str(exc)[:500]
                await session.commit()
    return sent
