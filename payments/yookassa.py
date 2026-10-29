from __future__ import annotations

import base64
import uuid
from dataclasses import dataclass

import aiohttp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.models import Order, OrderStatus, Payment, PaymentStatus, User, UserStatus
from services.order_service import activate_order_from_payment
from services.tariff_service import TariffInfo
from utils.logger import get_logger

logger = get_logger(__name__)

YOOKASSA_API = "https://api.yookassa.ru/v3/payments"

PAYMENT_UNAVAILABLE_MSG = (
    "Оплата временно недоступна. Администратор настраивает подключение к ЮKassa."
)
INVALID_CREDENTIALS_MSG = (
    "Оплата временно недоступна: неверные ключи ЮKassa. "
    "Обратитесь к администратору."
)


@dataclass
class PaymentLink:
    payment_db_id: int
    external_id: str
    confirmation_url: str | None
    amount: int
    is_mock: bool = False


def mock_payment_allowed() -> bool:
    return settings.allow_mock_payment


def _yookassa_configured() -> bool:
    shop = settings.yookassa_shop_id
    secret = settings.yookassa_secret_key
    if not shop or not secret:
        return False
    placeholders = ("your_shop", "your_secret", "your_bot", "change-me", "example")
    combined = f"{shop} {secret}".lower()
    return not any(token in combined for token in placeholders)


is_yookassa_configured = _yookassa_configured


def _is_auth_error(body: dict | str, status: int) -> bool:
    if status == 401:
        return True
    if isinstance(body, dict):
        code = str(body.get("code", "")).lower()
        description = str(body.get("description", "")).lower()
        return code == "invalid_credentials" or "shopid" in description or "secret key" in description
    return False


async def _finalize_mock_payment(
    session: AsyncSession,
    payment: Payment,
    pay_amount: int,
    *,
    reason: str,
) -> PaymentLink:
    if not mock_payment_allowed():
        raise ValueError(PAYMENT_UNAVAILABLE_MSG)

    mock_id = f"mock_{uuid.uuid4().hex[:16]}"
    payment.external_id = mock_id
    await session.commit()
    logger.warning("Using mock payment id=%s reason=%s", payment.id, reason)
    return PaymentLink(
        payment_db_id=payment.id,
        external_id=mock_id,
        confirmation_url=None,
        amount=pay_amount,
        is_mock=True,
    )


def _payment_description(
    tariff: TariffInfo, pay_amount: int, contact_limit: int
) -> str:
    promo_note = " (промокод)" if pay_amount == 0 else ""
    text = f"Пёс Дата — {contact_limit} контактов{promo_note}"
    return text[:128]


def _build_receipt(
    tariff: TariffInfo, pay_amount: int, user: User, contact_limit: int
) -> dict:
    item_name = f"Контакты ({contact_limit} шт.)"[:128]
    amount_value = f"{pay_amount:.2f}"
    return {
        "customer": {"email": f"user{user.telegram_id}@pesdata.app"},
        "items": [
            {
                "description": item_name,
                "quantity": "1.00",
                "amount": {"value": amount_value, "currency": "RUB"},
                "vat_code": 1,
                "payment_mode": "full_payment",
                "payment_subject": "service",
            }
        ],
    }


def _build_payload(
    payment: Payment,
    user: User,
    tariff: TariffInfo,
    pay_amount: int,
    contact_limit: int,
    *,
    with_receipt: bool,
) -> dict:
    payload = {
        "amount": {"value": f"{pay_amount:.2f}", "currency": "RUB"},
        "confirmation": {
            "type": "redirect",
            "return_url": settings.yookassa_return_url,
        },
        "capture": True,
        "description": _payment_description(tariff, pay_amount, contact_limit),
        "metadata": {
            "payment_db_id": str(payment.id),
            "user_telegram_id": str(user.telegram_id),
            "tariff_id": str(tariff.id),
            "contact_limit": str(contact_limit),
        },
    }
    if with_receipt:
        payload["receipt"] = _build_receipt(tariff, pay_amount, user, contact_limit)
    return payload


def _needs_receipt_retry(message: str) -> bool:
    lowered = message.lower()
    return any(token in lowered for token in ("receipt", "чек", "54-фз", "fiscal"))


