from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.menu_keyboard import CB_PKG_DISCUSS, CB_PKG_LIST, CB_PKG_PREFIX
from keyboards.payment_keyboard import CB_MOCK_PAY_PREFIX, CB_PROMO_PKG_PREFIX
from keyboards.start_keyboard import CB_BACK
from payments.yookassa import mock_payment_allowed

CB_PAY_PKG_PREFIX = "pay_pkg:"
CB_BANK_PKG_PREFIX = "bank_pkg:"
CB_PKG_PAY_MENU_PREFIX = "pkg_pay_menu:"


def package_card_actions_keyboard(code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить картой (ЮKassa)", callback_data=f"{CB_PAY_PKG_PREFIX}{code}")],
        [InlineKeyboardButton(text="🏦 Оплата с р/с", callback_data=f"{CB_BANK_PKG_PREFIX}{code}")],
        [InlineKeyboardButton(text="Обсудить этот пакет", callback_data=f"{CB_PKG_DISCUSS}{code}")],
        [InlineKeyboardButton(text="К списку пакетов", callback_data=CB_PKG_LIST)],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")],
    ])


def package_payment_keyboard(link, package_code: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if (link.is_mock or not link.confirmation_url) and mock_payment_allowed():
        rows.append([
            InlineKeyboardButton(
                text="🧪 Тест: активировать без оплаты",
                callback_data=f"{CB_MOCK_PAY_PREFIX}{link.payment_db_id}",
            )
        ])
    elif link.confirmation_url and not link.is_mock:
        rows.append([
            InlineKeyboardButton(text="💳 Перейти к оплате", url=link.confirmation_url),
        ])
    rows.append([
        InlineKeyboardButton(text="🎟 Промокод 100%", callback_data=f"{CB_PROMO_PKG_PREFIX}{package_code}"),
    ])
    rows.append([
        InlineKeyboardButton(text="◀️ К пакету", callback_data=f"{CB_PKG_PREFIX}{package_code}"),
        InlineKeyboardButton(text="◀️ Назад", callback_data=CB_BACK),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
