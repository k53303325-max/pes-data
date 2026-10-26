from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Tariff
from services.tariff_service import TariffInfo, _to_info


async def list_all_tariffs_admin(session: AsyncSession) -> list[TariffInfo]:
    result = await session.execute(
        select(Tariff).order_by(Tariff.sort_order, Tariff.price)
    )
    return [_to_info(t) for t in result.scalars().all()]


async def save_tariff(
    session: AsyncSession,
    *,
    tariff_id: int | None,
    name: str,
    emoji: str,
    price: int,
    contact_limit: int,
    description: str | None,
    sort_order: int,
    is_active: bool,
) -> Tariff:
    if tariff_id:
        tariff = await session.get(Tariff, tariff_id)
        if not tariff:
            raise ValueError("Тариф не найден")
    else:
        tariff = Tariff()
        session.add(tariff)

    tariff.name = name.strip()
    tariff.emoji = emoji.strip()
    tariff.price = price
    tariff.contact_limit = contact_limit
    tariff.description = description.strip() if description else None
    tariff.sort_order = sort_order
    tariff.is_active = is_active

    await session.commit()
    await session.refresh(tariff)
    return tariff


async def toggle_tariff_active(session: AsyncSession, tariff_id: int) -> Tariff:
    tariff = await session.get(Tariff, tariff_id)
    if not tariff:
        raise ValueError("Тариф не найден")
    tariff.is_active = not tariff.is_active
    await session.commit()
    await session.refresh(tariff)
    return tariff