async def _create_yookassa_payment_with_retry(
    payment: Payment,
    user: User,
    tariff: TariffInfo,
    pay_amount: int,
    contact_limit: int,
) -> dict:
    last_error: ValueError | None = None

    for with_receipt in (False, True):
        payload = _build_payload(
            payment,
            user,
            tariff,
            pay_amount,
            contact_limit,
            with_receipt=with_receipt,
        )
        try:
            return await _create_yookassa_payment(payload)
        except ValueError as exc:
            last_error = exc
            if str(exc) == "invalid_credentials":
                raise ValueError(INVALID_CREDENTIALS_MSG) from exc
            if not with_receipt and _needs_receipt_retry(str(exc)):
                logger.info("Retrying YooKassa payment with receipt")
                continue
            raise

    if last_error:
        raise last_error
    raise ValueError("ЮKassa: не удалось создать платёж")


def _yookassa_error_message(body: dict | str, status: int) -> str:
    if isinstance(body, dict):
        for key in ("description", "code", "type"):
            value = body.get(key)
            if value:
                text = str(value)
                lowered = text.lower()
                if "shopid" in lowered or "secret key" in lowered:
                    return INVALID_CREDENTIALS_MSG
                return text
        if body.get("parameter"):
            return f"{body.get('parameter')}: {body.get('description', 'ошибка')}"
    return f"HTTP {status}"


def _yookassa_auth_header() -> str:
    token = base64.b64encode(
        f"{settings.yookassa_shop_id}:{settings.yookassa_secret_key}".encode()
    ).decode()
    return f"Basic {token}"


async def fetch_yookassa_payment(external_id: str, *, timeout_sec: float = 15) -> dict | None:
    """Запрашивает актуальный статус платежа в ЮKassa."""
    if not _yookassa_configured() or not external_id or external_id.startswith("mock_"):
        return None

    headers = {
        "Authorization": _yookassa_auth_header(),
        "Content-Type": "application/json",
    }
    url = f"{YOOKASSA_API}/{external_id}"
    timeout = aiohttp.ClientTimeout(total=timeout_sec)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as http:
            async with http.get(url, headers=headers) as resp:
                try:
                    body = await resp.json(content_type=None)
                except Exception:
                    body = await resp.text()
                if resp.status >= 400:
                    logger.error(
                        "YooKassa fetch payment failed external_id=%s status=%s body=%s",
                        external_id,
                        resp.status,
                        body,
                    )
                    return None
                if isinstance(body, dict):
                    return body
    except Exception:
        logger.exception("YooKassa fetch payment request failed external_id=%s", external_id)
    return None


async def sync_pending_payment(
    session: AsyncSession, payment: Payment
) -> tuple[User, Order] | None:
    """Проверяет pending-платёж в ЮKassa и активирует заказ, если оплата прошла."""
    if payment.status != PaymentStatus.PENDING.value:
        return None
    if not payment.external_id or payment.external_id.startswith("mock_"):
        return None

    yoo_payment = await fetch_yookassa_payment(payment.external_id, timeout_sec=8)
    if not yoo_payment:
        return None
    if yoo_payment.get("status") != "succeeded":
        return None

    logger.info(
        "Syncing succeeded payment from YooKassa: payment_id=%s external_id=%s",
        payment.id,
        payment.external_id,
    )
    return await process_successful_payment(session, payment.external_id)


async def sync_user_pending_payments(
    session: AsyncSession, user_id: int
) -> tuple[User, Order] | None:
    """Синхронизирует все pending-платежи пользователя (от новых к старым)."""
    result = await session.execute(
        select(Payment)
        .where(
            Payment.user_id == user_id,
            Payment.status == PaymentStatus.PENDING.value,
            Payment.external_id.isnot(None),
        )
        .order_by(Payment.created_at.desc())
    )
    for payment in result.scalars():
        activated = await sync_pending_payment(session, payment)
        if activated:
            return activated
    return None


async def sync_all_pending_payments(session: AsyncSession) -> list[tuple[User, Order]]:
    """Синхронизирует все pending-платежи в БД."""
    result = await session.execute(
        select(Payment)
        .where(
            Payment.status == PaymentStatus.PENDING.value,
            Payment.external_id.isnot(None),
        )
        .order_by(Payment.created_at.desc())
    )
    activated: list[tuple[User, Order]] = []
    for payment in result.scalars():
        item = await sync_pending_payment(session, payment)
        if item:
            activated.append(item)
    return activated


