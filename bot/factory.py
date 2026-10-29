from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.postgres_storage import PostgresStorage
from aiogram.types import BotCommand, ErrorEvent

from bot.chat_log_middleware import ChatLogMiddleware, OutgoingChatLogMiddleware

from config.settings import settings
from services.messages import BOT_SYSTEM_ERROR_ALERT, BOT_SYSTEM_ERROR_TEXT
from utils.logger import get_logger

logger = get_logger(__name__)

_bot: Bot | None = None
_dp: Dispatcher | None = None
_webhook_ready = False


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        session = AiohttpSession(timeout=30)
        session.middleware(OutgoingChatLogMiddleware())
        _bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
            session=session,
        )
    return _bot


def get_dispatcher() -> Dispatcher:
    global _dp
    if _dp is None:
        from handlers import (
            bank_invoice,
            brief,
            competitors,
            faq,
            fsm_fallback,
            menu,
            orders,
            package_payment,
            packages,
            payments,
            profile,
            project,
            referral,
            start,
            tariffs,
        )

        storage = PostgresStorage() if settings.database_url.startswith("postgresql") else MemoryStorage()
        _dp = Dispatcher(storage=storage)

        async def errors_handler(event: ErrorEvent) -> None:
            logger.exception("Bot error", exc_info=event.exception)
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
            try:
                if event.update.message:
                    await event.update.message.answer(BOT_SYSTEM_ERROR_TEXT)
                elif event.update.callback_query:
                    await event.update.callback_query.answer(
                        BOT_SYSTEM_ERROR_ALERT,
                        show_alert=True,
                    )
            except Exception:
                pass

        _dp.errors.register(errors_handler)
        chat_log = ChatLogMiddleware()
        _dp.message.middleware(chat_log)
        _dp.callback_query.middleware(chat_log)
        _dp.include_router(start.router)
        _dp.include_router(menu.router)
        _dp.include_router(referral.router)
        _dp.include_router(packages.router)
        _dp.include_router(package_payment.router)
        _dp.include_router(bank_invoice.router)
        _dp.include_router(faq.router)
        _dp.include_router(tariffs.router)
        _dp.include_router(orders.router)
        _dp.include_router(payments.router)
        _dp.include_router(profile.router)
        _dp.include_router(project.router)
        _dp.include_router(competitors.router)
        _dp.include_router(brief.router)
        _dp.include_router(fsm_fallback.router)
    return _dp


async def ensure_telegram_webhook() -> None:
    global _webhook_ready
    if _webhook_ready or not settings.use_webhook or not settings.telegram_bot_enabled:
        return

    app_url = (settings.app_url or "").rstrip("/")
    if app_url.startswith("http://127.0.0.1") or app_url.startswith("http://localhost"):
        logger.error(
            "APP_URL не задан для webhook (сейчас %s). Задайте публичный URL в ONREZA env.",
            app_url,
        )
        return

    bot = get_bot()
    webhook_url = f"{app_url}/webhook/telegram"
    try:
        info = await asyncio.wait_for(bot.get_webhook_info(), timeout=10.0)
        if info.url != webhook_url:
            await asyncio.wait_for(
                bot.set_webhook(webhook_url, drop_pending_updates=False),
                timeout=10.0,
            )
            logger.info("Telegram webhook set: %s", webhook_url)
    except Exception:
        logger.exception("Telegram webhook sync failed (set URL manually if needed)")

    _webhook_ready = True

    try:
        await asyncio.wait_for(
            bot.set_my_commands([
                BotCommand(command="start", description="Главное меню"),
                BotCommand(command="profile", description="Мой пакет"),
            ]),
            timeout=8.0,
        )
        await asyncio.wait_for(
            bot.set_my_short_description(
                "Контакты для телефонных продаж. Проверьте нишу: бизнес → конкуренты → подбор."
            ),
            timeout=8.0,
        )
        await asyncio.wait_for(
            bot.set_my_description(
                "Пёс Дата помогает бизнесу проверить дополнительный источник контактов "
                "для телефонных продаж.\n\n"
                "Здесь можно узнать, как работает сервис, посмотреть пакеты и отправить "
                "вводные для проверки своей ниши.\n\n"
                "Контакт — это номер потенциального клиента. Его потребность и готовность "
                "покупать проверяет ваш отдел продаж."
            ),
            timeout=8.0,
        )
    except Exception:
        logger.exception("Failed to set bot profile text (non-fatal)")
