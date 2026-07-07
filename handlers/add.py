from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from config.settings import settings
from db.database import async_session
from services.lead_service import add_leads
from services.user_service import get_user, is_active, remaining
from utils.logger import get_logger
from utils.phone import RateLimiter, extract_phones

logger = get_logger(__name__)
router = Router()

rate_limiter = RateLimiter(
    max_calls=settings.add_rate_limit,
    window_seconds=settings.add_rate_window,
)


class AddLeadsState(StatesGroup):
    waiting_for_phones = State()


@router.message(Command("add"))
@router.message(F.text == "📱 Добавить номера")
async def cmd_add(message: Message, state: FSMContext) -> None:
    if not rate_limiter.is_allowed(message.from_user.id):
        wait = rate_limiter.seconds_until_reset(message.from_user.id)
        await message.answer(
            f"⏳ Слишком много запросов. Подождите {wait} сек."
        )
        return

    async with async_session() as session:
        user = await get_user(session, message.from_user.id)

    if not user:
        await message.answer("Сначала нажмите /start")
        return

    if not is_active(user):
        await message.answer(
            "❌ Загрузка номеров доступна только после оплаты пакета.\n"
            "Нажмите /start и выберите «Купить пакет»."
        )
        return

    if remaining(user) <= 0:
        await message.answer(
            "❌ Лимит пакета исчерпан. Обновите тариф.\n"
            "Нажмите /start → Купить пакет."
        )
        return

    await state.set_state(AddLeadsState.waiting_for_phones)
    await message.answer(
        f"📱 Отправьте список телефонов (по одному на строку или через запятую).\n\n"
        f"Осталось слотов: {remaining(user):,}".replace(",", " ")
    )


@router.message(AddLeadsState.waiting_for_phones)
async def process_phones(message: Message, state: FSMContext) -> None:
    if not rate_limiter.is_allowed(message.from_user.id):
        wait = rate_limiter.seconds_until_reset(message.from_user.id)
        await message.answer(f"⏳ Слишком много запросов. Подождите {wait} сек.")
        return

    phones = extract_phones(message.text or "")
    if not phones:
        await message.answer(
            "Не найдено валидных номеров. Формат: +79991234567 или 89991234567"
        )
        return

    async with async_session() as session:
        user = await get_user(session, message.from_user.id)
        if not user or not is_active(user):
            await state.clear()
            await message.answer("❌ Пакет не активен. Оплатите тариф через /start")
            return

        if remaining(user) <= 0:
            await state.clear()
            await message.answer("❌ Лимит пакета исчерпан. Обновите тариф.")
            return

        result = await add_leads(session, user, phones)
        await session.refresh(user)

    lines = [
        f"✅ Сохранено: {result.saved}",
    ]
    if result.duplicates:
        lines.append(f"⚠️ Дубликаты пропущены: {result.duplicates}")
    if result.skipped_limit:
        lines.append(f"🚫 Не вошло (лимит): {result.skipped_limit}")

    lines.append(
        f"\nИспользовано: {user.used:,}/{user.limit:,}".replace(",", " ")
    )

    if remaining(user) <= 0:
        lines.append("\n❌ Лимит пакета исчерпан. Обновите тариф.")

    await message.answer("\n".join(lines))
    await state.clear()

    logger.info(
        "/add completed: user_id=%s saved=%s duplicates=%s",
        message.from_user.id,
        result.saved,
        result.duplicates,
    )
