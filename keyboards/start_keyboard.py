from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

CB_CHOOSE_PACKAGE = "choose_package"
CB_HOW_IT_WORKS = "how_it_works"
CB_FAQ = "faq"
CB_BACK = "back"
CB_MY_PACKAGE = "my_package"
CB_ADD_COMPETITORS = "add_competitors"
CB_BUY_NEW = "buy_new_package"


def welcome_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Выбрать пакет", callback_data=CB_CHOOSE_PACKAGE)],
        [InlineKeyboardButton(text="📖 Как работает", callback_data=CB_HOW_IT_WORKS)],
        [InlineKeyboardButton(text="❓ FAQ", callback_data=CB_FAQ)],
    ])


def choose_package_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Выбрать пакет", callback_data=CB_CHOOSE_PACKAGE)],
    ])


def active_user_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Мой пакет", callback_data=CB_MY_PACKAGE)],
        [InlineKeyboardButton(text="📱 Добавить конкурентов", callback_data=CB_ADD_COMPETITORS)],
        [InlineKeyboardButton(text="💰 Купить новый пакет", callback_data=CB_BUY_NEW)],
    ])


def finished_user_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Купить новый пакет", callback_data=CB_BUY_NEW)],
    ])


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=CB_BACK)],
    ])
