from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from database.database import async_session
from keyboards.payment_keyboard import CB_TARIFF_PREFIX, pay_keyboard
from payments.yookassa import confirm_mock_payment, create_payment
from services.tariff_service import get_tariff
from services.telegram_notify import notify_payment_success
from services.user_service import get_user_by_telegram_id
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()


@router.callback_query(F.data.startswith(CB_TARIFF_PREFIX))
async def cb_select_tariff(callback: CallbackQuery) -> None:
    tariff_id = int(callback.data.removeprefix(CB_TARIFF_PREFIX))

    async with async_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Нажмите /start", show_alert=True)
            return

        tariff = await get_tariff(session, tariff_id)
        if not tariff:
            await callback.answer("Тариф не найден", show_alert=True)
            return

        try:
            me = await callback.bot.get_me()
            bot_username = me.username or "Pesdata_bot"
            link = await create_payment(session, user, tariff, bot_username)
        except ValueError as exc:
            await callback.answer(str(exc), show_alert=True)
            return
        except Exception as exc:
            logger.exception("Payment creation failed")
            await callback.answer("Ошибка создания платежа. Попробуйте позже.", show_alert=True)
            return

    text = (
        f"💳 <b>Оплата пакета «{tariff.name}»</b>\n\n"
        f"Сумма: <b>{tariff.price:,} ₽</b>\n".replace(",", " ")
        + f"Контактов: <b>{tariff.contact_limit:,}</b>\n\n".replace(",", " ")
        + "Нажмите «Оплатить» — откроется безопасная страница ЮKassa.\n"
        "После оплаты бот пришлёт подтверждение автоматически."
    )
    await callback.message.edit_text(text, reply_markup=pay_keyboard(link.confirmation_url))
    await callback.answer()


@router.message(CommandStart(deep_link=True))
async def cmd_start_deeplink(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].startswith("pay_"):
        return

    try:
        payment_id = int(args[1].removeprefix("pay_"))
    except ValueError:
        return

    async with async_session() as session:
        result = await confirm_mock_payment(session, payment_id)

    if not result:
        await message.answer("⚠️ Платёж не найден или уже обработан.")
        return

    user, order = result
    await notify_payment_success(user.telegram_id, order.tariff.name, order.contact_limit)
