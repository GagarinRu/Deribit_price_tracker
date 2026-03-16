import asyncio
import logging
import os
import re
import subprocess
import uuid

from alembic.config import Config
from redis import asyncio as aioredis
from sqlalchemy import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import (
    Mapped,
    declarative_base,
    declared_attr,
    mapped_column,
    sessionmaker,
)
from src.core.config import postgres_settings, project_settings

instance_id = os.getenv("HOSTNAME", "unknown_instance")

logger = logging.getLogger("src.db.postgres")


class PreBase:
    @declared_attr
    def __tablename__(self) -> str:
        """Добавляет название таблицы по названию класса в метаданные модели в стиле snake_case."""
        return re.sub(r"(?<!^)(?=[A-Z])", "_", self.__name__).lower()

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, sort_order=-1
    )


Base = declarative_base(cls=PreBase)
engine = create_async_engine(postgres_settings.dsn, echo=project_settings.debug)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession)


async def create_database(redis_client: aioredis.Redis, max_wait_time: int = 300):
    lock_key = "db_init_lock"
    lock_timeout = 60

    logger.info("Попытка инициализации базы данных")

    try:
        await redis_client.ping()
        logger.info("Redis доступен")

        lock_acquired = await redis_client.setnx(lock_key, "1")
        if lock_acquired:
            logger.info("Блокировка получена, начинаем создание таблиц")
            await redis_client.expire(lock_key, lock_timeout)
            await asyncio.sleep(2)
            try:
                alembic_cfg = Config("alembic.ini")
                alembic_cfg.set_main_option("sqlalchemy.url", postgres_settings.dsn)
                subprocess.run(["alembic", "upgrade", "head"], check=True)
            except Exception as e:
                logger.error(f"Ошибка при создании таблиц: {e}")
                raise
            finally:
                await redis_client.delete(lock_key)
                logger.info("Блокировка снята")
        else:
            logger.info("Блокировка уже существует, ожидаем завершения другой реплики")
            waited_time = 0
            while await redis_client.exists(lock_key) and waited_time < max_wait_time:
                await asyncio.sleep(1)
                waited_time += 1
                if waited_time % 10 == 0:
                    logger.info(f"Ожидание продолжается: {waited_time} секунд")
            if waited_time >= max_wait_time:
                logger.error("Тайм-аут ожидания инициализации базы данных")
                raise TimeoutError("Тайм-аут ожидания инициализации базы данных")
            logger.info(
                f"Ожидание завершено после {waited_time} секунд, база данных уже инициализирована"
            )
    except aioredis.RedisError as e:
        logger.error(f"Ошибка подключения к Redis: {e}")
        raise
    except Exception as e:
        logger.error(f"Ошибка в процессе инициализации: {e}")
        raise


async def get_async_session():
    async with AsyncSessionLocal() as async_session:
        yield async_session
