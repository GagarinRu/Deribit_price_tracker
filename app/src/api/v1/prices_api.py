from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.price_service import PriceService, get_price_service
from src.schemas.price_schema import PriceResponse, PriceFilter
from src.db.postgres import get_async_session

router = APIRouter()


@router.get("/", response_model=List[PriceResponse])
async def get_prices(
    ticker: str = Query(..., description="Ввести валюту: btc_usd или eth_usd"),
    session: AsyncSession = Depends(get_async_session),
    service: PriceService = Depends(get_price_service),
) -> List[PriceResponse]:
    """Получить все цены для указанного тикера."""
    return await service.get_all_prices(session, ticker)


@router.get("/latest", response_model=PriceResponse)
async def get_latest_price(
    ticker: str = Query(..., description="Ввести валюту: btc_usd или eth_usd"),
    session: AsyncSession = Depends(get_async_session),
    service: PriceService = Depends(get_price_service),
) -> PriceResponse:
    """Получить последнюю цену для указанного тикера."""
    price = await service.get_latest_price(session, ticker)
    if not price:
        raise HTTPException(status_code=404, detail="Валюта не найдена")
    return price


@router.get("/filter", response_model=List[PriceResponse])
async def get_filtered_prices(
    ticker: str = Query(..., description="Ввести валюту: btc_usd или eth_usd"),
    date_from: datetime | None = Query(
        None,
        description="Время начала фильтрации в ISO 8601 (например 2026-01-01T00:00:00Z или UNIX-секунды)",
    ),
    date_to: datetime | None = Query(
        None,
        description="Время окончания фильтрации в ISO 8601 (например 2026-01-02T00:00:00Z или UNIX-секунды)",
    ),
    session: AsyncSession = Depends(get_async_session),
    service: PriceService = Depends(get_price_service),
) -> List[PriceResponse]:
    """Получить цены с фильтром по дате."""
    filter_data = PriceFilter(ticker=ticker, date_from=date_from, date_to=date_to)
    return await service.get_filtered_prices(session, filter_data)
