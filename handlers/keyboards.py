from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from services.tariff_service import TariffInfo


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Тарифы"), KeyboardButton(text="💳 Купить пакет")],
            [KeyboardButton(text="📱 Добавить номера"), KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True,
    )


def buy_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Купить пакет", callback_data="buy_package")],
        ]
    )


def tariffs_keyboard(tariffs: list[TariffInfo]) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{t.name} — {t.price:,} ₽ ({t.limit:,} шт)".replace(",", " "),
                callback_data=f"tariff:{t.id}",
            )
        ]
        for t in tariffs
    ]
    buttons.append(
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_start")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)
