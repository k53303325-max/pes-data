from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config.settings import settings
from db.models import Base, Tariff

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

TARIFFS = [
    {"id": 1, "name": "Старт", "price": 10_000, "limit": 100},
    {"id": 2, "name": "Бизнес", "price": 60_000, "limit": 1_000},
    {"id": 3, "name": "Стандарт", "price": 150_000, "limit": 30_000},
    {"id": 4, "name": "Профи", "price": 306_000, "limit": 9_000},
    {"id": 5, "name": "Макси", "price": 1_260_000, "limit": 42_000},
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


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
