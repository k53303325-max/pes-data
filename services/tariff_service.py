from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Tariff


@dataclass(frozen=True)
class TariffInfo:
    id: int
    name: str
    emoji: str
    price: int
    contact_limit: int
    description: str | None
    sort_order: int
    is_active: bool

    @property
    def display_name(self) -> str:
        return f"{self.emoji} {self.name}".strip() if self.emoji else self.name

    @property
    def button_label(self) -> str:
        limit = format_contact_limit(self.contact_limit)
        price = format_price(self.price)
        return f"{self.display_name} · {limit} контактов · {price}"[:64]


def _to_info(t: Tariff) -> TariffInfo:
    return TariffInfo(
        id=t.id,
        name=t.name,
        emoji=t.emoji or "",
        price=t.price,
        contact_limit=t.contact_limit,
        description=t.description,
        sort_order=t.sort_order or 0,
        is_active=t.is_active if t.is_active is not None else True,
    )


async def get_active_tariffs(session: AsyncSession) -> list[TariffInfo]:
    result = await session.execute(
        select(Tariff)
        .where(Tariff.is_active.is_(True))
        .order_by(Tariff.sort_order, Tariff.price)
    )
    return [_to_info(t) for t in result.scalars().all()]


async def get_all_tariffs(session: AsyncSession, *, include_inactive: bool = False) -> list[TariffInfo]:
    stmt = select(Tariff).order_by(Tariff.sort_order, Tariff.price)
    if not include_inactive:
        stmt = stmt.where(Tariff.is_active.is_(True))
    result = await session.execute(stmt)
    return [_to_info(t) for t in result.scalars().all()]


async def get_tariff(session: AsyncSession, tariff_id: int) -> TariffInfo | None:
    tariff = await session.get(Tariff, tariff_id)
    if not tariff or not tariff.is_active:
        return None
    return _to_info(tariff)


async def get_tariff_any(session: AsyncSession, tariff_id: int) -> TariffInfo | None:
    tariff = await session.get(Tariff, tariff_id)
    if not tariff:
        return None
    return _to_info(tariff)


def format_price(price: int) -> str:
    return f"{price:,} ₽".replace(",", " ")


def format_price_short(price: int) -> str:
    if price >= 1_000_000:
        val = price / 1_000_000
        text = f"{val:.2f}".rstrip("0").rstrip(".")
        return f"{text}M ₽"
    if price >= 10_000:
        return f"{price // 1000}k ₽"
    return format_price(price)


def format_contact_limit(limit: int) -> str:
    return f"{limit:,}".replace(",", " ")


CHOOSE_TARIFF_TEXT = (
    "🐶 <b>Купить контакты</b>\n\n"
    "Укажите нужное количество контактов — стоимость рассчитается автоматически."
)


def format_tariff_block(t: TariffInfo) -> str:
    return (
        f"{t.display_name}\n\n"
        f"Лимит пакета: {format_contact_limit(t.contact_limit)} контактов\n\n"
        f"Стоимость: {format_price(t.price)}"
    )


def format_tariffs_list_message(tariffs: list[TariffInfo]) -> str:
    return CHOOSE_TARIFF_TEXT


def format_tariff_details(t: TariffInfo) -> str:
    limit = format_contact_limit(t.contact_limit)
    return (
        f"🐶 <b>{t.display_name}</b>\n\n"
        f"<b>{format_price(t.price)}</b> · {limit} контактов\n\n"
        f"<b>Что входит:</b>\n\n"
        "✅ Добавление номеров конкурентов\n\n"
        "✅ Отслеживание новых контактов\n\n"
        "✅ Постепенная выдача через Telegram\n\n"
        f"Пакет завершится после {limit} контактов."
    )
