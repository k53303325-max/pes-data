from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.start_keyboard import CB_ADD_COMPETITORS, CB_BUY_NEW

CB_PROFILE = "profile"
CB_MY_PACKAGE = "profile"
CB_MY_PROJECTS = "my_projects"
CB_MY_COMPETITORS = "my_competitors"  # legacy callback в старых сообщениях
CB_REFRESH_PROFILE = "refresh_profile"
CB_BUY_PACKAGE = "buy_package"
CB_BACK_TO_PROFILE = "back_to_cabinet"


def cabinet_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏢 Мои проекты", callback_data=CB_MY_PROJECTS)],
            [InlineKeyboardButton(text="💰 Купить пакет", callback_data=CB_BUY_PACKAGE)],
            [InlineKeyboardButton(text="🔄 Обновить", callback_data=CB_REFRESH_PROFILE)],
        ]
    )


def completed_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏢 Мои проекты", callback_data=CB_MY_PROJECTS)],
        [InlineKeyboardButton(text="💰 Купить новый пакет", callback_data=CB_BUY_PACKAGE)],
    ])


def no_package_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Купить пакет", callback_data=CB_BUY_PACKAGE)],
    ])


def project_detail_keyboard(*, can_add_numbers: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if can_add_numbers:
        rows.append(
            [InlineKeyboardButton(text="➕ Добавить номера", callback_data=CB_ADD_COMPETITORS)]
        )
    rows.append([InlineKeyboardButton(text="⬅ Назад", callback_data=CB_BACK_TO_PROFILE)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def competitors_keyboard() -> InlineKeyboardMarkup:
    return project_detail_keyboard(can_add_numbers=True)


# Алиасы для совместимости
profile_keyboard = cabinet_keyboard
