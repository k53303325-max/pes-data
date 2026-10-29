from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.menu_keyboard import CB_MAIN_MENU, CB_MAIN_REFERRAL

CB_REF_LINK = "ref_link"
CB_REF_CABINET = "ref_cabinet"
CB_REF_AGREE = "ref_agree"


def referral_program_keyboard(*, show_agree: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if show_agree:
        rows.append([
            InlineKeyboardButton(
                text="Получить партнёрскую ссылку",
                callback_data=CB_REF_AGREE,
            )
        ])
    else:
        rows.append([
            InlineKeyboardButton(
                text="Получить партнёрскую ссылку",
                callback_data=CB_REF_LINK,
            )
        ])
    rows.append([
        InlineKeyboardButton(text="Кабинет партнёра", callback_data=CB_REF_CABINET),
    ])
    rows.append([
        InlineKeyboardButton(text="В главное меню", callback_data=CB_MAIN_MENU),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def referral_link_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Кабинет партнёра", callback_data=CB_REF_CABINET)],
        [InlineKeyboardButton(text="◀️ К программе", callback_data=CB_MAIN_REFERRAL)],
        [InlineKeyboardButton(text="В главное меню", callback_data=CB_MAIN_MENU)],
    ])

