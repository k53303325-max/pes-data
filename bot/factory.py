from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, ErrorEvent

from config.settings import settings
from handlers import payments, start
from utils.logger import get_logger

logger = get_logger(__name__)

_bot: Bot | None = None
_dp: Dispatcher | None = None
_webhook_ready = False


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
    return _bot


def get_dispatcher() -> Dispatcher:
    global _dp
    if _dp is None:
        _dp = Dispatcher(storage=MemoryStorage())

        async def errors_handler(event: ErrorEvent) -> None:
            logger.exception("Bot error", exc_info=event.exception)
            try:
                if event.update.message:
                    await event.update.message.answer("⚠️ Ошибка. Нажмите /start")
                elif event.update.callback_query:
                    await event.update.callback_query.answer("⚠️ Ошибка", show_alert=True)
            except Exception:
                pass

        _dp.errors.register(errors_handler)
        _dp.include_router(start.router)
        _dp.include_router(payments.router)
    return _dp


async def ensure_telegram_webhook() -> None:
    global _webhook_ready
    if _webhook_ready or not settings.is_vercel or not settings.bot_token:
        return

    bot = get_bot()
    webhook_url = f"{settings.app_url}/webhook/telegram"
    info = await bot.get_webhook_info()
    if info.url != webhook_url:
        await bot.set_webhook(webhook_url, drop_pending_updates=False)
        logger.info("Telegram webhook set: %s", webhook_url)

    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню"),
    ])
    _webhook_ready = True
