from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Tariff


@dataclass(frozen=True)
class TariffInfo:
    id: int
    name: str
    price: int
    limit: int


async def get_all_tariffs(session: AsyncSession) -> list[TariffInfo]:
    result = await session.execute(select(Tariff).order_by(Tariff.price))
    tariffs = result.scalars().all()
    return [
        TariffInfo(id=t.id, name=t.name, price=t.price, limit=t.limit) for t in tariffs
    ]


async def get_tariff(session: AsyncSession, tariff_id: int) -> TariffInfo | None:
    tariff = await session.get(Tariff, tariff_id)
    if not tariff:
        return None
    return TariffInfo(
        id=tariff.id, name=tariff.name, price=tariff.price, limit=tariff.limit
    )


def format_tariff(t: TariffInfo) -> str:
    return f"{t.name}: {t.price:,} ₽ → {t.limit:,} контактов".replace(",", " ")
