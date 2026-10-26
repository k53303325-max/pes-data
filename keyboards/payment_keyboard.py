from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.start_keyboard import CB_BACK
from payments.yookassa import mock_payment_allowed

CB_MOCK_PAY_PREFIX = "mock_pay:"
CB_PROMO_PREFIX = "promo_tariff:"
CB_PROMO_PKG_PREFIX = "promo_pkg:"


def payment_keyboard(link) -> InlineKeyboardMarkup:
    if (link.is_mock or not link.confirmation_url) and mock_payment_allowed():
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧪 Тест: активировать без оплаты",
                    callback_data=f"{CB_MOCK_PAY_PREFIX}{link.payment_db_id}",
                )
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data=CB_BACK)],
        ])
    if link.is_mock or not link.confirmation_url:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data=CB_BACK)],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Перейти к оплате", url=link.confirmation_url)],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=CB_BACK)],
    ])


def promo_button_row(tariff_id: int) -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text="🎟 Промокод", callback_data=f"{CB_PROMO_PREFIX}{tariff_id}")]
