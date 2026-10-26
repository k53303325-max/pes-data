from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.start_keyboard import CB_ADD_COMPETITORS, CB_BUY_NEW

CB_PROFILE = "profile"
CB_MY_PACKAGE = "profile"
CB_MY_COMPETITORS = "my_competitors"
CB_REFRESH_PROFILE = "refresh_profile"
CB_BUY_PACKAGE = "buy_package"
CB_BACK_TO_PROFILE = "profile"


def cabinet_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Мои конкуренты", callback_data=CB_MY_COMPETITORS)],
        [InlineKeyboardButton(text="➕ Добавить номера", callback_data=CB_ADD_COMPETITORS)],
        [InlineKeyboardButton(text="💰 Купить пакет", callback_data=CB_BUY_PACKAGE)],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data=CB_REFRESH_PROFILE)],
    ])


def completed_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Мои конкуренты", callback_data=CB_MY_COMPETITORS)],
        [InlineKeyboardButton(text="💰 Купить новый пакет", callback_data=CB_BUY_PACKAGE)],
    ])


def no_package_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Купить пакет", callback_data=CB_BUY_PACKAGE)],
    ])


def competitors_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить номера", callback_data=CB_ADD_COMPETITORS)],
        [InlineKeyboardButton(text="⬅ Назад", callback_data=CB_BACK_TO_PROFILE)],
    ])


# Алиасы для совместимости
profile_keyboard = cabinet_keyboard
