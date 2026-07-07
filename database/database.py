from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from config.settings import settings
from database.models import Base, Tariff

connect_args: dict = {}
engine_kwargs: dict = {"echo": False}

if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif settings.database_url.startswith("postgresql"):
    connect_args = {"ssl": True}
    if settings.is_vercel:
        engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(
    settings.database_url or "sqlite+aiosqlite:///:memory:",
    connect_args=connect_args,
    **engine_kwargs,
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

TARIFFS = [
    {"id": 1, "name": "Старт", "price": 10_000, "contact_limit": 100},
    {"id": 2, "name": "Бизнес", "price": 60_000, "contact_limit": 1_000},
    {"id": 3, "name": "Стандарт", "price": 150_000, "contact_limit": 30_000},
    {"id": 4, "name": "Профи", "price": 306_000, "contact_limit": 9_000},
    {"id": 5, "name": "Макси", "price": 1_260_000, "contact_limit": 42_000},
]


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        for t in TARIFFS:
            existing = await session.get(Tariff, t["id"])
            if not existing:
                session.add(Tariff(**t))
        await session.commit()
