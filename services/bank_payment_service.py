from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import BankPaymentRequest, BankPaymentStatus, Payment, PaymentStatus, User
from services.package_catalog import PackageOffer
from services.tariff_service import get_tariff
from utils.inn import validate_inn

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


async def cancel_user_pending_payments(session: AsyncSession, user_id: int) -> None:
    result = await session.execute(
        select(Payment).where(
            Payment.user_id == user_id,
            Payment.status == PaymentStatus.PENDING.value,
        )
    )
    for pay in result.scalars().all():
        pay.status = PaymentStatus.CANCELED.value
    await session.commit()


async def create_bank_invoice_request(
    session: AsyncSession,
    user: User,
    pkg: PackageOffer,
    *,
    company_name: str,
    company_inn: str | None,
    invoice_email: str | None = None,
    requisites_file_id: str | None = None,
    requisites_file_name: str | None = None,
) -> BankPaymentRequest:
    if not pkg.tariff_id:
        raise ValueError("Пакет недоступен")

    await cancel_user_pending_payments(session, user.id)

    tariff = await get_tariff(session, pkg.tariff_id)
    if not tariff:
        raise ValueError("Тариф не найден")

    payment = Payment(
        user_id=user.id,
        tariff_id=tariff.id,
        contact_limit=pkg.contact_count,
        amount=pkg.price,
        status=PaymentStatus.PENDING.value,
        external_id=f"bank_pending_{uuid.uuid4().hex[:12]}",
    )
    session.add(payment)
    await session.flush()

    row = BankPaymentRequest(
        user_id=user.id,
        payment_id=payment.id,
        package_code=pkg.code,
        package_name=pkg.name,
        contact_limit=pkg.contact_count,
        amount=pkg.price,
        status=BankPaymentStatus.AWAITING_PAYMENT.value,
        company_name=company_name.strip()[:512],
        company_inn=company_inn,
        invoice_email=(invoice_email or "").strip()[:255] or None,
        requisites_file_id=requisites_file_id,
        requisites_file_name=requisites_file_name,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


def parse_invoice_message(text: str) -> tuple[str, str, str | None]:
    raw = (text or "").strip()
    if len(raw) < 5:
        raise ValueError("Слишком короткое сообщение")

    email: str | None = None
    email_match = EMAIL_RE.search(raw)
    if email_match:
        email = email_match.group(0)

    inn: str | None = None
    for token in re.findall(r"\d{10,12}", raw):
        ok, normalized = validate_inn(token)
        if ok and normalized:
            inn = normalized
            break
    if not inn:
        raise ValueError("Укажите корректный ИНН (10 или 12 цифр)")

    company = raw
    if email:
        company = company.replace(email, "")
    company = re.sub(r"\d{10,12}", "", company).strip()
    company = " ".join(company.split())
    if len(company) < 2:
        company = "ИП / организация"

    return company, inn, email


async def confirm_bank_payment_paid(
    session: AsyncSession,
    request: BankPaymentRequest,
) -> None:
    if request.status == BankPaymentStatus.PAID.value:
        return

    if not request.payment_id:
        raise ValueError("У заявки нет связанного платежа")

    payment = await session.get(Payment, request.payment_id)
    if not payment:
        raise ValueError("Платёж не найден")

    if payment.status == PaymentStatus.PAID.value:
        request.status = BankPaymentStatus.PAID.value
        await session.commit()
        return

    payment.paid_at = datetime.now(timezone.utc)
    from services.order_service import activate_order_from_payment

    await activate_order_from_payment(session, payment)
    request.status = BankPaymentStatus.PAID.value
    await session.commit()
