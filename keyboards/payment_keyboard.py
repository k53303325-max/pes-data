from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.start_keyboard import CB_BACK
from services.tariff_service import TariffInfo

CB_TARIFF_PREFIX = "tariff:"
CB_PAY_PREFIX = "pay_tariff:"
CB_PROMO_PREFIX = "promo_tariff:"


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


def pay_keyboard(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Перейти к оплате", url=url)],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=CB_BACK)],
    ])
