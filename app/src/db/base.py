from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Callable, Generic, TypeVar
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeMeta

T = TypeVar("T", bound=DeclarativeMeta)


class SessionFactory:
    def __init__(self, session_factory: Callable[[], AsyncSession]):
        self._session_factory = session_factory

    @asynccontextmanager
    async def create_session(self) -> AsyncIterator[AsyncSession]:
        async with self._session_factory() as session:
            yield session


class CRUDRepository(Generic[T]):
    def __init__(self, model: type[T]):
        self._model = model

    def _base_query(self):
        return select(self._model)

    async def get(self, session: AsyncSession, obj_id: UUID) -> T | None:
        result = await session.execute(
            self._base_query().where(self._model.id == obj_id)
        )
        return result.scalar_one_or_none()

    async def get_multi(self, session: AsyncSession) -> list[T]:
        result = await session.execute(self._base_query())
        return result.scalars().all()

    async def create(self, session: AsyncSession, entity: T) -> T:
        session.add(entity)
        await session.flush()
        await session.refresh(entity)
        return entity

    async def update(self, session: AsyncSession, db_obj: T, update_data: dict) -> T:
        obj_data = jsonable_encoder(db_obj)
        for field, value in update_data.items():
            if field in obj_data:
                setattr(db_obj, field, value)
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj

    async def remove(self, session: AsyncSession, db_obj: T) -> T:
        await session.delete(db_obj)
        await session.flush()
        return db_obj
