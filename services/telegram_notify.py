from __future__ import annotations

import html
from dataclasses import dataclass

import aiohttp

from config.settings import settings
from database.models import DeliveryType
from utils.logger import get_logger

logger = get_logger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


@dataclass
class DeliveryNotifyResult:
    ok: bool
    message_sent: bool
    contacts_sent: int
    error: str | None = None


async def _telegram_post(method: str, **kwargs) -> tuple[bool, str]:
    if not settings.bot_token:
        return False, "BOT_TOKEN не задан"

    url = TELEGRAM_API.format(token=settings.bot_token, method=method)
    timeout = aiohttp.ClientTimeout(total=15)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, **kwargs) as resp:
                body = await resp.text()
                if resp.status == 200:
                    await _log_telegram_outgoing(method, kwargs)
                    return True, body
                logger.error("Telegram %s failed: %s %s", method, resp.status, body)
                return False, body
    except Exception as exc:
        logger.exception("Telegram %s request error", method)
        return False, str(exc)


async def _log_telegram_outgoing(method: str, kwargs: dict) -> None:
    payload = kwargs.get("json") or {}
    chat_id = payload.get("chat_id")
    text = payload.get("text") or payload.get("caption")
    if method == "sendDocument" and not text:
        text = "[документ с контактами]"
    if not chat_id or not text:
        return
    try:
        from database.database import async_session
        from services.chat_log_service import log_outgoing

        async with async_session() as session:
            await log_outgoing(
                session,
                telegram_id=int(chat_id),
                content=text,
                message_type="document" if method == "sendDocument" else "text",
                source=f"telegram_notify.{method}",
            )
    except Exception:
        logger.exception("Failed to log telegram_notify outgoing chat_id=%s", chat_id)


async def notify_payment_success(telegram_id: int, contact_limit: int) -> bool:
    from services.order_service import payment_success_text
    from services.project_service import PROJECT_NAME_PROMPT

    text = payment_success_text(contact_limit)
    text += f"\n\n{PROJECT_NAME_PROMPT}"
    ok, _ = await _telegram_post(
        "sendMessage",
        json={
            "chat_id": telegram_id,
            "text": text,
            "parse_mode": "HTML",
        },
    )
    return ok


def _format_stats_block(sent_today: int, received: int, limit: int, remaining: int) -> str:
    return (
        "🐶 <b>Новые контакты готовы!</b>\n\n"
        f"Сегодня добавлено:\n\n"
        f"{sent_today} контактов\n\n"
        f"📥 Получено всего:\n\n"
        f"{received} / {limit}\n\n"
        f"📤 Осталось получить:\n\n"
        f"{remaining}"
    )


def _format_phone_lines(phones: list[str]) -> str:
    return "\n\n".join(html.escape(p.lstrip("+")) for p in phones)


async def deliver_contacts_to_user(
    telegram_id: int,
    phones: list[str],
    received: int,
    limit: int,
    remaining: int,
    *,
    delivery_type: str = DeliveryType.MESSAGE.value,
    file_name: str | None = None,
    file_data: bytes | None = None,
) -> DeliveryNotifyResult:
    if not telegram_id:
        return DeliveryNotifyResult(False, False, 0, "Telegram ID пользователя не найден")
    if not phones:
        return DeliveryNotifyResult(False, False, 0, "Список контактов пуст")

    sent_today = len(phones)
    stats = _format_stats_block(sent_today, received, limit, remaining)

    if delivery_type == DeliveryType.FILE.value and file_data:
        text = stats + "\n\nКонтакты прикреплены к этому сообщению."
        form = aiohttp.FormData()
        form.add_field("chat_id", str(telegram_id))
        form.add_field("caption", text)
        form.add_field("parse_mode", "HTML")
        form.add_field(
            "document",
            file_data,
            filename=file_name or "contacts.txt",
            content_type="application/octet-stream",
        )
        ok, err = await _telegram_post("sendDocument", data=form)
        if ok:
            try:
                from database.database import async_session
                from services.chat_log_service import log_outgoing

                async with async_session() as session:
                    await log_outgoing(
                        session,
                        telegram_id=telegram_id,
                        content=text,
                        message_type="document",
                        source="telegram_notify.sendDocument",
                    )
            except Exception:
                logger.exception("Failed to log sendDocument chat_id=%s", telegram_id)
            return DeliveryNotifyResult(True, True, sent_today)
        return DeliveryNotifyResult(False, False, 0, err[:300])

    phone_block = _format_phone_lines(phones)
    text = stats + "\n\nВаши новые контакты:\n\n" + phone_block

    if len(text) <= 4000:
        ok, err = await _telegram_post(
            "sendMessage",
            json={"chat_id": telegram_id, "text": text, "parse_mode": "HTML"},
        )
        if ok:
            return DeliveryNotifyResult(True, True, sent_today)
        return DeliveryNotifyResult(False, False, 0, err[:300])

    ok_header, err = await _telegram_post(
        "sendMessage",
        json={"chat_id": telegram_id, "text": stats, "parse_mode": "HTML"},
    )
    if not ok_header:
        return DeliveryNotifyResult(False, False, 0, err[:300])

    chunks = [phones[i : i + 40] for i in range(0, len(phones), 40)]
    sent = 0
    errors: list[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        chunk_text = f"📋 <b>Контакты ({idx}/{len(chunks)}):</b>\n\n{_format_phone_lines(chunk)}"
        ok, chunk_err = await _telegram_post(
            "sendMessage",
            json={"chat_id": telegram_id, "text": chunk_text, "parse_mode": "HTML"},
        )
        if ok:
            sent += len(chunk)
        else:
            errors.append(chunk_err[:120])

    if sent > 0:
        return DeliveryNotifyResult(
            True,
            True,
            sent,
            "; ".join(errors) if errors else None,
        )
    return DeliveryNotifyResult(False, True, 0, "; ".join(errors) if errors else "Ошибка отправки")


async def notify_package_completed(telegram_id: int) -> bool:
    text = (
        "🎉 <b>Ваш пакет полностью выполнен!</b>\n\n"
        "Вы получили все оплаченные контакты.\n\n"
        "Спасибо за использование сервиса «Пёс Дата».\n\n"
        "Для продолжения работы вы можете приобрести новый пакет."
    )
    reply_markup = {
        "inline_keyboard": [
            [{"text": "💰 Купить новый пакет", "callback_data": "buy_package"}]
        ]
    }
    ok, _ = await _telegram_post(
        "sendMessage",
        json={
            "chat_id": telegram_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": reply_markup,
        },
    )
    return ok
