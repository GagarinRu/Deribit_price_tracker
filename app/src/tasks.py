import asyncio
import datetime
from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from src.core.config import celery_settings, postgres_settings, project_settings
from src.db.base import SessionFactory
from src.schemas.price_schema import PriceCreate
from src.services.price_service import PriceRepository, PriceService
from src.utils.deribit_client import fetch_price
from src.core.logger import get_logger

logger = get_logger(__name__)


class PriceHandler:
    """Обрабатывает получение и сохранение цен."""

    def __init__(self, service: PriceService, session_factory: SessionFactory):
        """Инициализация обработчика."""
        self._service = service
        self._session_factory = session_factory

    async def handle(self, ticker: str):
        """Получить и сохранить цену для указанного тикера."""
        price = await fetch_price(ticker)
        timestamp = datetime.datetime.utcnow()
        price_data = PriceCreate(ticker=ticker, price=price, timestamp=timestamp)
        async with self._session_factory.create_session() as session:
            async with session.begin():
                await self._service.create_price(session, price_data)
        return price


def create_celery_app():
    """Настройка приложения Celery."""
    app = Celery(
        "deribit_tracker",
        broker=celery_settings.broker_url,
        backend=celery_settings.result_backend,
        include=["src.tasks"],
    )
    app.config_from_object("src.core.celeryconfig")
    return app


def create_price_handler():
    """Фабрика для создания PriceHandler."""
    engine = create_async_engine(
        postgres_settings.dsn,
        echo=project_settings.debug,
        poolclass=NullPool,
    )
    session_maker = sessionmaker(engine, class_=AsyncSession)
    session_factory = SessionFactory(session_maker)
    price_service = PriceService(repository=PriceRepository())
    return PriceHandler(service=price_service, session_factory=session_factory)


celery_app = create_celery_app()
price_handler = create_price_handler()


@celery_app.task()
def fetch_and_save_price(ticker: str):
    """Задача для получения и сохранения цены."""
    try:
        price = asyncio.run(price_handler.handle(ticker))
        logger.debug(f"Задача выполнена успешно для {ticker}: {price}")
        return price
    except Exception as e:
        logger.error(f"Ошибка в задаче для {ticker}: {e}", exc_info=True)
        raise


@celery_app.task()
def periodic_price_fetch():
    """Периодическая задача для сбора цен основных криптовалют."""
    tickers = ["btc_usd", "eth_usd"]
    for ticker in tickers:
        fetch_and_save_price.delay(ticker)
