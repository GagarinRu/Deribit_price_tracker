import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

import pytest
from fastapi import HTTPException

from src.api.v1.prices_api import get_filtered_prices, get_latest_price, get_prices
from src.schemas.price_schema import PriceFilter
from src.services.price_service import PriceService


@dataclass
class StubPriceRecord:
    id: uuid.UUID
    ticker: str
    price: float
    timestamp: int


def make_stub_price(**overrides):
    kwargs = {
        "id": uuid.uuid4(),
        "ticker": "btc_usd",
        "price": 100.0,
        "timestamp": 123456,
    }
    kwargs.update(overrides)
    return StubPriceRecord(**kwargs)


class CapturedRepository:
    def __init__(self, items):
        self.captured: dict = {}
        self._items = items

    async def list_by_ticker(
        self,
        session,
        ticker,
        date_from=None,
        date_to=None,
        limit=None,
        sort_desc=True,
    ):
        """Записывает аргументы вызова и возвращает заранее заданный список."""
        self.captured.update(
            session=session,
            ticker=ticker,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            sort_desc=sort_desc,
        )
        return self._items


class RecordingService:
    def __init__(self, *, all_prices=None, latest_price=None, filtered=None):
        self._all_prices = all_prices
        self._latest_price = latest_price
        self._filtered = filtered
        self.captured: dict = {}

    async def get_all_prices(self, session, ticker):
        self.captured["session"] = session
        self.captured["ticker"] = ticker
        return self._all_prices

    async def get_latest_price(self, session, ticker):
        self.captured["session"] = session
        self.captured["ticker"] = ticker
        return self._latest_price

    async def get_filtered_prices(self, session, filter_data):
        self.captured["session"] = session
        self.captured["filter"] = filter_data
        return self._filtered


def run_async(corotine):
    """Запуск корутин внутри синхронных тестов."""
    return asyncio.run(corotine)


def test_get_all_prices_does_not_apply_default_limit():
    repository = CapturedRepository([])
    service = PriceService(repository=repository)

    run_async(service.get_all_prices("session", "btc_usd"))

    assert repository.captured["limit"] is None, (
        "Сервис должен запрашивать полный набор данных"
    )
    assert repository.captured["ticker"] == "btc_usd"
    assert repository.captured["session"] == "session"


def test_get_filtered_prices_converts_datetimes():
    """Проверяет, что фильтр конвертирует временные метки в UTC на стороне репозитория."""
    repository = CapturedRepository([make_stub_price()])
    service = PriceService(repository=repository)

    date_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
    date_to = datetime(2026, 1, 2, tzinfo=timezone.utc)
    filter_data = PriceFilter(ticker="btc_usd", date_from=date_from, date_to=date_to)

    run_async(service.get_filtered_prices(None, filter_data))

    assert repository.captured["ticker"] == "btc_usd"
    assert repository.captured["session"] is None
    assert repository.captured["date_from"] == date_from
    assert repository.captured["date_to"] == date_to


def test_get_prices_delegates_to_service():
    """Убеждается, что API просто проксирует запрос к сервису."""
    service = RecordingService(all_prices=["price"])

    result = run_async(get_prices("btc_usd", session="session", service=service))

    assert result == ["price"]
    assert service.captured["session"] == "session"
    assert service.captured["ticker"] == "btc_usd"


def test_get_latest_price_returns_value():
    """Возвращает найденную цену, если таковая есть."""
    service = RecordingService(latest_price={"price": 100.0})

    result = run_async(get_latest_price("eth_usd", session="session", service=service))

    assert result == {"price": 100.0}
    assert service.captured["session"] == "session"
    assert service.captured["ticker"] == "eth_usd"


def test_get_latest_price_raises_when_missing():
    """Поднимает HTTPException, когда сервис вернул None."""
    service = RecordingService(latest_price=None)

    with pytest.raises(HTTPException) as exc_info:
        run_async(get_latest_price("btc_usd", session="session", service=service))

    assert exc_info.value.status_code == 404


def test_get_filtered_prices_builds_filter():
    """Проверяет, что собирается фильтр из входных аргументов."""
    expected_filter = PriceFilter(
        ticker="btc_usd",
        date_from=datetime(2026, 3, 1, tzinfo=timezone.utc),
        date_to=datetime(2026, 3, 2, tzinfo=timezone.utc),
    )
    service = RecordingService(filtered=[{"price": 200.0}])

    result = run_async(
        get_filtered_prices(
            "btc_usd",
            session="session",
            service=service,
            date_from=expected_filter.date_from,
            date_to=expected_filter.date_to,
        )
    )
    assert result == [{"price": 200.0}]
    assert service.captured["session"] == "session"
    assert service.captured["filter"].ticker == expected_filter.ticker
    assert service.captured["filter"].date_from == expected_filter.date_from
    assert service.captured["filter"].date_to == expected_filter.date_to
