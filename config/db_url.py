from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def resolve_database_url() -> str:
    """Vercel Postgres автоматически добавляет POSTGRES_URL."""
    for key in ("POSTGRES_URL", "DATABASE_URL", "POSTGRES_URL_NON_POOLING"):
        value = os.getenv(key)
        if value:
            return normalize_database_url(value)

    if os.getenv("VERCEL") == "1":
        return ""

    from pathlib import Path
    base = Path(__file__).resolve().parent.parent
    return f"sqlite+aiosqlite:///{base / 'pes_data.db'}"


def get_app_url() -> str:
    prod = os.getenv("VERCEL_PROJECT_PRODUCTION_URL")
    if prod:
        return f"https://{prod}"
    vercel_url = os.getenv("VERCEL_URL")
    if vercel_url:
        return f"https://{vercel_url}"
    return os.getenv("APP_URL", "http://127.0.0.1:8000")
