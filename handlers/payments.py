from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from database.database import async_session
from keyboards.payment_keyboard import (
    CB_MOCK_PAY_PREFIX,
    CB_PAY_PREFIX,
    CB_PROMO_PREFIX,
    CB_TARIFF_PREFIX,
    checkout_keyboard,
    payment_keyboard,
)
from keyboards.start_keyboard import active_user_keyboard, back_keyboard
from payments.yookassa import confirm_mock_payment, create_payment
from services.promo_service import verify_test_promo
from services.tariff_service import get_tariff
from services.telegram_notify import notify_payment_success
from services.user_service import get_user_by_telegram_id
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()

PROMO_PRICE = 1


class PromoState(StatesGroup):
    waiting_code = State()


async def _bot_username(bot) -> str:
    me = await bot.get_me()
    return me.username or "Pesdata_bot"


def _checkout_text(tariff, price: int, promo_applied: bool = False, *, mock: bool = False) -> str:
    promo_line = "\n🎟 <b>Промокод применён — 1 ₽</b>\n" if promo_applied else ""
    if mock:
        pay_hint = (
            "⚠️ <b>ЮKassa не настроена</b> — реальная оплата недоступна.\n"
            "Для теста нажмите «Тест: активировать без оплаты».\n\n"
            "Администратор: добавьте YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY в Vercel."
        )
    else:
        pay_hint = (
            "Нажмите «Перейти к оплате» — откроется страница ЮKassa.\n"
            "После оплаты бот пришлёт подтверждение автоматически."
        )
    return (
        f"💳 <b>Оплата пакета «{tariff.name}»</b>{promo_line}\n\n"
        f"Сумма: <b>{price:,} ₽</b>\n".replace(",", " ")
        + f"Контактов: <b>{tariff.contact_limit:,}</b>\n\n".replace(",", " ")
        + pay_hint
    )


@router.callback_query(F.data.startswith(CB_TARIFF_PREFIX))
async def cb_select_tariff(callback: CallbackQuery) -> None:
    tariff_id = int(callback.data.removeprefix(CB_TARIFF_PREFIX))

    async with async_session() as session:
        tariff = await get_tariff(session, tariff_id)
        if not tariff:
            await callback.answer("Тариф не найден", show_alert=True)
            return

    await callback.message.edit_text(
        _checkout_text(tariff, tariff.price),
        reply_markup=checkout_keyboard(tariff_id, tariff.price),
    )
    await callback.answer()


@router.callback_query(F.data.startswith(CB_PAY_PREFIX))
async def cb_pay_tariff(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    tariff_id = int(callback.data.removeprefix(CB_PAY_PREFIX))
    await _start_payment(callback, tariff_id, amount=None, promo_applied=False)


@router.callback_query(F.data.startswith(CB_PROMO_PREFIX))
async def cb_promo_tariff(callback: CallbackQuery, state: FSMContext) -> None:
    tariff_id = int(callback.data.removeprefix(CB_PROMO_PREFIX))
    await state.set_state(PromoState.waiting_code)
    await state.update_data(tariff_id=tariff_id)
    await callback.message.edit_text(
        "🎟 <b>Промокод</b>\n\nВведите промокод одним сообщением:",
        reply_markup=back_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith(CB_MOCK_PAY_PREFIX))
async def cb_mock_pay(callback: CallbackQuery) -> None:
    payment_id = int(callback.data.removeprefix(CB_MOCK_PAY_PREFIX))
    async with async_session() as session:
        result = await confirm_mock_payment(session, payment_id)
    if not result:
        await callback.answer("Платёж не найден или уже обработан", show_alert=True)
        return
    user, order = result
    await notify_payment_success(user.telegram_id, order.tariff.name, order.contact_limit)
    await callback.message.edit_text(
        f"✅ Тестовая активация!\nПакет «{order.tariff.name}» — {order.contact_limit} контактов.",
        reply_markup=active_user_keyboard(),
    )

    await callback.answer("Пакет активирован")


@router.message(PromoState.waiting_code, F.text)
async def process_promo_code(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    tariff_id = data.get("tariff_id")
    if not tariff_id:
        await state.clear()
        await message.answer("⚠️ Сессия истекла. Нажмите /start")
        return

    if not verify_test_promo(message.text or ""):
        await message.answer("❌ Неверный промокод. Попробуйте ещё раз или нажмите «Назад».")
        return

    await state.clear()
    await message.answer("✅ Промокод принят! Создаю платёж на 1 ₽…")

    async with async_session() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        tariff = await get_tariff(session, tariff_id)
        if not user or not tariff:
            await message.answer("⚠️ Ошибка. Нажмите /start")
            return
        try:
            username = await _bot_username(message.bot)
            link = await create_payment(
                session, user, tariff, username, amount=PROMO_PRICE
            )
        except ValueError as exc:
            await message.answer(f"❌ {exc}")
            return
        except Exception:
            logger.exception("Promo payment failed")
            await message.answer("❌ Ошибка создания платежа")
            return

    await message.answer(
        _checkout_text(tariff, PROMO_PRICE, promo_applied=True, mock=link.is_mock),
        reply_markup=payment_keyboard(link),
    )


async def _start_payment(
    callback: CallbackQuery,
    tariff_id: int,
    amount: int | None,
    promo_applied: bool,
) -> None:
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
            username = await _bot_username(callback.bot)
            link = await create_payment(session, user, tariff, username, amount=amount)
        except ValueError as exc:
            await callback.answer(str(exc), show_alert=True)
            return
        except Exception:
            logger.exception("Payment creation failed")
            await callback.answer("Ошибка создания платежа", show_alert=True)
            return

    price = amount if amount is not None else tariff.price
    await callback.message.edit_text(
        _checkout_text(tariff, price, promo_applied=promo_applied, mock=link.is_mock),
        reply_markup=payment_keyboard(link),
    )
    await callback.answer()


@router.message(CommandStart(deep_link=True))
async def cmd_start_deeplink(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return

    if args[1] == "payment_ok":
        await message.answer(
            "✅ Спасибо! Если оплата прошла — бот пришлёт подтверждение в течение минуты.\n"
            "Если сообщения нет — напишите /start"
        )
