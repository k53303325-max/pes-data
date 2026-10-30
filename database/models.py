from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserStatus(str, Enum):
    NEW = "new"
    ACTIVE = "active"
    FINISHED = "finished"
    BLOCKED = "blocked"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELED = "canceled"


class OrderStatus(str, Enum):
    CREATED = "created"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class CompetitorStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DELETED = "deleted"


class DeliveryType(str, Enum):
    MESSAGE = "message"
    FILE = "file"


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"


class ActivityType(str, Enum):
    PAYMENT = "payment"
    PROJECT_CREATED = "project_created"
    COMPETITORS_ADDED = "competitors_added"
    CONTACTS_SENT = "contacts_sent"


class ChatDirection(str, Enum):
    IN = "in"
    OUT = "out"


class TelegramOutboxStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class BriefRequestStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    NOTIFY_FAILED = "notify_failed"


class TrialEntitlementStatus(str, Enum):
    REQUESTED = "requested"
    CHECKING = "checking"
    RESERVED = "reserved"
    ISSUING = "issuing"
    COMPLETED = "completed"
    RELEASED = "released"


class BankPaymentStatus(str, Enum):
    NEW = "new"
    AWAITING_PAYMENT = "awaiting_payment"
    INVOICED = "invoiced"
    PAID = "paid"
    CANCELED = "canceled"


class ReferralCommissionStatus(str, Enum):
    PENDING = "pending"
    ELIGIBLE = "eligible"
    PAID_OUT = "paid_out"
    REVERSED = "reversed"
    REVIEW = "review"


class AdminNotification(Base):
    __tablename__ = "admin_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    new_registration_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    new_project_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    payment_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    competitor_added_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    package_completed_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    error_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=UserStatus.NEW.value, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    orders: Mapped[list["Order"]] = relationship(back_populates="user")
    payments: Mapped[list["Payment"]] = relationship(back_populates="user")
    competitor_numbers: Mapped[list["CompetitorNumber"]] = relationship(back_populates="user")
    deliveries: Mapped[list["Delivery"]] = relationship(back_populates="user")
    projects: Mapped[list["Project"]] = relationship(back_populates="user")
    activity_logs: Mapped[list["ClientActivityLog"]] = relationship(back_populates="user")
    chat_messages: Mapped[list["BotMessage"]] = relationship(back_populates="user")
    niche_briefs: Mapped[list["NicheBriefRequest"]] = relationship(back_populates="user")
    trial_entitlements: Mapped[list["TrialEntitlement"]] = relationship(back_populates="user")
    bank_payment_requests: Mapped[list["BankPaymentRequest"]] = relationship(back_populates="user")
    start_source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    referral_code: Mapped[Optional[str]] = mapped_column(String(32), unique=True, nullable=True, index=True)
    referred_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    referred_by: Mapped[Optional["User"]] = relationship(
        remote_side="User.id",
        foreign_keys=[referred_by_user_id],
        back_populates="referrals",
    )
    referrals: Mapped[list["User"]] = relationship(
        back_populates="referred_by",
        foreign_keys=[referred_by_user_id],
    )
    partner_agreed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    partner_commissions: Mapped[list["ReferralCommission"]] = relationship(
        back_populates="partner",
        foreign_keys="ReferralCommission.partner_user_id",
    )


class Tariff(Base):
    __tablename__ = "tariffs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    emoji: Mapped[str] = mapped_column(String(10), default="")
    price: Mapped[int] = mapped_column(Integer)
    contact_limit: Mapped[int] = mapped_column(Integer)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    orders: Mapped[list["Order"]] = relationship(back_populates="tariff")
    payments: Mapped[list["Payment"]] = relationship(back_populates="tariff")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    tariff_id: Mapped[int] = mapped_column(ForeignKey("tariffs.id"))
    contact_limit: Mapped[int] = mapped_column(Integer)
    received: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default=OrderStatus.CREATED.value, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="orders")
    tariff: Mapped["Tariff"] = relationship(back_populates="orders")
    payments: Mapped[list["Payment"]] = relationship(back_populates="order")
    deliveries: Mapped[list["Delivery"]] = relationship(back_populates="order")
    project: Mapped[Optional["Project"]] = relationship(back_populates="order", uselist=False)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id"), nullable=True)
    tariff_id: Mapped[int] = mapped_column(ForeignKey("tariffs.id"))
    contact_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default=PaymentStatus.PENDING.value, index=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="payments")
    order: Mapped[Optional["Order"]] = relationship(back_populates="payments")
    tariff: Mapped["Tariff"] = relationship(back_populates="payments")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True, index=True)
    project_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default=ProjectStatus.ACTIVE.value, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="projects")
    order: Mapped["Order"] = relationship(back_populates="project")
    competitor_numbers: Mapped[list["CompetitorNumber"]] = relationship(back_populates="project")
    deliveries: Mapped[list["Delivery"]] = relationship(back_populates="project")
    activity_logs: Mapped[list["ClientActivityLog"]] = relationship(back_populates="project")


