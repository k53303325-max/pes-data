from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.start_keyboard import CB_BACK
from services.tariff_service import TariffInfo

CB_TARIFF_PREFIX = "tariff:"


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


def pay_keyboard(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url=url)],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=CB_BACK)],
    ])
