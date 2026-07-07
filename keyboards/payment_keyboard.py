from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.start_keyboard import CB_BACK
from services.tariff_service import TariffInfo

CB_TARIFF_PREFIX = "tariff:"
CB_PAY_PREFIX = "pay_tariff:"
CB_PROMO_PREFIX = "promo_tariff:"
CB_MOCK_PAY_PREFIX = "mock_pay:"


def tariffs_keyboard(tariffs: list[TariffInfo]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{t.name} — {t.price:,} ₽".replace(",", " "),
                callback_data=f"{CB_TARIFF_PREFIX}{t.id}",
            )
        ]
        for t in tariffs
    ]
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data=CB_BACK)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def checkout_keyboard(tariff_id: int, price: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", callback_data=f"{CB_PAY_PREFIX}{tariff_id}")],
        [InlineKeyboardButton(text="🎟 Промокод", callback_data=f"{CB_PROMO_PREFIX}{tariff_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=CB_BACK)],
    ])


def payment_keyboard(link) -> InlineKeyboardMarkup:
    """Клавиатура после создания платежа — только реальный URL ЮKassa или тест."""
    if link.is_mock or not link.confirmation_url:
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧪 Тест: активировать без оплаты",
                    callback_data=f"{CB_MOCK_PAY_PREFIX}{link.payment_db_id}",
                )
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data=CB_BACK)],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Перейти к оплате", url=link.confirmation_url)],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=CB_BACK)],
    ])