class ClientActivityLog(Base):
    __tablename__ = "client_activity_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    action_type: Mapped[str] = mapped_column(String(50), index=True)
    description: Mapped[str] = mapped_column(Text)
    contacts_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    admin_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="activity_logs")
    user: Mapped["User"] = relationship(back_populates="activity_logs")


class NicheBriefRequest(Base):
    __tablename__ = "niche_brief_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    request_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default=BriefRequestStatus.DRAFT.value, index=True)
    is_trial: Mapped[bool] = mapped_column(Boolean, default=False)
    package_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    business_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sales_team: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    competitor_phones_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    competitor_phones_normalized: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    competitors_need_help: Mapped[bool] = mapped_column(Boolean, default=False)
    inn: Mapped[Optional[str]] = mapped_column(String(12), nullable=True, index=True)
    inn_manual_review: Mapped[bool] = mapped_column(Boolean, default=False)
    inn_manual_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    admin_notified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="niche_briefs")


class TrialEntitlement(Base):
    __tablename__ = "trial_entitlements"
    __table_args__ = (UniqueConstraint("inn", name="uq_trial_entitlement_inn"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    inn: Mapped[str] = mapped_column(String(12))
    status: Mapped[str] = mapped_column(
        String(20), default=TrialEntitlementStatus.REQUESTED.value, index=True
    )
    brief_request_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("niche_brief_requests.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="trial_entitlements")


class FsmStorageEntry(Base):
    __tablename__ = "fsm_storage"
    __table_args__ = (
        UniqueConstraint(
            "bot_id",
            "chat_id",
            "user_id",
            "destiny",
            name="uq_fsm_storage_key",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bot_id: Mapped[int] = mapped_column(BigInteger)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    thread_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    destiny: Mapped[str] = mapped_column(String(32), default="default")
    state: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    data_json: Mapped[str] = mapped_column(Text, default="{}")


class ReferralCommission(Base):
    __tablename__ = "referral_commissions"
    __table_args__ = (UniqueConstraint("payment_id", name="uq_referral_commission_payment"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    partner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    referee_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    paid_amount: Mapped[int] = mapped_column(Integer)
    commission_amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(20), default=ReferralCommissionStatus.PENDING.value, index=True
    )
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    eligible_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    admin_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    partner: Mapped["User"] = relationship(
        back_populates="partner_commissions",
        foreign_keys=[partner_user_id],
    )


class BankPaymentRequest(Base):
    __tablename__ = "bank_payment_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    payment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("payments.id"), nullable=True, unique=True)
    package_code: Mapped[str] = mapped_column(String(32))
    package_name: Mapped[str] = mapped_column(String(100))
    contact_limit: Mapped[int] = mapped_column(Integer)
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default=BankPaymentStatus.NEW.value, index=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    company_inn: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
    invoice_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    requisites_file_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    requisites_file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    admin_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="bank_payment_requests")


class BotMessage(Base):
    __tablename__ = "bot_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    direction: Mapped[str] = mapped_column(String(10), index=True)
    message_type: Mapped[str] = mapped_column(String(30), default="text")
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    telegram_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    user: Mapped[Optional["User"]] = relationship(back_populates="chat_messages")


class TelegramOutbox(Base):
    """Сообщения из админки ONREZA → отправляет poller на Amvera (нет доступа к Bot API с ONREZA)."""

    __tablename__ = "telegram_outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(100), default="admin.chat")
    status: Mapped[str] = mapped_column(
        String(20), default=TelegramOutboxStatus.PENDING.value, index=True
    )
    error: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_data: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class CompetitorNumber(Base):
    __tablename__ = "competitor_numbers"
    __table_args__ = (UniqueConstraint("user_id", "phone", name="uq_user_competitor_number_phone"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    phone: Mapped[str] = mapped_column(String(11))
    added_by: Mapped[str] = mapped_column(String(100), default="user")
    status: Mapped[str] = mapped_column(
        String(20), default=CompetitorStatus.ACTIVE.value, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="competitor_numbers")
    project: Mapped[Optional["Project"]] = relationship(back_populates="competitor_numbers")


# Обратная совместимость
Competitor = CompetitorNumber


class Delivery(Base):
    __tablename__ = "deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    delivery_type: Mapped[str] = mapped_column(String(20), default=DeliveryType.MESSAGE.value)
    contacts_count: Mapped[int] = mapped_column(Integer)
    contacts_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_data: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    admin_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="deliveries")
    order: Mapped["Order"] = relationship(back_populates="deliveries")
    project: Mapped[Optional["Project"]] = relationship(back_populates="deliveries")
    contacts: Mapped[list["DeliveredContact"]] = relationship(back_populates="delivery")

    @property
    def count(self) -> int:
        return self.contacts_count


# Обратная совместимость
ContactDelivery = Delivery


class DeliveredContact(Base):
    __tablename__ = "delivered_contacts"
    __table_args__ = (UniqueConstraint("order_id", "phone", name="uq_order_contact_phone"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    delivery_id: Mapped[int] = mapped_column(ForeignKey("deliveries.id"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    phone: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    delivery: Mapped["Delivery"] = relationship(back_populates="contacts")
