from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
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
    competitors: Mapped[list["Competitor"]] = relationship(back_populates="user")
    deliveries: Mapped[list["ContactDelivery"]] = relationship(back_populates="user")


class Tariff(Base):
    __tablename__ = "tariffs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[int] = mapped_column(Integer)
    contact_limit: Mapped[int] = mapped_column(Integer)

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
    deliveries: Mapped[list["ContactDelivery"]] = relationship(back_populates="order")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id"), nullable=True)
    tariff_id: Mapped[int] = mapped_column(ForeignKey("tariffs.id"))
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default=PaymentStatus.PENDING.value, index=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="payments")
    order: Mapped[Optional["Order"]] = relationship(back_populates="payments")
    tariff: Mapped["Tariff"] = relationship(back_populates="payments")


class Competitor(Base):
    __tablename__ = "competitors"
    __table_args__ = (UniqueConstraint("user_id", "phone", name="uq_user_competitor_phone"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    phone: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="competitors")


class ContactDelivery(Base):
    __tablename__ = "contact_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    count: Mapped[int] = mapped_column(Integer)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="deliveries")
    order: Mapped["Order"] = relationship(back_populates="deliveries")
    contacts: Mapped[list["DeliveredContact"]] = relationship(back_populates="delivery")


class DeliveredContact(Base):
    __tablename__ = "delivered_contacts"
    __table_args__ = (UniqueConstraint("order_id", "phone", name="uq_order_contact_phone"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    delivery_id: Mapped[int] = mapped_column(ForeignKey("contact_deliveries.id"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    phone: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    delivery: Mapped["ContactDelivery"] = relationship(back_populates="contacts")
