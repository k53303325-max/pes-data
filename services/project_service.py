from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import (
    ActivityType,
    Order,
    OrderStatus,
    Payment,
    PaymentStatus,
    Project,
    ProjectStatus,
    Tariff,
    User,
)
from services.activity_service import log_activity
from services.tariff_service import format_price


PROJECT_NAME_PROMPT = (
    "🏢 <b>Как называется ваш проект или компания?</b>\n\n"
    "Например:\n\n"
    "Ремонт квартир Москва\n\n"
    "Продажа автомобилей\n\n"
    "Юридическая компания\n\n"
    "Это название будет использоваться для удобной идентификации вашего проекта."
)


def project_created_text(project_name: str) -> str:
    return (
        "✅ <b>Проект создан.</b>\n\n"
        f"Название:\n\n{project_name}\n\n"
        "Теперь добавьте номера конкурентов для отслеживания."
    )


async def create_project_for_order(
    session: AsyncSession,
    user: User,
    order: Order,
    *,
    tariff_name: str,
    contact_limit: int,
    price: int = 0,
) -> Project:
    existing = await session.execute(
        select(Project).where(Project.order_id == order.id)
    )
    project = existing.scalar_one_or_none()
    if project:
        return project

    project = Project(
        user_id=user.id,
        order_id=order.id,
        project_name=None,
        status=ProjectStatus.ACTIVE.value,
    )
    session.add(project)
    await session.flush()

    await log_activity(
        session,
        project_id=project.id,
        user_id=user.id,
        action_type=ActivityType.PAYMENT.value,
        description=f"Оплачен пакет: {contact_limit} контактов ({tariff_name})",
        contacts_count=contact_limit,
    )
    await session.commit()
    await session.refresh(project)

    from services.admin_notify_service import notify_admin_payment

    await notify_admin_payment(
        user,
        project_name=project.project_name,
        tariff_name=tariff_name,
        price=price,
        contact_limit=contact_limit,
        paid_at=order.paid_at,
    )
    return project


async def get_project_by_order(session: AsyncSession, order_id: int) -> Project | None:
    result = await session.execute(select(Project).where(Project.order_id == order_id))
    return result.scalar_one_or_none()


async def get_active_project(session: AsyncSession, user_id: int) -> Project | None:
    result = await session.execute(
        select(Project)
        .join(Order, Project.order_id == Order.id)
        .where(
            Project.user_id == user_id,
            Order.status.in_([OrderStatus.ACTIVE.value, OrderStatus.IN_PROGRESS.value]),
        )
        .order_by(Project.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_project_needing_name(session: AsyncSession, user_id: int) -> Project | None:
    project = await get_active_project(session, user_id)
    if project and not project.project_name:
        return project
    return None


async def set_project_name(session: AsyncSession, project: Project, name: str) -> Project:
    cleaned = " ".join(name.strip().split())
    if len(cleaned) < 2:
        raise ValueError("Название слишком короткое")
    if len(cleaned) > 255:
        raise ValueError("Название слишком длинное (макс. 255 символов)")

    project.project_name = cleaned
    await log_activity(
        session,
        project_id=project.id,
        user_id=project.user_id,
        action_type=ActivityType.PROJECT_CREATED.value,
        description=f"Проект создан: {cleaned}",
    )
    await session.commit()
    await session.refresh(project)
    return project


async def complete_project(session: AsyncSession, order_id: int) -> None:
    project = await get_project_by_order(session, order_id)
    if project:
        project.status = ProjectStatus.COMPLETED.value
        await session.commit()


async def get_project_detail(session: AsyncSession, project_id: int) -> Project | None:
    result = await session.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.user),
            selectinload(Project.order).selectinload(Order.tariff),
            selectinload(Project.competitor_numbers),
            selectinload(Project.deliveries),
            selectinload(Project.activity_logs),
        )
    )
    return result.scalar_one_or_none()


async def list_projects(
    session: AsyncSession,
    *,
    q: str = "",
    status: str = "",
    date_from: str = "",
    date_to: str = "",
) -> list[Project]:
    stmt = (
        select(Project)
        .options(
            selectinload(Project.user),
            selectinload(Project.order).selectinload(Order.tariff),
        )
        .order_by(Project.created_at.desc())
    )
    if q:
        q_clean = q.strip().lstrip("@")
        if q_clean.isdigit():
            stmt = stmt.join(User).where(
                or_(
                    User.telegram_id == int(q_clean),
                    Project.project_name.ilike(f"%{q}%"),
                )
            )
        else:
            stmt = stmt.join(User).where(
                or_(
                    Project.project_name.ilike(f"%{q}%"),
                    User.username.ilike(f"%{q_clean}%"),
                    User.first_name.ilike(f"%{q}%"),
                )
            )
    if status:
        stmt = stmt.where(Project.status == status)
    if date_from:
        try:
            dt = datetime.strptime(date_from, "%Y-%m-%d")
            stmt = stmt.where(Project.created_at >= dt)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d")
            stmt = stmt.where(Project.created_at <= dt)
        except ValueError:
            pass

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_order_price(session: AsyncSession, order: Order) -> int:
    result = await session.execute(
        select(Payment.amount)
        .where(
            Payment.order_id == order.id,
            Payment.status == PaymentStatus.PAID.value,
        )
        .limit(1)
    )
    amount = result.scalar_one_or_none()
    if amount is not None:
        return amount
    tariff = await session.get(Tariff, order.tariff_id)
    return tariff.price if tariff else 0


def format_project_price(price: int) -> str:
    return format_price(price)


async def delete_project(session: AsyncSession, project_id: int) -> bool:
    project = await session.get(Project, project_id)
    if not project:
        return False

    order_id = project.order_id
    user_id = project.user_id

    try:
        cleanup_sql = [
            """
            DELETE FROM delivered_contacts
            WHERE order_id = :order_id
               OR delivery_id IN (SELECT id FROM deliveries WHERE project_id = :pid)
            """,
            """
            DELETE FROM delivered_contacts
            WHERE delivery_id IN (SELECT id FROM contact_deliveries WHERE order_id = :order_id)
            """,
            "DELETE FROM client_activity_log WHERE project_id = :pid",
            "DELETE FROM deliveries WHERE project_id = :pid",
            "DELETE FROM competitor_numbers WHERE project_id = :pid",
            "DELETE FROM payments WHERE order_id = :order_id",
            "DELETE FROM contact_deliveries WHERE order_id = :order_id",
            "DELETE FROM projects WHERE id = :pid",
            "DELETE FROM orders WHERE id = :order_id",
        ]
        params = {"pid": project_id, "order_id": order_id}
        for sql in cleanup_sql:
            try:
                await session.execute(text(sql), params)
            except Exception as exc:
                if "does not exist" not in str(exc).lower():
                    raise

        from services.user_service import refresh_user_status

        await refresh_user_status(session, user_id)
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return True
