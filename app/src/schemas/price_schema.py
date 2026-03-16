import datetime
from src.schemas.dto import AbstractDTO
from uuid import UUID


class PriceCreate(AbstractDTO):
    ticker: str
    price: float
    timestamp: datetime.datetime


class PriceResponse(PriceCreate):
    id: UUID


class PriceFilter(AbstractDTO):
    ticker: str
    date_from: datetime.datetime | None = None
    date_to: datetime.datetime | None = None
