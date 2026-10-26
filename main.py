from __future__ import annotations

import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, ErrorEvent

from config.settings import settings
from services.messages import BOT_SYSTEM_ERROR_ALERT, BOT_SYSTEM_ERROR_TEXT
from database.database import init_db
from handlers import competitors, orders, payments, profile, start, tariffs
from utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


async def errors_handler(event: ErrorEvent) -> None:
    logger.exception("Unhandled error", exc_info=event.exception)
    user_label = "—"
    try:
        if event.update.message and event.update.message.from_user:
            user_label = str(event.update.message.from_user.id)
        elif event.update.callback_query and event.update.callback_query.from_user:
            user_label = str(event.update.callback_query.from_user.id)
    except Exception:
        pass
    try:
        from services.admin_notify_service import notify_admin_error

        await notify_admin_error(
            event="bot_handler",
            user_label=user_label,
            error_message=str(event.exception),
        )
    except Exception:
        pass
    update = event.update
    try:
        if update.message:
            await update.message.answer(BOT_SYSTEM_ERROR_TEXT)
        elif update.callback_query:
            await update.callback_query.answer(BOT_SYSTEM_ERROR_ALERT, show_alert=True)
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
    dp.include_router(tariffs.router)
    dp.include_router(orders.router)
    dp.include_router(payments.router)
    dp.include_router(profile.router)
    dp.include_router(competitors.router)

    me = await bot.get_me()
    logger.info("Bot connected: @%s", me.username)

    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="profile", description="Мой пакет"),
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
