from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InaccessibleMessage, InlineKeyboardMarkup, Message

from utils.logger import get_logger

logger = get_logger(__name__)


async def safe_callback_answer(
    callback: CallbackQuery,
    text: str | None = None,
    *,
    show_alert: bool = False,
) -> None:
    try:
        await callback.answer(text, show_alert=show_alert)
    except TelegramBadRequest as exc:
        logger.debug("callback.answer ignored: %s", exc)
    except Exception:
        logger.exception("callback.answer failed")


async def safe_edit_or_send(
    message: Message | None,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    if message is None:
        return
    try:
        await message.edit_text(text, reply_markup=reply_markup)
        return
    except TelegramBadRequest as exc:
        err = str(exc).lower()
        if "message is not modified" in err:
            return
        if "there is no text" in err or "can't be edited" in err or "message to edit not found" in err:
            logger.info("edit_text fallback to answer: %s", exc)
            await message.answer(text, reply_markup=reply_markup)
            return
        raise


async def respond_to_callback(
    callback: CallbackQuery,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
    answer_text: str | None = None,
    show_alert: bool = False,
) -> None:
    """Ответ на inline-кнопку: ack + edit или новое сообщение в чат."""
    if answer_text is not None or show_alert:
        await safe_callback_answer(callback, answer_text, show_alert=show_alert)
    else:
        await safe_callback_answer(callback)

    msg = callback.message
    if isinstance(msg, Message):
        try:
            await msg.edit_text(text, reply_markup=reply_markup)
            return
        except TelegramBadRequest as exc:
            err = str(exc).lower()
            if "message is not modified" in err:
                return
            logger.info("callback edit_text failed, sending new message: %s", exc)
        except AttributeError:
            pass

    if isinstance(msg, InaccessibleMessage) or msg is None:
        logger.info("callback message inaccessible, send_message user_id=%s", callback.from_user.id)

    await callback.bot.send_message(
        callback.from_user.id,
        text,
        reply_markup=reply_markup,
    )
