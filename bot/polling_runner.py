from __future__ import annotations

import asyncio
import fcntl
from pathlib import Path

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

_polling_lock = asyncio.Lock()
_polling_started = False
_POLLING_LOCK_PATH = Path("/tmp/pes_data_telegram_polling.lock")
_lock_handle = None


def _acquire_process_lock() -> bool:
    """Один polling на инстанс (несколько uvicorn workers)."""
    global _lock_handle
    try:
        _POLLING_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        _lock_handle = open(_POLLING_LOCK_PATH, "w")
        fcntl.flock(_lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_handle.write(str(__import__("os").getpid()))
        _lock_handle.flush()
        return True
    except (OSError, BlockingIOError):
        _lock_handle = None
        return False


async def run_telegram_polling() -> None:
    """Long polling рядом с FastAPI — надёжнее webhook на ONREZA."""
    global _polling_started
    if not _acquire_process_lock():
        logger.info("Telegram polling already running in another worker")
        return
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

    async def _outbox_worker() -> None:
        from services.telegram_outbox_service import process_outbox_batch

        while True:
            try:
                n = await process_outbox_batch(bot)
                await asyncio.sleep(0.8 if n else 2.5)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Telegram outbox worker error")
                await asyncio.sleep(5.0)

    outbox_task = asyncio.create_task(_outbox_worker(), name="telegram_outbox")
    logger.info("Telegram outbox worker started")
    try:
        logger.info("Telegram long polling started")
        await dp.start_polling(bot, handle_signals=False)
    finally:
        outbox_task.cancel()
        try:
            await outbox_task
        except asyncio.CancelledError:
            pass
