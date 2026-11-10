#!/usr/bin/env python3
"""Поставить в outbox уведомление по уже созданной delivery (без повторного списания лимита)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env.migrate", override=False)

from database.database import async_session
from services.delivery_requeue import requeue_delivery_telegram


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: requeue_delivery_notify.py <delivery_id> [delivery_id ...]", file=sys.stderr)
        raise SystemExit(2)
    ids = [int(x) for x in sys.argv[1:]]
    async with async_session() as session:
        for did in ids:
            ok = await requeue_delivery_telegram(session, did)
            print(f"delivery {did}: {'queued' if ok else 'skip'}")


if __name__ == "__main__":
    asyncio.run(main())
