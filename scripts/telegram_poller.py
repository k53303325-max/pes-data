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


def _load_env_file(path: Path, *, override: bool) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key or not value:
            continue
        if override or not (os.getenv(key) or "").strip():
            os.environ[key] = value


def _bootstrap_env() -> None:
    """Amvera: UI-переменные + файл из «Подгрузить .env» (/data/.env)."""
    os.environ.setdefault("PES_DATA_POLLER", "1")
    os.environ.setdefault("SKIP_INIT_DB", "1")
    # В репозитории на Amvera иногда лежит dev-.env с sqlite — не использовать
    if "sqlite" in (os.getenv("DATABASE_URL") or "").lower():
        os.environ.pop("DATABASE_URL", None)
    _load_env_file(Path("/data/.env"), override=True)
    load_dotenv(ROOT / ".env.migrate", override=False)
    if "sqlite" not in (os.getenv("DATABASE_URL") or "").lower():
        load_dotenv(ROOT / ".env", override=False)

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

    db_url = os.environ["DATABASE_URL"].strip()
    if not db_url.startswith(("postgres://", "postgresql://")):
        print(
            f"DATABASE_URL должен быть postgresql://… (сейчас: {db_url[:40]}…)",
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
    if os.getenv("SKIP_INIT_DB") == "1":
        logger.info("Telegram poller: skip init_db (schema already on Postgres)")
    else:
        await init_db()
        logger.info("Telegram poller: DB ready")
    logger.info("Telegram poller: starting polling…")
    await run_telegram_polling()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
