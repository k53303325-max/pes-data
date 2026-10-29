from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from services.package_catalog import PACKAGES

CB_MAIN_MENU = "main_menu"
CB_MAIN_TRIAL = "main_trial"
CB_MAIN_NICHE = "main_niche"
CB_MAIN_HOW = "main_how"
CB_MAIN_PACKAGES = "main_packages"
CB_MAIN_FAQ = "main_faq"
CB_MAIN_CONTACT = "main_contact"
CB_MAIN_REFERRAL = "main_referral"

CB_PKG_LIST = "pkg_list"
CB_PKG_PREFIX = "pkg:"
CB_PKG_TRIAL_CARD = "pkg_trial_card"
CB_PKG_TRIAL_START = "pkg_trial_start"
CB_PKG_DISCUSS = "pkg_discuss:"

CB_FAQ_LIST = "faq_list"
CB_FAQ_PREFIX = "faq:"
CB_FAQ_EVAL = "faq_eval"

CB_CONTACT_WRITE = "contact_write"

CB_BRIEF_START = "brief_start"
CB_BRIEF_SALES_PREFIX = "brief_sales:"
CB_BRIEF_COMP_HELP = "brief_comp_help"
CB_BRIEF_INN_NO = "brief_inn_no"
CB_BRIEF_CONFIRM = "brief_confirm"
CB_BRIEF_EDIT = "brief_edit"
CB_BRIEF_EDIT_PREFIX = "brief_edit_field:"
CB_BRIEF_RESUBMIT = "brief_resubmit"


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Получить бесплатный триал", callback_data=CB_MAIN_TRIAL)],
        [InlineKeyboardButton(text="🔍 Проверить мою нишу", callback_data=CB_MAIN_NICHE)],
        [InlineKeyboardButton(text="📖 Как это работает", callback_data=CB_MAIN_HOW)],
        [InlineKeyboardButton(text="💰 Пакеты и цены", callback_data=CB_MAIN_PACKAGES)],
        [InlineKeyboardButton(text="❓ Вопросы и ответы", callback_data=CB_MAIN_FAQ)],
        [InlineKeyboardButton(text="✉️ Связаться с командой", callback_data=CB_MAIN_CONTACT)],
        [InlineKeyboardButton(text="🤝 Партнёрская программа", callback_data=CB_MAIN_REFERRAL)],
    ])


def back_to_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data=CB_MAIN_MENU)],
    ])


def brief_intro_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Начать", callback_data=CB_BRIEF_START)],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data=CB_MAIN_MENU)],
    ])


def brief_sales_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Есть отдел продаж", callback_data=f"{CB_BRIEF_SALES_PREFIX}team")],
        [InlineKeyboardButton(text="Звоню сам", callback_data=f"{CB_BRIEF_SALES_PREFIX}self")],
        [InlineKeyboardButton(text="Пока некому звонить", callback_data=f"{CB_BRIEF_SALES_PREFIX}none")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=CB_BRIEF_EDIT)],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data=CB_MAIN_MENU)],
    ])


def brief_competitors_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Нужна помощь с выбором", callback_data=CB_BRIEF_COMP_HELP)],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=CB_BRIEF_EDIT)],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data=CB_MAIN_MENU)],
    ])


def brief_inn_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Нет ИНН / нужна помощь", callback_data=CB_BRIEF_INN_NO)],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=CB_BRIEF_EDIT)],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data=CB_MAIN_MENU)],
    ])


def brief_summary_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отправить на проверку", callback_data=CB_BRIEF_CONFIRM)],
        [InlineKeyboardButton(text="Изменить ответы", callback_data=CB_BRIEF_EDIT)],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data=CB_MAIN_MENU)],
    ])


def brief_edit_fields_keyboard(*, show_inn: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="Бизнес", callback_data=f"{CB_BRIEF_EDIT_PREFIX}business")],
        [InlineKeyboardButton(text="Кто звонит", callback_data=f"{CB_BRIEF_EDIT_PREFIX}sales")],
        [InlineKeyboardButton(text="Телефоны конкурентов", callback_data=f"{CB_BRIEF_EDIT_PREFIX}phones")],
    ]
    if show_inn:
        rows.append([InlineKeyboardButton(text="ИНН для триала", callback_data=f"{CB_BRIEF_EDIT_PREFIX}inn")])
    rows.append([InlineKeyboardButton(text="◀️ К сводке", callback_data=CB_BRIEF_EDIT)])
    rows.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data=CB_MAIN_MENU)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def brief_success_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Как оценивать контакты", callback_data=CB_FAQ_EVAL)],
        [InlineKeyboardButton(text="✉️ Связаться с командой", callback_data=CB_MAIN_CONTACT)],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data=CB_MAIN_MENU)],
    ])


def brief_failed_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Повторить отправку", callback_data=CB_BRIEF_RESUBMIT)],
        [InlineKeyboardButton(text="✉️ Связаться с командой", callback_data=CB_MAIN_CONTACT)],
    ])


def trial_blocked_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Пакеты и цены", callback_data=CB_MAIN_PACKAGES)],
        [InlineKeyboardButton(text="✉️ Связаться с командой", callback_data=CB_MAIN_CONTACT)],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data=CB_MAIN_MENU)],
    ])


def packages_list_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for pkg in PACKAGES:
        if pkg.is_trial:
            rows.append([
                InlineKeyboardButton(text=pkg.button_label, callback_data=CB_PKG_TRIAL_CARD)
            ])
        else:
            rows.append([
                InlineKeyboardButton(text=pkg.button_label, callback_data=f"{CB_PKG_PREFIX}{pkg.code}")
            ])
    rows.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data=CB_MAIN_MENU)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def trial_card_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Получить триал", callback_data=CB_PKG_TRIAL_START)],
        [InlineKeyboardButton(text="К списку пакетов", callback_data=CB_PKG_LIST)],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data=CB_MAIN_MENU)],
    ])


def package_card_keyboard(code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Обсудить этот пакет", callback_data=f"{CB_PKG_DISCUSS}{code}")],
        [InlineKeyboardButton(text="К списку пакетов", callback_data=CB_PKG_LIST)],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data=CB_MAIN_MENU)],
    ])


def how_it_works_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Проверить мою нишу", callback_data=CB_MAIN_NICHE)],
        [InlineKeyboardButton(text="Как оценивать контакты", callback_data=CB_FAQ_EVAL)],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data=CB_MAIN_MENU)],
    ])


def faq_list_keyboard() -> InlineKeyboardMarkup:
    from services.faq_content import FAQ_TOPICS

    rows = [
        [InlineKeyboardButton(text=title, callback_data=f"{CB_FAQ_PREFIX}{key}")]
        for key, title in FAQ_TOPICS
    ]
    rows.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data=CB_MAIN_MENU)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def faq_answer_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Проверить мою нишу", callback_data=CB_MAIN_NICHE)],
        [InlineKeyboardButton(text="К вопросам", callback_data=CB_FAQ_LIST)],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data=CB_MAIN_MENU)],
    ])


def contact_keyboard(admin_username: str) -> InlineKeyboardMarkup:
    url = f"https://t.me/{admin_username.lstrip('@')}" if admin_username else None
    rows: list[list[InlineKeyboardButton]] = []
    if url:
        rows.append([InlineKeyboardButton(text="Написать команде", url=url)])
    rows.extend([
        [InlineKeyboardButton(text="🔍 Проверить мою нишу", callback_data=CB_MAIN_NICHE)],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data=CB_MAIN_MENU)],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
