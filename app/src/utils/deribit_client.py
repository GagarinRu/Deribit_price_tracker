import aiohttp
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any
from src.core.config import deribit_settings
from src.core.logger import get_logger

logger = get_logger(__name__)


class DeribitClient:
    def __init__(self, session: aiohttp.ClientSession):
        self.base_url = deribit_settings.base_url
        self.session = session

    async def _make_request(
        self, method: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Сделать запрос к Deribit API."""
        url = f"{self.base_url}/public/{method}"
        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            data = await response.json()
            if data.get("error"):
                raise ValueError(f"Deribit API ошибка: {data['error']}")
            return data["result"]

    async def get_index_price(self, index_name: str) -> float:
        """Получить индексную цену для указанного индекса."""
        params = {"index_name": index_name}
        result = await self._make_request("get_index_price", params)
        return result["index_price"]


@asynccontextmanager
async def deribit_client() -> AsyncIterator[DeribitClient]:
    async with aiohttp.ClientSession() as session:
        yield DeribitClient(session=session)


async def fetch_price(ticker: str) -> float:
    """Получить цену для тикера."""
    index_map = {"btc_usd": "btc_usd", "eth_usd": "eth_usd"}
    if ticker not in index_map:
        raise ValueError(f"Ticker не поддерживается: {ticker}")
    async with deribit_client() as client:
        return await client.get_index_price(index_map[ticker])
