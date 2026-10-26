from __future__ import annotations

from dataclasses import dataclass

from config.settings import settings
from services.tariff_service import format_contact_limit, format_price

MAX_CONTACTS = 42_000
MIN_CONTACTS = 1

# (макс. количество в тарифе, цена за контакт ₽, id тарифа в БД)
PRICING_TIERS: tuple[tuple[int, int, int], ...] = (
    (100, 120, 1),
    (1_000, 80, 2),
    (3_000, 60, 3),
    (9_000, 40, 4),
    (42_000, 20, 5),
)


@dataclass(frozen=True)
class PurchaseQuote:
    contact_limit: int
    price_per_contact: int
    total_price: int
    tier_tariff_id: int
    tier_label: str


def parse_contact_quantity(text: str) -> int:
    cleaned = "".join(ch for ch in (text or "").strip() if ch.isdigit())
    if not cleaned:
        raise ValueError("Укажите количество контактов числом, например: 500")
    quantity = int(cleaned)
    if quantity < MIN_CONTACTS:
        raise ValueError(f"Минимум {MIN_CONTACTS} контакт")
    if quantity > MAX_CONTACTS:
        raise ValueError(f"Максимум {format_contact_limit(MAX_CONTACTS)} контактов")
    return quantity


def quote_for_quantity(quantity: int) -> PurchaseQuote:
    for max_qty, price_per, tier_id in PRICING_TIERS:
        if quantity <= max_qty:
            return PurchaseQuote(
                contact_limit=quantity,
                price_per_contact=price_per,
                total_price=quantity * price_per,
                tier_tariff_id=tier_id,
                tier_label=f"до {format_contact_limit(max_qty)}",
            )
    raise ValueError(f"Максимум {format_contact_limit(MAX_CONTACTS)} контактов")


def format_pricing_table() -> str:
    lines = ["<b>Цена за контакт:</b>", ""]
    for max_qty, price_per, _ in PRICING_TIERS:
        lines.append(
            f"• до {format_contact_limit(max_qty)} контактов — {format_price(price_per)}/контакт"
        )
    return "\n".join(lines)


def admin_contact_handle() -> str:
    username = (settings.admin_username or "").strip().lstrip("@")
    if username:
        return f"@{username}"
    return "администратору (контакт в описании профиля бота)"


def format_purchase_intro_text() -> str:
    return (
        "🐶 <b>Купить контакты</b>\n\n"
        "Вы оплачиваете нужное количество новых контактов. "
        "После оплаты добавьте номера конкурентов — мы будем присылать "
        "новые контакты по мере их появления.\n\n"
        f"{format_pricing_table()}\n\n"
        f"🏢 <b>Юридическое лицо:</b>\n"
        f"Для оплаты по счёту обратитесь к {admin_contact_handle()} "
        f"(контакт указан в описании профиля бота).\n\n"
        f"✏️ <b>Напишите, сколько контактов хотите купить</b> "
        f"(от {MIN_CONTACTS} до {format_contact_limit(MAX_CONTACTS)}):"
    )


def format_purchase_confirm_text(quote: PurchaseQuote) -> str:
    limit = format_contact_limit(quote.contact_limit)
    return (
        "🐶 <b>Подтверждение заказа</b>\n\n"
        f"<b>Количество:</b> {limit} контактов\n"
        f"<b>Тариф:</b> {quote.tier_label} · {format_price(quote.price_per_contact)}/контакт\n"
        f"<b>К оплате:</b> {format_price(quote.total_price)}\n\n"
        "После оплаты укажите название проекта и добавьте номера конкурентов."
    )


def order_package_label(contact_limit: int) -> str:
    return f"{format_contact_limit(contact_limit)} контактов"
