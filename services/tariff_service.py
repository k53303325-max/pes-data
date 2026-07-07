from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Tariff


@dataclass(frozen=True)
class TariffInfo:
    id: int
    name: str
    price: int
    contact_limit: int


async def get_all_tariffs(session: AsyncSession) -> list[TariffInfo]:
    result = await session.execute(select(Tariff).order_by(Tariff.price))
    return [
        TariffInfo(
            id=t.id,
            name=t.name,
            price=t.price,
            contact_limit=t.contact_limit,
        )
        for t in result.scalars().all()
    ]


async def get_tariff(session: AsyncSession, tariff_id: int) -> TariffInfo | None:
    tariff = await session.get(Tariff, tariff_id)
    if not tariff:
        return None
    return TariffInfo(
        id=tariff.id,
        name=tariff.name,
        price=tariff.price,
        contact_limit=tariff.contact_limit,
    )


def format_tariff(t: TariffInfo) -> str:
    return (
        f"• <b>{t.name}</b> — {t.price:,} ₽ → {t.contact_limit:,} контактов".replace(",", " ")
    )


def format_tariffs_list(tariffs: list[TariffInfo]) -> str:
    lines = ["💰 <b>Выберите пакет</b>", ""]
    lines.extend(format_tariff(t) for t in tariffs)
    lines.append("")
    lines.append("После оплаты вы сможете добавлять номера конкурентов.")
    return "\n".join(lines)
