#!/usr/bin/env python3
"""Проверка доступности Postgres (тот же DATABASE_URL, что на Amvera/poller)."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env.migrate", override=False)
load_dotenv(ROOT / ".env", override=False)

url = (os.getenv("DATABASE_URL") or os.getenv("TARGET_DATABASE_URL") or "").strip()
if not url:
    print("Задайте DATABASE_URL или TARGET_DATABASE_URL", file=sys.stderr)
    raise SystemExit(2)

if "sqlite" in url.lower():
    print("Сейчас DATABASE_URL указывает на sqlite — для Amvera нужен postgresql://…", file=sys.stderr)
    raise SystemExit(2)

if url.startswith("postgresql+asyncpg://"):
    url = "postgresql://" + url.split("://", 1)[1]

parsed = urlparse(url)
host = parsed.hostname or "?"
port = parsed.port or 5432
dbname = (parsed.path or "/").lstrip("/") or "?"
print(f"host={host} port={port} db={dbname} user={parsed.username or '?'}")


async def main() -> None:
    import asyncpg

    timeout = int(os.getenv("DATABASE_CONNECT_TIMEOUT", "45"))
    try:
        conn = await asyncio.wait_for(
            asyncpg.connect(dsn=url, timeout=timeout, ssl=True),
            timeout=timeout + 10,
        )
        val = await conn.fetchval("SELECT 1")
        await conn.close()
        print(f"OK: SELECT 1 -> {val}")
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    asyncio.run(main())
