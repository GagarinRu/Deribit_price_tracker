from abc import ABC, abstractmethod

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis
from redis.exceptions import ConnectionError as RedisError
from src.core.config import RedisSettings
from src.utils.backoff import backoff


class CacheInterface(ABC):
    @abstractmethod
    async def connect(self):
        pass

    @abstractmethod
    async def close(self):
        pass


class RedisCache(CacheInterface):
    """Класс для управления подключением к Redis."""

    def __init__(self, redis_client: aioredis.Redis):
        self.redis_client = redis_client

    async def connect(self):
        FastAPICache.init(RedisBackend(self.redis_client), prefix="fastapi-cache")

    async def close(self):
        await self.redis_client.close()


class RedisClientFactory:
    """Фабрика для создания клиента Redis."""

    @staticmethod
    async def create(redis_dsn: str) -> aioredis.Redis:
        return await aioredis.from_url(redis_dsn)


class RedisCacheManager:
    """Менеджер для управления подключением и кешированием Redis."""

    def __init__(self, settings: RedisSettings):
        self.settings = settings
        self.redis_client: aioredis.Redis | None = None
        self.cache: CacheInterface | None = None

    @backoff(RedisError)
    async def setup(self):
        self.redis_client = await RedisClientFactory.create(self.settings.dsn)
        self.cache = RedisCache(self.redis_client)
        await self.cache.connect()

    @backoff(RedisError)
    async def tear_down(self):
        if self.cache:
            await self.cache.close()
