from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.payment_keyboard import CB_MOCK_PAY_PREFIX, promo_button_row
from keyboards.start_keyboard import CB_BACK
from payments.yookassa import PaymentLink, mock_payment_allowed
from services.tariff_service import format_price

CB_CHOOSE_TARIFF = "choose_tariff"
CB_TARIFF_DETAILS = "tariff_details:"
CB_CREATE_ORDER = "create_order:"
CB_BACK_TO_TARIFFS = "back_to_tariffs"


def purchase_confirm_keyboard(
    tier_tariff_id: int,
    link: PaymentLink | None = None,
) -> InlineKeyboardMarkup:
    if link and link.confirmation_url and not link.is_mock:
        pay_btn = InlineKeyboardButton(
            text=f"💳 Оплатить · {format_price(link.amount)}",
            url=link.confirmation_url,
        )
    elif link and link.is_mock and mock_payment_allowed():
        pay_btn = InlineKeyboardButton(
            text="🧪 Тест: активировать",
            callback_data=f"{CB_MOCK_PAY_PREFIX}{link.payment_db_id}",
        )
    else:
        pay_btn = InlineKeyboardButton(
            text="💳 Оплатить",
            callback_data=f"{CB_CREATE_ORDER}{tier_tariff_id}",
        )

    return InlineKeyboardMarkup(inline_keyboard=[
        [pay_btn],
        promo_button_row(tier_tariff_id),
        [InlineKeyboardButton(text="✏️ Изменить количество", callback_data=CB_BACK_TO_TARIFFS)],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=CB_BACK)],
    ])


# Обратная совместимость (админка / старые импорты)
def tariff_confirm_keyboard(tier_tariff_id: int, link: PaymentLink | None = None):
    return purchase_confirm_keyboard(tier_tariff_id, link)


def tariffs_list_keyboard(*_args, **_kwargs) -> InlineKeyboardMarkup:
    from keyboards.start_keyboard import back_keyboard

    return back_keyboard()
