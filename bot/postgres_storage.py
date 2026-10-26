from __future__ import annotations

import json
from typing import Any

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StateType, StorageKey
from sqlalchemy import select

from database.database import async_session
from database.models import FsmStorageEntry


def _state_str(state: StateType) -> str | None:
    if state is None:
        return None
    if isinstance(state, State):
        return state.state
    return str(state)


class PostgresStorage(BaseStorage):
    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        async with async_session() as session:
            row = await self._get_or_create(session, key)
            row.state = _state_str(state)
            await session.commit()

    async def get_state(self, key: StorageKey) -> str | None:
        async with async_session() as session:
            row = await self._get_row(session, key)
            return row.state if row else None

    async def set_data(self, key: StorageKey, data: dict[str, Any]) -> None:
        async with async_session() as session:
            row = await self._get_or_create(session, key)
            row.data_json = json.dumps(data, ensure_ascii=False)
            await session.commit()

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        async with async_session() as session:
            row = await self._get_row(session, key)
            if not row or not row.data_json:
                return {}
            try:
                parsed = json.loads(row.data_json)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}

    async def close(self) -> None:
        return None

    async def _get_row(self, session, key: StorageKey) -> FsmStorageEntry | None:
        result = await session.execute(
            select(FsmStorageEntry).where(
                FsmStorageEntry.bot_id == key.bot_id,
                FsmStorageEntry.chat_id == key.chat_id,
                FsmStorageEntry.user_id == key.user_id,
                FsmStorageEntry.destiny == key.destiny,
            )
        )
        return result.scalar_one_or_none()

    async def _get_or_create(self, session, key: StorageKey) -> FsmStorageEntry:
        row = await self._get_row(session, key)
        if row:
            return row
        row = FsmStorageEntry(
            bot_id=key.bot_id,
            chat_id=key.chat_id,
            user_id=key.user_id,
            thread_id=key.thread_id,
            destiny=key.destiny,
            state=None,
            data_json="{}",
        )
        session.add(row)
        await session.flush()
        return row
