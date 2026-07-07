from __future__ import annotations

import aiohttp

from config.settings import settings


async def notify_payment_success(
    telegram_id: int,
    tariff_name: str,
    contact_limit: int,
) -> bool:
    if not settings.bot_token:
        return False
    text = (
        "✅ <b>Оплата прошла успешно!</b>\n\n"
        f"Пакет «{tariff_name}» активирован.\n"
        f"Лимит: {contact_limit:,} контактов.\n\n".replace(",", " ")
        + "Скоро вы сможете добавлять номера конкурентов."
    )
    url = f"https://api.telegram.org/bot{settings.bot_token}/sendMessage"
    payload = {"chat_id": telegram_id, "text": text, "parse_mode": "HTML"}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            return resp.status == 200


async def notify_new_contacts(
    telegram_id: int,
    count: int,
    received: int,
    limit: int,
    remaining: int,
) -> bool:
    if not settings.bot_token:
        return False
    text = (
        "🐶 <b>Пёс Дата</b>\n\n"
        "Новые контакты готовы!\n\n"
        f"Сегодня отправлено:\n{count} контактов\n\n"
        f"Всего получено:\n{received}/{limit}\n\n"
        f"Осталось:\n{remaining}"
    )
    url = f"https://api.telegram.org/bot{settings.bot_token}/sendMessage"
    payload = {
        "chat_id": telegram_id,
        "text": text,
        "parse_mode": "HTML",
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            return resp.status == 200
