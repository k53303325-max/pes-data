from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.menu_keyboard import CB_MAIN_PACKAGES

CB_CHOOSE_PACKAGE = "choose_tariff"
CB_HOW_IT_WORKS = "how_it_works"
CB_FAQ = "faq"
CB_BACK = "back"
CB_MY_PACKAGE = "profile"
CB_ADD_COMPETITORS = "add_competitors"
CB_BUY_NEW = "buy_package"


def welcome_keyboard() -> InlineKeyboardMarkup:
    from keyboards.menu_keyboard import main_menu_keyboard

    return main_menu_keyboard()


def choose_package_keyboard() -> InlineKeyboardMarkup:
    from keyboards.menu_keyboard import back_to_main_keyboard

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Пакеты и цены", callback_data=CB_MAIN_PACKAGES)],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=CB_BACK)],
    ])


def active_user_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Мой пакет", callback_data=CB_MY_PACKAGE)],
        [InlineKeyboardButton(text="📱 Добавить номера конкурентов", callback_data=CB_ADD_COMPETITORS)],
        [InlineKeyboardButton(text="💰 Пакеты и цены", callback_data=CB_MAIN_PACKAGES)],
    ])


def finished_user_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Мой пакет", callback_data=CB_MY_PACKAGE)],
        [InlineKeyboardButton(text="💰 Пакеты и цены", callback_data=CB_MAIN_PACKAGES)],
    ])


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=CB_BACK)],
    ])
