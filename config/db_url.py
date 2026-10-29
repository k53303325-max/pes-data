from __future__ import annotations

import os
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv

load_dotenv()


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    parsed = urlparse(url)
    if not parsed.query:
        return url

    # asyncpg не понимает libpq query-параметры — SSL задаём в connect_args
    return urlunparse(parsed._replace(query=""))


def _is_vercel() -> bool:
    return os.getenv("VERCEL") == "1"


def resolve_database_url() -> str:
    """Vercel serverless: NON_POOLING. ONREZA/обычный хостинг: DATABASE_URL."""
    if _is_vercel():
        keys = ("POSTGRES_URL_NON_POOLING", "DATABASE_URL", "POSTGRES_URL")
    else:
        keys = ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_URL_NON_POOLING")
    for key in keys:
        value = os.getenv(key)
        if value:
            return normalize_database_url(value)

    if _is_vercel() or os.getenv("AMVERA") == "1" or os.getenv("PES_DATA_POLLER") == "1":
        return ""

    from pathlib import Path
    base = Path(__file__).resolve().parent.parent
    return f"sqlite+aiosqlite:///{base / 'pes_data.db'}"


def get_app_url() -> str:
    explicit = (os.getenv("APP_URL") or "").strip().rstrip("/")
    if explicit:
        return explicit
    prod = os.getenv("VERCEL_PROJECT_PRODUCTION_URL")
    if prod:
        return f"https://{prod}"
    vercel_url = os.getenv("VERCEL_URL")
    if vercel_url:
        return f"https://{vercel_url}"
    onreza_url = (os.getenv("ONREZA_APP_URL") or os.getenv("NRZ_APP_URL") or "").strip().rstrip("/")
    if onreza_url:
        return onreza_url
    return "http://127.0.0.1:8000"


def resolve_yookassa_return_url() -> str:
    configured = os.getenv("YOOKASSA_RETURN_URL", "").strip()
    if configured and "your_bot" not in configured:
        return configured
    return "https://t.me/Pesdata_bot?start=payment_ok"
