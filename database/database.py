from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from config.settings import settings
from database.models import Base, Tariff


def _postgres_connect_args(database_url: str) -> dict:
    args: dict = {"timeout": 15, "command_timeout": 30}
    host = (urlparse(database_url).hostname or "").lower()
    if "neon.tech" in host or "supabase.co" in host or "sslmode=require" in database_url.lower():
        args["ssl"] = True
    return args


connect_args: dict = {}
engine_kwargs: dict = {"echo": False}

if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif settings.database_url.startswith("postgresql"):
    connect_args = _postgres_connect_args(settings.database_url)
    if settings.is_vercel:
        engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(
    settings.database_url or "sqlite+aiosqlite:///:memory:",
    connect_args=connect_args,
    **engine_kwargs,
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

TARIFFS = [
    {
        "id": 1,
        "emoji": "📦",
        "name": "Мини",
        "price": 5_000,
        "contact_limit": 50,
        "description": "100 ₽/контакт",
        "sort_order": 1,
        "is_active": True,
    },
    {
        "id": 2,
        "emoji": "🚀",
        "name": "Старт",
        "price": 9_000,
        "contact_limit": 100,
        "description": "90 ₽/контакт",
        "sort_order": 2,
        "is_active": True,
    },
    {
        "id": 3,
        "emoji": "📈",
        "name": "Рост",
        "price": 20_000,
        "contact_limit": 250,
        "description": "80 ₽/контакт",
        "sort_order": 3,
        "is_active": True,
    },
    {
        "id": 4,
        "emoji": "🏢",
        "name": "Бизнес",
        "price": 35_000,
        "contact_limit": 500,
        "description": "70 ₽/контакт",
        "sort_order": 4,
        "is_active": True,
    },
    {
        "id": 5,
        "emoji": "🐺",
        "name": "Масштаб",
        "price": 60_000,
        "contact_limit": 1_000,
        "description": "60 ₽/контакт",
        "sort_order": 5,
        "is_active": True,
    },
]


def _migrate_payments_contact_limit(sync_conn) -> None:
    from sqlalchemy import inspect, text

    insp = inspect(sync_conn)
    if not insp.has_table("payments"):
        return
    cols = {c["name"] for c in insp.get_columns("payments")}
    if "contact_limit" not in cols:
        sync_conn.execute(text("ALTER TABLE payments ADD COLUMN contact_limit INTEGER"))


def _migrate_tariff_columns(sync_conn) -> None:
    from sqlalchemy import inspect, text

    insp = inspect(sync_conn)
    if not insp.has_table("tariffs"):
        return

    cols = {c["name"] for c in insp.get_columns("tariffs")}
    dialect = sync_conn.dialect.name
    additions = [
        ("emoji", "VARCHAR(10)", "''"),
        ("description", "TEXT", "NULL"),
        ("sort_order", "INTEGER", "0"),
        ("is_active", "BOOLEAN", "TRUE" if dialect == "postgresql" else "1"),
    ]
    for name, col_type, default in additions:
        if name not in cols:
            sync_conn.execute(
                text(f"ALTER TABLE tariffs ADD COLUMN {name} {col_type} DEFAULT {default}")
            )


def _migrate_competitor_numbers(sync_conn) -> None:
    from sqlalchemy import inspect, text

    try:
        insp = inspect(sync_conn)
        if not insp.has_table("competitor_numbers"):
            return
        if not insp.has_table("competitors"):
            return

        sync_conn.execute(
            text(
                """
                INSERT INTO competitor_numbers (user_id, phone, status, created_at, updated_at)
                SELECT
                    c.user_id,
                    c.normalized_phone,
                    'active',
                    c.created_at,
                    c.created_at
                FROM (
                    SELECT
                        user_id,
                        created_at,
                        CASE
                            WHEN phone LIKE '+7%' THEN replace(phone, '+', '')
                            WHEN phone LIKE '7%' AND length(phone) = 11 THEN phone
                            ELSE regexp_replace(phone, '[^0-9]', '', 'g')
                        END AS normalized_phone
                    FROM competitors
                ) c
                WHERE length(c.normalized_phone) = 11
                  AND c.normalized_phone LIKE '7%'
                  AND NOT EXISTS (
                      SELECT 1 FROM competitor_numbers cn
                      WHERE cn.user_id = c.user_id AND cn.phone = c.normalized_phone
                  )
                """
            )
        )
    except Exception:
        pass


def _migrate_deliveries(sync_conn) -> None:
    from sqlalchemy import inspect, text

    insp = inspect(sync_conn)
    dialect = sync_conn.dialect.name

    if insp.has_table("contact_deliveries") and not insp.has_table("deliveries"):
        if dialect == "postgresql":
            sync_conn.execute(text("ALTER TABLE contact_deliveries RENAME TO deliveries"))
        else:
            sync_conn.execute(text("ALTER TABLE contact_deliveries RENAME TO deliveries"))

    if not insp.has_table("deliveries"):
        return

    cols = {c["name"] for c in insp.get_columns("deliveries")}

    if "count" in cols and "contacts_count" not in cols:
        if dialect == "postgresql":
            sync_conn.execute(text("ALTER TABLE deliveries RENAME COLUMN count TO contacts_count"))
        else:
            sync_conn.execute(text("ALTER TABLE deliveries ADD COLUMN contacts_count INTEGER DEFAULT 0"))
            sync_conn.execute(text("UPDATE deliveries SET contacts_count = count WHERE contacts_count = 0"))
        cols.add("contacts_count")

    blob_type = "BYTEA" if dialect == "postgresql" else "BLOB"
    additions = [
        ("delivery_type", "VARCHAR(20)", "'message'"),
        ("contacts_text", "TEXT", "NULL"),
        ("file_name", "VARCHAR(255)", "NULL"),
        ("file_path", "VARCHAR(512)", "NULL"),
        ("file_data", blob_type, "NULL"),
        ("admin_id", "VARCHAR(100)", "NULL"),
    ]
    for name, col_type, default in additions:
        if name not in cols:
            sync_conn.execute(
                text(f"ALTER TABLE deliveries ADD COLUMN {name} {col_type} DEFAULT {default}")
            )


def _migrate_projects(sync_conn) -> None:
    from sqlalchemy import inspect, text

    insp = inspect(sync_conn)
    dialect = sync_conn.dialect.name

    if not insp.has_table("projects"):
        return

    if insp.has_table("competitor_numbers"):
        cols = {c["name"] for c in insp.get_columns("competitor_numbers")}
        if "project_id" not in cols:
            sync_conn.execute(text("ALTER TABLE competitor_numbers ADD COLUMN project_id INTEGER"))
        if "added_by" not in cols:
            sync_conn.execute(
                text("ALTER TABLE competitor_numbers ADD COLUMN added_by VARCHAR(100) DEFAULT 'user'")
            )

    if insp.has_table("deliveries"):
        cols = {c["name"] for c in insp.get_columns("deliveries")}
        if "project_id" not in cols:
            sync_conn.execute(text("ALTER TABLE deliveries ADD COLUMN project_id INTEGER"))

    sync_conn.execute(
        text(
            """
            INSERT INTO projects (user_id, order_id, project_name, status, created_at, updated_at)
            SELECT o.user_id, o.id, NULL, 'active', COALESCE(o.paid_at, o.created_at), COALESCE(o.paid_at, o.created_at)
            FROM orders o
            WHERE o.status IN ('active', 'in_progress', 'completed')
              AND NOT EXISTS (SELECT 1 FROM projects p WHERE p.order_id = o.id)
            """
        )
    )

    if dialect == "postgresql":
        sync_conn.execute(
            text(
                """
                UPDATE competitor_numbers cn
                SET project_id = p.id
                FROM projects p
                WHERE cn.user_id = p.user_id AND cn.project_id IS NULL
                """
            )
        )
        sync_conn.execute(
            text(
                """
                UPDATE deliveries d
                SET project_id = p.id
                FROM projects p
                WHERE d.order_id = p.order_id AND d.project_id IS NULL
                """
            )
        )
    else:
        sync_conn.execute(
            text(
                """
                UPDATE competitor_numbers
                SET project_id = (
                    SELECT p.id FROM projects p
                    WHERE p.user_id = competitor_numbers.user_id
                    ORDER BY p.id DESC LIMIT 1
                )
                WHERE project_id IS NULL
                """
            )
        )
        sync_conn.execute(
            text(
                """
                UPDATE deliveries
                SET project_id = (
                    SELECT p.id FROM projects p
                    WHERE p.order_id = deliveries.order_id LIMIT 1
                )
                WHERE project_id IS NULL
                """
            )
        )


def _migrate_referral_commissions(sync_conn) -> None:
    from sqlalchemy import inspect, text

    insp = inspect(sync_conn)
    if not insp.has_table("referral_commissions"):
        return


def _migrate_bank_invoice_columns(sync_conn) -> None:
    from sqlalchemy import inspect, text

    insp = inspect(sync_conn)
    if not insp.has_table("bank_payment_requests"):
        return
    cols = {c["name"] for c in insp.get_columns("bank_payment_requests")}
    additions = [
        ("payment_id", "INTEGER", "NULL"),
        ("company_name", "VARCHAR(512)", "NULL"),
        ("company_inn", "VARCHAR(12)", "NULL"),
        ("invoice_email", "VARCHAR(255)", "NULL"),
        ("requisites_file_id", "VARCHAR(128)", "NULL"),
        ("requisites_file_name", "VARCHAR(255)", "NULL"),
    ]
    for name, col_type, default in additions:
        if name not in cols:
            sync_conn.execute(
                text(f"ALTER TABLE bank_payment_requests ADD COLUMN {name} {col_type} DEFAULT {default}")
            )


def _migrate_users_referral(sync_conn) -> None:
    from sqlalchemy import inspect, text

    insp = inspect(sync_conn)
    if not insp.has_table("users"):
        return
    cols = {c["name"] for c in insp.get_columns("users")}
    if "referral_code" not in cols:
        sync_conn.execute(text("ALTER TABLE users ADD COLUMN referral_code VARCHAR(32)"))
    if "referred_by_user_id" not in cols:
        sync_conn.execute(text("ALTER TABLE users ADD COLUMN referred_by_user_id INTEGER"))
    if "partner_agreed_at" not in cols:
        dialect = sync_conn.dialect.name
        ts_type = "TIMESTAMP WITH TIME ZONE" if dialect == "postgresql" else "DATETIME"
        sync_conn.execute(text(f"ALTER TABLE users ADD COLUMN partner_agreed_at {ts_type}"))
    dialect = sync_conn.dialect.name
    if dialect == "postgresql":
        sync_conn.execute(
            text(
                "UPDATE users SET referral_code = 'ref' || id::text "
                "WHERE referral_code IS NULL OR referral_code = ''"
            )
        )
    else:
        sync_conn.execute(
            text(
                "UPDATE users SET referral_code = 'ref' || id "
                "WHERE referral_code IS NULL OR referral_code = ''"
            )
        )


def _migrate_users_start_source(sync_conn) -> None:
    from sqlalchemy import inspect, text

    insp = inspect(sync_conn)
    if not insp.has_table("users"):
        return
    cols = {c["name"] for c in insp.get_columns("users")}
    if "start_source" not in cols:
        sync_conn.execute(text("ALTER TABLE users ADD COLUMN start_source VARCHAR(64)"))


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_users_start_source)
        await conn.run_sync(_migrate_users_referral)
        await conn.run_sync(_migrate_bank_invoice_columns)
        await conn.run_sync(_migrate_referral_commissions)
        await conn.run_sync(_migrate_tariff_columns)
        await conn.run_sync(_migrate_payments_contact_limit)
        await conn.run_sync(_migrate_competitor_numbers)
        await conn.run_sync(_migrate_deliveries)
        await conn.run_sync(_migrate_projects)

    async with async_session() as session:
        for t in TARIFFS:
            existing = await session.get(Tariff, t["id"])
            if existing:
                for key, value in t.items():
                    setattr(existing, key, value)
            else:
                session.add(Tariff(**t))
        await session.commit()
        await _seed_admin_notifications(session)


async def _seed_admin_notifications(session) -> None:
    from sqlalchemy import select

    from database.models import AdminNotification
    from services.admin_notify_service import resolve_admin_telegram_id

    telegram_id = await resolve_admin_telegram_id(session)
    if not telegram_id:
        return
    result = await session.execute(select(AdminNotification).limit(1))
    if result.scalar_one_or_none():
        return
    session.add(AdminNotification(telegram_id=telegram_id))
    await session.commit()