async def _create_yookassa_payment(payload: dict) -> dict:
    headers = {
        "Authorization": _yookassa_auth_header(),
        "Idempotence-Key": str(uuid.uuid4()),
        "Content-Type": "application/json",
    }

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as http:
        async with http.post(YOOKASSA_API, json=payload, headers=headers) as resp:
            try:
                body = await resp.json(content_type=None)
            except Exception:
                body = await resp.text()

            if resp.status >= 400:
                message = _yookassa_error_message(body, resp.status)
                logger.error("YooKassa API error %s: %s", resp.status, body)
                if _is_auth_error(body, resp.status):
                    raise ValueError("invalid_credentials")
                raise ValueError(f"ЮKassa: {message}")

            if not isinstance(body, dict):
                raise ValueError("ЮKassa: некорректный ответ сервера")

            return body


async def create_payment(
    session: AsyncSession,
    user: User,
    tariff: TariffInfo,
    amount: int | None = None,
    contact_limit: int | None = None,
) -> PaymentLink:
    if user.status == UserStatus.BLOCKED.value:
        raise ValueError("Аккаунт заблокирован")

    active = await session.execute(
        select(Order.id).where(
            Order.user_id == user.id,
            Order.status.in_([OrderStatus.ACTIVE.value, OrderStatus.IN_PROGRESS.value]),
        ).limit(1)
    )
    if active.scalar_one_or_none():
        raise ValueError("Сначала завершите текущий пакет")

    limit = contact_limit or tariff.contact_limit
    if not limit:
        raise ValueError("Не указано количество контактов")

    pay_amount = amount if amount is not None else tariff.price

    payment = Payment(
        user_id=user.id,
        tariff_id=tariff.id,
        contact_limit=limit,
        amount=pay_amount,
        status=PaymentStatus.PENDING.value,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)

    if not _yookassa_configured():
        return await _finalize_mock_payment(
            session,
            payment,
            pay_amount,
            reason="not_configured",
        )

    try:
        yoo_payment = await _create_yookassa_payment_with_retry(
            payment, user, tariff, pay_amount, limit
        )
    except ValueError:
        payment.status = PaymentStatus.CANCELED.value
        await session.commit()
        raise
    except Exception as exc:
        payment.status = PaymentStatus.CANCELED.value
        await session.commit()
        logger.exception("YooKassa request failed")
        raise ValueError("Не удалось связаться с ЮKassa. Попробуйте позже.") from exc

    external_id = yoo_payment.get("id")
    if not external_id:
        payment.status = PaymentStatus.CANCELED.value
        await session.commit()
        raise ValueError("ЮKassa: не получен идентификатор платежа")

    confirmation = yoo_payment.get("confirmation") or {}
    confirmation_url = confirmation.get("confirmation_url")

    payment.external_id = external_id
    await session.commit()

    logger.info(
        "YooKassa payment created: external_id=%s user=%s tariff=%s",
        external_id,
        user.telegram_id,
        tariff.id,
    )

    return PaymentLink(
        payment_db_id=payment.id,
        external_id=external_id,
        confirmation_url=confirmation_url,
        amount=pay_amount,
        is_mock=False,
    )


async def process_successful_payment(
    session: AsyncSession, external_id: str
) -> tuple[User, Order] | None:
    result = await session.execute(
        select(Payment).where(Payment.external_id == external_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        logger.error("Payment not found: external_id=%s", external_id)
        return None

    if payment.status == PaymentStatus.PAID.value:
        user = await session.get(User, payment.user_id)
        order = await session.get(Order, payment.order_id) if payment.order_id else None
        if user and order:
            await session.refresh(order, ["tariff"])
            return user, order
        return None

    try:
        user, order = await activate_order_from_payment(session, payment)
    except ValueError as exc:
        logger.error("Order activation failed: %s", exc)
        return None

    logger.info(
        "Payment succeeded: external_id=%s user=%s order=%s",
        external_id,
        user.telegram_id,
        order.id,
    )
    return user, order


async def confirm_mock_payment(session: AsyncSession, payment_db_id: int) -> tuple[User, Order] | None:
    if not mock_payment_allowed():
        logger.warning("Mock payment blocked: payment_db_id=%s", payment_db_id)
        return None

    payment = await session.get(Payment, payment_db_id)
    if not payment or not payment.external_id or not payment.external_id.startswith("mock_"):
        return None
    return await process_successful_payment(session, payment.external_id)
