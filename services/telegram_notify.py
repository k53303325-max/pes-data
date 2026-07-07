from __future__ import annotations

import aiohttp

from config.settings import settings


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
