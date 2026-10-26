from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.profile_keyboard import CB_PROFILE

CB_ADD_COMPETITORS = "add_competitors"
CB_ADD_MORE = "add_more_competitors"


def project_created_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📱 Добавить номера конкурентов",
                callback_data=CB_ADD_COMPETITORS,
            )
        ],
        [InlineKeyboardButton(text="📊 Мой пакет", callback_data=CB_PROFILE)],
    ])


def payment_success_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Мой пакет", callback_data=CB_PROFILE)],
    ])


def after_save_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить еще номера", callback_data=CB_ADD_MORE)],
        [InlineKeyboardButton(text="📊 Мой пакет", callback_data=CB_PROFILE)],
    ])
