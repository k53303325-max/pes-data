from __future__ import annotations

import asyncio

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

_polling_lock = asyncio.Lock()
_polling_started = False


async def run_telegram_polling() -> None:
    """Long polling рядом с FastAPI — надёжнее webhook на ONREZA."""
    global _polling_started
    async with _polling_lock:
        if _polling_started:
            return
        _polling_started = True

    from bot.factory import get_bot, get_dispatcher

    bot = get_bot()
    dp = get_dispatcher()

    try:
        await asyncio.wait_for(bot.delete_webhook(drop_pending_updates=False), timeout=15.0)
        logger.info("Telegram webhook removed (polling mode)")
    except Exception:
        logger.exception("delete_webhook failed (polling continues)")

    logger.info("Telegram long polling started")
    await dp.start_polling(bot, handle_signals=False)
