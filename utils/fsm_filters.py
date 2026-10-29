from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject
from aiogram.fsm.context import FSMContext


class NoStateFilter(BaseFilter):
    async def __call__(self, _event: TelegramObject, state: FSMContext) -> bool:
        return await state.get_state() is None


class HasStateFilter(BaseFilter):
    async def __call__(self, _event: TelegramObject, state: FSMContext) -> bool:
        return await state.get_state() is not None
