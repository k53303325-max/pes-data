#!/usr/bin/env python3
"""Отдельный процесс: long polling (админка может жить на ONREZA без бота)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
load_dotenv(ROOT / ".env.migrate")

import os

if not os.getenv("DATABASE_URL") and os.getenv("TARGET_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.getenv("TARGET_DATABASE_URL", "")

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
