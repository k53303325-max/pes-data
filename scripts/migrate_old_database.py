#!/usr/bin/env python3
"""
Перенос данных из старой Postgres (Neon) в новую (ONREZA).

Использование:
  export SOURCE_DATABASE_URL='postgresql://...neon...'   # старая база
  export TARGET_DATABASE_URL='postgresql://...onreza...'  # новая база
  ./venv/bin/python scripts/migrate_old_database.py

Или положите SOURCE в .env.vercel.prod, TARGET — в .env.migrate (не коммитьте).
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
load_dotenv(ROOT / ".env.vercel.prod")
load_dotenv(ROOT / ".env.migrate")

from urllib.parse import urlparse, urlunparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def normalize_url(url: str) -> tuple[str, bool]:
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    use_ssl = (
        "neon.tech" in host
        or "kaiki.ru" in host
        or "sslmode=require" in (parsed.query or "").lower()
    )
    clean = urlunparse(parsed._replace(query=""))
    return clean, use_ssl


def make_engine(url: str):
    clean, use_ssl = normalize_url(url)
    connect_args = {"ssl": True} if use_ssl else {}
    return create_async_engine(clean, connect_args=connect_args)


TABLES_AFTER_USERS = [
    "orders",
    "payments",
    "projects",
    "niche_brief_requests",
    "trial_entitlements",
    "competitor_numbers",
    "deliveries",
    "delivered_contacts",
    "client_activity_log",
    "bot_messages",
    "bank_payment_requests",
    "referral_commissions",
    "fsm_storage",
]


async def table_columns(session: AsyncSession, table: str) -> list[str]:
    r = await session.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :t ORDER BY ordinal_position"
        ),
        {"t": table},
    )
    return [row[0] for row in r.fetchall()]


async def copy_users(src: AsyncSession, dst: AsyncSession) -> dict[int, int]:
    """old_user_id -> new_user_id (по telegram_id без дублей)."""
    cols = await table_columns(src, "users")
    rows = (await src.execute(text(f"SELECT {', '.join(cols)} FROM users ORDER BY id"))).mappings().all()
    id_map: dict[int, int] = {}
    for row in rows:
        data = dict(row)
        old_id = data.pop("id")
        tg = data["telegram_id"]
        existing = await dst.execute(
            text("SELECT id FROM users WHERE telegram_id = :tg"),
            {"tg": tg},
        )
        hit = existing.scalar_one_or_none()
        if hit:
            id_map[old_id] = hit
            continue
        ref_old = data.get("referred_by_user_id")
        if ref_old is not None and ref_old in id_map:
            data["referred_by_user_id"] = id_map[ref_old]
        elif ref_old is not None:
            data["referred_by_user_id"] = None
        placeholders = ", ".join(f":{c}" for c in data)
        names = ", ".join(data)
        res = await dst.execute(
            text(f"INSERT INTO users ({names}) VALUES ({placeholders}) RETURNING id"),
            data,
        )
        new_id = res.scalar_one()
        id_map[old_id] = new_id
    # второй проход: referred_by для тех, кто ссылался на ещё не перенесённых
    for row in rows:
        old_id = row["id"]
        ref_old = row.get("referred_by_user_id")
        if ref_old and ref_old in id_map and id_map.get(old_id):
            await dst.execute(
                text("UPDATE users SET referred_by_user_id = :ref WHERE id = :id"),
                {"ref": id_map[ref_old], "id": id_map[old_id]},
            )
    await dst.commit()
    return id_map


def remap_fk(row: dict, id_map: dict[int, int], *fields: str) -> dict:
    out = dict(row)
    for f in fields:
        if out.get(f) is not None and out[f] in id_map:
            out[f] = id_map[out[f]]
    return out


async def copy_table(
    src: AsyncSession,
    dst: AsyncSession,
    table: str,
    id_map: dict[int, int],
    *,
    user_fields: tuple[str, ...] = ("user_id",),
    skip_id: bool = True,
) -> int:
    cols = await table_columns(src, table)
    if not cols:
        return 0
    rows = (await src.execute(text(f"SELECT {', '.join(cols)} FROM {table} ORDER BY id"))).mappings().all()
    count = 0
    for row in rows:
        data = dict(row)
        if skip_id:
            data.pop("id", None)
        for uf in user_fields:
            if data.get(uf) is not None and data[uf] not in id_map:
                continue
        data = remap_fk(data, id_map, *user_fields)
        if "partner_user_id" in data:
            data = remap_fk(data, id_map, "partner_user_id", "referee_user_id")
        if "order_id" in data and data.get("order_id") is not None:
            # order ids copied in same order if we preserve - handle below
            pass
        try:
            names = ", ".join(data)
            placeholders = ", ".join(f":{k}" for k in data)
            await dst.execute(text(f"INSERT INTO {table} ({names}) VALUES ({placeholders})"), data)
            count += 1
        except Exception:
            continue
    await dst.commit()
    return count


async def copy_simple(src: AsyncSession, dst: AsyncSession, table: str, id_map: dict[int, int]) -> int:
    cols = await table_columns(src, table)
    if not cols:
        return 0
    rows = (await src.execute(text(f"SELECT {', '.join(cols)} FROM {table}"))).mappings().all()
    order_map: dict[int, int] = {}
    payment_map: dict[int, int] = {}
    project_map: dict[int, int] = {}
    n = 0
    for row in rows:
        data = dict(row)
        old_pk = data.pop("id", None)
        skip = False
        for key in ("user_id", "partner_user_id", "referee_user_id"):
            if data.get(key) is not None:
                if data[key] not in id_map:
                    skip = True
                    break
                data[key] = id_map[data[key]]
        if skip:
            continue
        if "order_id" in data and data.get("order_id") is not None:
            if data["order_id"] not in order_map:
                continue
            data["order_id"] = order_map[data["order_id"]]
        if "payment_id" in data and data.get("payment_id") is not None:
            if data["payment_id"] not in payment_map:
                continue
            data["payment_id"] = payment_map[data["payment_id"]]
        if "project_id" in data and data.get("project_id") is not None:
            if data["project_id"] not in project_map:
                continue
            data["project_id"] = project_map[data["project_id"]]
        names = ", ".join(data)
        ph = ", ".join(f":{k}" for k in data)
        try:
            res = await dst.execute(
                text(f"INSERT INTO {table} ({names}) VALUES ({ph}) RETURNING id"),
                data,
            )
            new_id = res.scalar_one()
            n += 1
            if old_pk is not None:
                if table == "orders":
                    order_map[old_pk] = new_id
                elif table == "payments":
                    payment_map[old_pk] = new_id
                elif table == "projects":
                    project_map[old_pk] = new_id
        except Exception:
            await dst.rollback()
            continue
    await dst.commit()
    return n


async def main() -> int:
    source = os.getenv("SOURCE_DATABASE_URL") or os.getenv("POSTGRES_URL_NON_POOLING")
    target = os.getenv("TARGET_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not source or not target:
        print("Задайте SOURCE_DATABASE_URL (Neon) и TARGET_DATABASE_URL (ONREZA)", file=sys.stderr)
        return 1
    if normalize_url(source)[0] == normalize_url(target)[0]:
        print("SOURCE и TARGET совпадают — миграция не нужна", file=sys.stderr)
        return 1

    print("Инициализация схемы в новой базе…")
    from database.models import Base, Tariff

    dst_engine = make_engine(target)
    async with dst_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    DstSeed = async_sessionmaker(dst_engine, class_=AsyncSession, expire_on_commit=False)
    async with DstSeed() as session:
        seeds = (
            (1, "📦", "Мини", 5000, 50),
            (2, "🚀", "Старт", 9000, 100),
            (3, "📈", "Рост", 20000, 250),
            (4, "🏢", "Бизнес", 35000, 500),
            (5, "🐺", "Масштаб", 60000, 1000),
        )
        for tid, emoji, name, price, limit in seeds:
            if await session.get(Tariff, tid) is None:
                session.add(
                    Tariff(
                        id=tid,
                        emoji=emoji,
                        name=name,
                        price=price,
                        contact_limit=limit,
                        sort_order=tid,
                        is_active=True,
                    )
                )
        await session.commit()

    src_engine = make_engine(source)
    Src = async_sessionmaker(src_engine, class_=AsyncSession, expire_on_commit=False)
    Dst = async_sessionmaker(dst_engine, class_=AsyncSession, expire_on_commit=False)

    async with Src() as src, Dst() as dst:
        n_users = (await src.execute(text("SELECT COUNT(*) FROM users"))).scalar() or 0
        print(f"В старой базе пользователей: {n_users}")
        id_map = await copy_users(src, dst)
        print(f"Сопоставлено пользователей: {len(id_map)}")
        for table in ["orders", "payments", "projects", "niche_brief_requests", "bot_messages"]:
            c = await copy_simple(src, dst, table, id_map)
            print(f"  {table}: +{c}")

    await src_engine.dispose()
    await dst_engine.dispose()
    print("Готово. В ONREZA в DATABASE_URL должен быть TARGET — перезапуск не нужен, если уже он.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
