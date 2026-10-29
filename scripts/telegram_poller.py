#!/usr/bin/env python3
"""Отдельный процесс: long polling (админка может жить на ONREZA без бота)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import os

from dotenv import load_dotenv


def _bootstrap_env() -> None:
    """Amvera: UI-переменные + файл из «Подгрузить .env» (/data/.env)."""
    for path in (
        Path("/data/.env"),
        ROOT / ".env",
        ROOT / ".env.migrate",
    ):
        if path.is_file():
            load_dotenv(path, override=False)

    if not os.getenv("DATABASE_URL") and os.getenv("TARGET_DATABASE_URL"):
        os.environ["DATABASE_URL"] = os.getenv("TARGET_DATABASE_URL", "")


def _require_env() -> None:
    missing = [k for k in ("BOT_TOKEN", "DATABASE_URL") if not (os.getenv(k) or "").strip()]
    if missing:
        hint = (
            "Amvera: Переменные → BOT_TOKEN и DATABASE_URL (этап «Запуск»), "
            "затем Управление → Перезапустить. Или «Подгрузить .env» в /data/.env"
        )
        print(f"Не задано: {', '.join(missing)}. {hint}", file=sys.stderr)
        if os.getenv("AMVERA"):
            print(
                f"Диагностика: AMVERA={os.getenv('AMVERA')!r}, "
                f"/data/.env exists={Path('/data/.env').is_file()}",
                file=sys.stderr,
            )
        raise SystemExit(2)


_bootstrap_env()
_require_env()

from database.database import init_db
from bot.polling_runner import run_telegram_polling
from utils.logger import setup_logging, get_logger


async def main() -> None:
    setup_logging()
    logger = get_logger(__name__)
    await init_db()
    logger.info("Telegram poller: DB ready, starting polling…")
    await run_telegram_polling()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
