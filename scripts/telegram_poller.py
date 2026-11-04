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


def _is_poller_host() -> bool:
    return os.getenv("PES_DATA_POLLER") == "1" or os.getenv("AMVERA") == "1"


def _bootstrap_env() -> None:
    """Amvera: UI-переменные + файл из «Подгрузить .env» (/data/.env)."""
    os.environ.setdefault("PES_DATA_POLLER", "1")
    # В репозитории / платформе иногда попадает dev DATABASE_URL=sqlite — сбросить
    if "sqlite" in (os.getenv("DATABASE_URL") or "").lower():
        os.environ.pop("DATABASE_URL", None)

    for data_env in (
        Path("/data/.env"),
        Path("/data/env"),
        Path("/data/amvera.env"),
    ):
        if data_env.is_file():
            load_dotenv(data_env, override=True)
            _load_env_file(data_env, override=True)
    if not (os.getenv("BOT_TOKEN") or "").strip():
        _load_env_file(ROOT / "amvera.env", override=True)

    load_dotenv(ROOT / ".env.migrate", override=False)

    # Локальный .env с sqlite никогда не подмешиваем в poller (Amvera / Mac backup)
    if not _is_poller_host():
        load_dotenv(ROOT / ".env", override=False)

    if not os.getenv("DATABASE_URL") and os.getenv("TARGET_DATABASE_URL"):
        os.environ["DATABASE_URL"] = os.getenv("TARGET_DATABASE_URL", "")


def _require_env() -> None:
    missing = [k for k in ("BOT_TOKEN", "DATABASE_URL") if not (os.getenv(k) or "").strip()]
    if missing:
        hint = (
            "Amvera: (1) Репозиторий → папка Data → загрузить файл .env (2 строки BOT_TOKEN, DATABASE_URL), "
            "или (2) Переменные → отдельно BOT_TOKEN и DATABASE_URL → Перезапустить"
        )
        print(f"Не задано: {', '.join(missing)}. {hint}", file=sys.stderr)
        if os.getenv("AMVERA"):
            data_paths = ["/data/.env", "/data/env", "/data/amvera.env"]
            exists = {p: Path(p).is_file() for p in data_paths}
            print(
                f"Диагностика: AMVERA={os.getenv('AMVERA')!r}, data files={exists}",
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

from urllib.parse import urlparse

from sqlalchemy import text

from database.database import engine, init_db
from bot.polling_runner import run_telegram_polling
from utils.logger import setup_logging, get_logger


async def verify_db_connectivity(logger) -> bool:
    db_url = os.environ.get("DATABASE_URL", "")
    host = urlparse(db_url).hostname or "?"
    port = urlparse(db_url).port or 5432
    connect_timeout = int(os.getenv("DATABASE_CONNECT_TIMEOUT", "45"))
    try:
        async with asyncio.timeout(connect_timeout + 15):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        logger.info("Telegram poller: DB ping ok (host=%s port=%s)", host, port)
        return True
    except Exception as exc:
        logger.error(
            "Telegram poller: DB ping FAILED host=%s port=%s — %s. "
            "Проверьте DATABASE_URL на Amvera (пароль: ! → %%21), sslmode=require; "
            "ONREZA /health db_ready=true — та же строка должна работать отсюда.",
            host,
            port,
            exc,
        )
        return False


def _log_database_target(logger) -> None:
    db_url = os.environ.get("DATABASE_URL", "")
    safe = db_url.replace("postgresql+asyncpg://", "postgresql://")
    parsed = urlparse(safe)
    db_name = (parsed.path or "").lstrip("/") or "?"
    logger.info(
        "Telegram poller: DATABASE_URL → host=%s port=%s db=%s user=%s",
        parsed.hostname or "?",
        parsed.port or 5432,
        db_name,
        parsed.username or "?",
    )


async def main() -> None:
    setup_logging()
    logger = get_logger(__name__)
    _log_database_target(logger)
    db_ok = await verify_db_connectivity(logger)
    if os.getenv("SKIP_INIT_DB") == "1":
        logger.info("Telegram poller: skip init_db (SKIP_INIT_DB=1)")
    elif db_ok:
        try:
            await asyncio.wait_for(init_db(), timeout=180.0)
            logger.info("Telegram poller: DB schema ready")
        except asyncio.TimeoutError:
            logger.error("Telegram poller: init_db timed out (schema/migrations)")
        except Exception:
            logger.exception("Telegram poller: init_db failed")
    else:
        logger.warning(
            "Telegram poller: polling starts without DB — кнопки с базой будут падать до исправления DATABASE_URL"
        )
    if db_ok:
        from services.admin_notify_service import ensure_admin_notify_config

        try:
            await ensure_admin_notify_config()
        except Exception:
            logger.exception("ensure_admin_notify_config failed (non-fatal)")
    logger.info("Telegram poller: starting polling…")
    await run_telegram_polling()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
