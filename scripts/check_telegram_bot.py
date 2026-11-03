#!/usr/bin/env python3
"""Быстрая диагностика: токен, webhook, нужен ли poller на Amvera."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _api(method: str, *, query: str = "") -> dict:
    token = (os.getenv("BOT_TOKEN") or "").strip()
    if not token:
        print("BOT_TOKEN не задан (локально .env или Amvera → Переменные)", file=sys.stderr)
        raise SystemExit(2)
    url = f"https://api.telegram.org/bot{token}/{method}{query}"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        print(f"{method} HTTP {exc.code}: {body[:300]}", file=sys.stderr)
        raise SystemExit(1) from exc


def main() -> None:
    me = _api("getMe")
    wh = _api("getWebhookInfo")
    info = wh.get("result") or {}
    username = (me.get("result") or {}).get("username", "?")
    url = (info.get("url") or "").strip()
    pending = info.get("pending_update_count", 0)

    print(f"Бот: @{username}")
    print(f"Webhook URL: {url or '(пусто — нужен long polling)'}")
    print(f"Очередь Telegram (pending): {pending}")

    if url:
        print(
            "\n⚠️  Включён webhook — сообщения идут на URL, а не в poller.",
            "Снимите webhook: python scripts/delete_telegram_webhook.py",
            sep="\n",
        )
        raise SystemExit(1)

    print(
        "\n✓ Режим polling. Должен работать процесс scripts/telegram_poller.py",
        "  (Amvera по amvera.yml или Mac/VPS). ONREZA с TELEGRAM_BOT_DISABLED=1 бота не крутит.",
        sep="\n",
    )
    print(
        "\nПроверка Amvera: Логи → «Telegram long polling started».",
        "Если приложения Amvera нет — создайте по docs/AMVERA_BOT.md.",
        sep="\n",
    )


if __name__ == "__main__":
    main()
