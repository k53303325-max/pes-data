from __future__ import annotations

import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, ErrorEvent

from config.settings import settings
from database.database import init_db
from handlers import payments, start
from utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


async def errors_handler(event: ErrorEvent) -> None:
    logger.exception("Unhandled error", exc_info=event.exception)
    update = event.update
    try:
        if update.message:
            await update.message.answer("⚠️ Ошибка. Нажмите /start")
        elif update.callback_query:
            await update.callback_query.answer("⚠️ Ошибка", show_alert=True)
    except Exception:
        pass


async def run_bot() -> None:
    setup_logging()
    logger.info("Starting Пёс Дата bot...")
    await init_db()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.errors.register(errors_handler)
    dp.include_router(start.router)
    dp.include_router(payments.router)

    me = await bot.get_me()
    logger.info("Bot connected: @%s", me.username)

    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню"),
    ])

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Polling started")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


def main() -> None:
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception:
        logger.exception("Fatal error")
        sys.exit(1)


if __name__ == "__main__":
    main()
