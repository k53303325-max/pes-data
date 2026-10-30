from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from payments.yookassa import PaymentLink, create_payment
from services.package_catalog import PackageOffer, get_package
from services.tariff_service import get_tariff


def format_payment_intro(pkg: PackageOffer) -> str:
    price = f"{pkg.price:,} ₽".replace(",", " ")
    return (
        f"<b>Оплата пакета «{pkg.name}»</b>\n\n"
        f"Контактов: {pkg.contact_count}\n"
        f"Сумма: {price}\n\n"
        "• <b>Физлицо</b> — оплата картой или СБП (ЮKassa);\n"
        "• <b>Юрлицо / ИП</b> — выставим счёт (нужны название и ИНН).\n"
        "Промокод — кнопка ниже после выбора ЮKassa."
    )


async def create_package_yookassa_payment(
    session: AsyncSession,
    user: User,
    pkg: PackageOffer,
) -> PaymentLink:
    if not pkg.tariff_id:
        raise ValueError("Оплата для этого пакета недоступна")
    tariff = await get_tariff(session, pkg.tariff_id)
    if not tariff:
        raise ValueError("Пакет временно недоступен")
    return await create_payment(
        session,
        user,
        tariff,
        amount=pkg.price,
        contact_limit=pkg.contact_count,
    )


def resolve_package(code: str) -> PackageOffer:
    pkg = get_package(code)
    if not pkg or pkg.is_trial:
        raise ValueError("Пакет не найден")
    if not pkg.tariff_id:
        raise ValueError("Оплата недоступна")
    return pkg
