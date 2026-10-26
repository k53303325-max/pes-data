from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    ActivityType,
    DeliveredContact,
    Delivery,
    DeliveryType,
    Order,
    OrderStatus,
    User,
    UserStatus,
)
from services.activity_service import log_activity
from services.project_service import get_project_by_order
from services.user_service import order_remaining
from utils.phone import extract_phones, extract_phones_with_stats, normalize_phone


@dataclass
class DeliveryPreview:
    phones: list[str]
    duplicates: int
    invalid: int
    skipped_limit: int
    will_send: int
    received: int
    limit: int
    remaining: int
    after_received: int
    after_remaining: int


@dataclass
class DeliveryResult:
    delivery_id: int
    sent_count: int
    order_id: int
    user_db_id: int
    user_telegram_id: int
    received: int
    limit: int
    remaining: int
    order_completed: bool
    phones: list[str]
    delivery_type: str
    file_name: str | None
    file_data: bytes | None
    project_id: int | None


def display_phone(phone: str) -> str:
    return phone.lstrip("+")


def phones_to_text(phones: list[str]) -> str:
    return "\n".join(display_phone(p) for p in phones)


def parse_contacts_text(text: str) -> tuple[list[str], int]:
    return extract_phones_with_stats(text)


def parse_contacts_file(content: bytes, filename: str) -> tuple[list[str], int]:
    name = filename.lower()
    if name.endswith(".xlsx"):
        return _parse_xlsx(content)
    if name.endswith(".csv"):
        return _parse_csv(content)
    return extract_phones_with_stats(content.decode("utf-8", errors="ignore"))


def _parse_csv(content: bytes) -> tuple[list[str], int]:
    text = content.decode("utf-8-sig", errors="ignore")
    phones: list[str] = []
    invalid = 0
    reader = csv.reader(io.StringIO(text))
    for row in reader:
        chunk, bad = extract_phones_with_stats(" ".join(row))
        phones.extend(chunk)
        invalid += bad
    return _dedupe_preserve_order(phones), invalid


def _parse_xlsx(content: bytes) -> tuple[list[str], int]:
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    phones: list[str] = []
    invalid = 0
    for sheet in wb.worksheets:
        for row in sheet.iter_rows(values_only=True):
            for cell in row:
                if cell is None:
                    continue
                if isinstance(cell, float) and cell == int(cell):
                    cell_str = str(int(cell))
                elif isinstance(cell, int):
                    cell_str = str(cell)
                else:
                    cell_str = str(cell)
                normalized = normalize_phone(cell_str)
                if normalized:
                    phones.append(normalized)
                elif str(cell).strip() and any(ch.isdigit() for ch in str(cell)):
                    invalid += 1
    return _dedupe_preserve_order(phones), invalid


def _dedupe_preserve_order(phones: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for phone in phones:
        if phone not in seen:
            seen.add(phone)
            result.append(phone)
    return result


async def preview_delivery(
    session: AsyncSession,
    order_id: int,
    phones: list[str],
    *,
    invalid: int = 0,
) -> DeliveryPreview:
    order = await session.get(Order, order_id)
    if not order:
        raise ValueError("Заказ не найден")

    remaining = order_remaining(order)
    unique_valid = _dedupe_preserve_order(phones)

    existing = await session.execute(
        select(DeliveredContact.phone).where(DeliveredContact.order_id == order_id)
    )
    existing_phones = set(existing.scalars().all())

    new_phones: list[str] = []
    duplicates = 0
    for phone in unique_valid:
        if phone in existing_phones:
            duplicates += 1
        else:
            new_phones.append(phone)

    will_send = min(len(new_phones), remaining)
    skipped = len(new_phones) - will_send
    phones_to_send = new_phones[:will_send]

    return DeliveryPreview(
        phones=phones_to_send,
        duplicates=duplicates,
        invalid=invalid,
        skipped_limit=skipped,
        will_send=will_send,
        received=order.received,
        limit=order.contact_limit,
        remaining=remaining,
        after_received=order.received + will_send,
        after_remaining=max(0, remaining - will_send),
    )


async def commit_delivery(
    session: AsyncSession,
    order_id: int,
    phones: list[str],
    *,
    delivery_type: str = DeliveryType.MESSAGE.value,
    contacts_text: str | None = None,
    file_name: str | None = None,
    file_data: bytes | None = None,
    admin_id: str | None = None,
    note: str | None = None,
    invalid: int = 0,
) -> DeliveryResult:
    order = await session.get(Order, order_id)
    if not order:
        raise ValueError("Заказ не найден")

    user = await session.get(User, order.user_id)
    if not user:
        raise ValueError("Пользователь не найден")

    project = await get_project_by_order(session, order.id)

    preview = await preview_delivery(session, order_id, phones, invalid=invalid)
    to_send = preview.phones

    if not to_send:
        raise ValueError("Нет контактов для отправки")

    if not contacts_text:
        contacts_text = phones_to_text(to_send)

    delivery = Delivery(
        user_id=user.id,
        order_id=order.id,
        project_id=project.id if project else None,
        delivery_type=delivery_type,
        contacts_count=len(to_send),
        contacts_text=contacts_text,
        file_name=file_name,
        file_path=None,
        file_data=file_data,
        admin_id=admin_id,
        note=note,
    )
    session.add(delivery)
    await session.flush()
    delivery.file_path = f"/deliveries/{delivery.id}/download" if file_name or file_data else None

    for phone in to_send:
        session.add(
            DeliveredContact(
                delivery_id=delivery.id,
                order_id=order.id,
                phone=phone,
            )
        )

    order.received += len(to_send)
    order.status = OrderStatus.IN_PROGRESS.value
    user.status = UserStatus.ACTIVE.value

    order_completed = order.received >= order.contact_limit
    if order_completed:
        order.status = OrderStatus.COMPLETED.value
        order.completed_at = datetime.now(timezone.utc)
        user.status = UserStatus.FINISHED.value
        if project:
            project.status = "completed"

    if project:
        await log_activity(
            session,
            project_id=project.id,
            user_id=user.id,
            action_type=ActivityType.CONTACTS_SENT.value,
            description=f"Администратор отправил: {len(to_send)} новых контактов",
            contacts_count=len(to_send),
            admin_id=admin_id,
        )

    await session.commit()
    await session.refresh(order)
    await session.refresh(user)
    await session.refresh(delivery)

    if order_completed:
        from services.admin_notify_service import notify_admin_package_completed

        await session.refresh(order, ["tariff"])
        pname = project.project_name if project else None
        tname = order.tariff.name if order.tariff else "—"
        await notify_admin_package_completed(
            user,
            project_name=pname,
            tariff_name=tname,
            contact_limit=order.contact_limit,
            completed_at=order.completed_at,
        )

    return DeliveryResult(
        delivery_id=delivery.id,
        sent_count=len(to_send),
        order_id=order.id,
        user_db_id=user.id,
        user_telegram_id=user.telegram_id,
        received=order.received,
        limit=order.contact_limit,
        remaining=order_remaining(order),
        order_completed=order_completed,
        phones=to_send,
        delivery_type=delivery_type,
        file_name=file_name,
        file_data=file_data,
        project_id=project.id if project else None,
    )
