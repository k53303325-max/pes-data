from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from database.database import async_session
from services.chat_log_service import log_incoming, log_outgoing
from utils.logger import get_logger

logger = get_logger(__name__)

OUTGOING_METHODS = {
    "SendMessage",
    "EditMessageText",
    "SendDocument",
    "AnswerCallbackQuery",
}


def _extract_incoming(event: TelegramObject) -> tuple[int, str, str, str | None, int | None] | None:
    if isinstance(event, Message):
        user = event.from_user
        if not user:
            return None
        if event.text:
            msg_type = "command" if event.text.startswith("/") else "text"
            return user.id, event.text, msg_type, "message", event.message_id
        if event.caption:
            return user.id, event.caption, "caption", "message", event.message_id
        if event.contact:
            return user.id, f"[контакт] {event.contact.phone_number}", "contact", "message", event.message_id
        if event.document:
            name = event.document.file_name or "файл"
            return user.id, f"[документ] {name}", "document", "message", event.message_id
        if event.photo:
            return user.id, "[фото]", "photo", "message", event.message_id
        return user.id, "[сообщение без текста]", "other", "message", event.message_id

    if isinstance(event, CallbackQuery):
        user = event.from_user
        if not user:
            return None
        label = event.message.text[:80] if event.message and event.message.text else "кнопка"
        content = f"[кнопка] {event.data}\n↳ {label}"
        return user.id, content, "callback", "callback_query", event.message.message_id if event.message else None

    return None


class ChatLogMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        parsed = _extract_incoming(event)
        if parsed:
            telegram_id, content, msg_type, source, tg_msg_id = parsed
            try:
                async with async_session() as session:
                    await log_incoming(
                        session,
                        telegram_id=telegram_id,
                        content=content,
                        message_type=msg_type,
                        source=source,
                        telegram_message_id=tg_msg_id,
                    )
            except Exception:
                logger.exception("Failed to log incoming chat telegram_id=%s", telegram_id)
        return await handler(event, data)


class OutgoingChatLogMiddleware(BaseRequestMiddleware):
    async def __call__(self, make_request, bot, method):
        response = await make_request(bot, method)
        method_name = type(method).__name__
        if method_name not in OUTGOING_METHODS:
            return response

        chat_id = getattr(method, "chat_id", None)
        text = getattr(method, "text", None) or getattr(method, "caption", None)
        if method_name == "AnswerCallbackQuery":
            return response

        if not chat_id or not text:
            return response

        try:
            async with async_session() as session:
                await log_outgoing(
                    session,
                    telegram_id=int(chat_id),
                    content=text,
                    message_type="text" if method_name != "SendDocument" else "document",
                    source=method_name,
                )
        except Exception:
            logger.exception("Failed to log outgoing chat chat_id=%s", chat_id)
        return response
