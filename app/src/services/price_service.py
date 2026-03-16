from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import CRUDRepository
from src.models.price_model import Price
from src.schemas.price_schema import PriceCreate, PriceResponse, PriceFilter


class PriceRepository(CRUDRepository[Price]):
    """Репозиторий для работы с моделью Price."""

    def __init__(self):
        super().__init__(Price)

    def _ensure_utc_naive(self, date_value: datetime | None):
        """Преобразовать дату в UTC, если она не является UTC."""
        if not date_value:
            return None
        if date_value.tzinfo:
            return date_value.astimezone(timezone.utc).replace(tzinfo=None)
        return date_value

    async def list_by_ticker(
        self,
        session: AsyncSession,
        ticker: str,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: Optional[int] = None,
        sort_desc: bool = True,
    ):
        """Получить список цен для указанного тикера с опциональными фильтрами по дате."""
        query = self._base_query().where(Price.ticker == ticker)
        date_from = self._ensure_utc_naive(date_from)
        date_to = self._ensure_utc_naive(date_to)
        if date_from:
            query = query.where(Price.timestamp >= date_from)
        if date_to:
            query = query.where(Price.timestamp <= date_to)
        order_column = getattr(Price, "timestamp")
        query = query.order_by(order_column.desc() if sort_desc else order_column)
        if limit:
            query = query.limit(limit)
        result = await session.execute(query)
        return result.scalars().all()


@dataclass
class PriceService:
    """Сервис для работы с цеными данными."""

    repository: PriceRepository

    def _to_response(self, price: Price):
        return PriceResponse.model_validate(price)

    async def create_price(self, session: AsyncSession, data: PriceCreate):
        """Создать новую запись цены."""
        price = Price(**data.model_dump())
        created = await self.repository.create(session, price)
        return self._to_response(created)

    async def get_all_prices(self, session: AsyncSession, ticker: str):
        """Получить все цены для тикера."""
        prices = await self.repository.list_by_ticker(session, ticker)
        return [self._to_response(price) for price in prices]

    async def get_latest_price(self, session: AsyncSession, ticker: str):
        """Получить последнюю цену для тикера."""
        prices = await self.repository.list_by_ticker(session, ticker, limit=1)
        if prices:
            return self._to_response(prices[0])
        return None

    async def get_filtered_prices(
        self, session: AsyncSession, filter_data: PriceFilter
    ):
        """Получить цены с фильтром по дате."""
        prices = await self.repository.list_by_ticker(
            session,
            filter_data.ticker,
            date_from=filter_data.date_from,
            date_to=filter_data.date_to,
        )
        return [self._to_response(price) for price in prices]


@lru_cache()
def get_price_service() -> "PriceService":
    repository = PriceRepository()
    return PriceService(repository=repository)
