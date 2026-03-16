# Deribit Price Tracker

[![FastAPI](https://img.shields.io/badge/-FastAPI-2EC884?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Celery](https://img.shields.io/badge/-Celery-4899C4?style=flat-square&logo=celery)](https://docs.celeryq.dev/)
[![PostgreSQL](https://img.shields.io/badge/-PostgreSQL-2F7CC9?style=flat-square&logo=postgresql)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/-Redis-DC382D?style=flat-square&logo=redis)](https://redis.io/)

## Обзор

Deribit Price Tracker собирает цены для `btc_usd` и `eth_usd` из публичного API Deribit, сохраняет каждую запись в PostgreSQL и предоставляет только для чтения FastAPI-эндпоинты для получения всех и последних значений. Redis используется и как брокер/бэкенд результатов Celery, и как кэширующий бэкенд FastAPI, а Celery beat запускает сбор данных ежеминутно.

## Архитектура

- **FastAPI-приложение** (`app/src/main.py`): подключает роутеры, время жизни приложения, логирование, настройки через Pydantic и Redis-кэш, реализованный через `FastAPICache`.
- **Сервис цен** (`app/src/services/price_service.py`): оборачивает CRUD-репозиторий SQLAlchemy для модели `Price`, нормализует метки времени к UTC и предоставляет зависимость API.
- **PostgreSQL + Alembic**: модель `Price` описана в `app/src/models/price_model.py`, миграции лежат под `app/alembic`; при старте FastAPI запускает `create_database`, чтобы заблокировать миграции через Redis и выполнить `alembic upgrade head`.
- **Менеджер Redis-кэша** (`app/src/db/redis_cache.py`): создает соединение с Redis, регистрирует бэкенд FastAPI Cache и корректно закрывает соединение при завершении.
- **Celery worker + beat** (`app/src/tasks.py`): задача `fetch_and_save_price` получает актуальную цену через `app/src/utils/deribit_client.py`, сохраняет ее через `PriceService`, а worker и beat запускаются через Docker Compose.
- **Docker Compose** (`docker-compose.yml`): оркестрирует FastAPI, Postgres, Redis, Celery worker и Celery beat; монтирует `./app/src` внутрь контейнеров, чтобы правки отражались во время разработки.

## Стек технологий

- Python 3.12 (образ `python:3.12`)
- FastAPI
- SQLAlchemy + asyncpg
- Alembic
- PostgreSQL
- Redis
- Celery
- Публичное API Deribit (`get_index_price`) через `aiohttp`
- Pytest + pytest-asyncio для модульных тестов

## Начало работы

### Требования

- Docker и Docker Compose (рекомендуется)
- Скопируйте `.env.example` в `.env` и настройте секреты/URL под свою среду

### Docker Compose (рекомендуется)

```bash
git clone <repo_url>
cd Deribit_price_tracker
cp .env.example .env
# отредактируйте .env (учетные данные Deribit, пароль БД и т.п.)
docker compose up -d --build
```

- FastAPI доступен по адресу `http://localhost:${UVICORN_PORT}` (по умолчанию 8000)
- OpenAPI-документация — `http://localhost:${UVICORN_PORT}/api/openapi`

### Запуск без Docker

```bash
cd app
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp ../.env.example .env
uvicorn src.main:app --reload --host $UVICORN_HOST --port $UVICORN_PORT
```

Для отладки можно запускать Celery вручную:

```bash
cd app
celery -A src.tasks worker --loglevel=info
celery -A src.tasks beat --loglevel=info --schedule=/tmp/celerybeat-schedule
```


## Описание API

FastAPI обслуживает HTTP API по пути `/api/v1`. Все ответы — JSON.

| Метод | Путь | Описание | Параметры запроса |
|-------|------|----------|-------------------|
| `GET` | `/api/v1/prices` | Возвращает все сохраненные цены по тикеру (сначала последние). | `ticker` (обязательный, например `btc_usd`) |
| `GET` | `/api/v1/prices/latest` | Возвращает единственную самую свежую цену по тикеру. | `ticker` (обязательный) |
| `GET` | `/api/v1/prices/filter` | Фильтрует цены по тикеру и диапазону дат. | `ticker` (обязательный), `date_from` / `date_to` (ISO 8601 или RFC 3339)

Ответы соответствуют модели `PriceResponse`:

```json
{
  "id": "8c1d2d7d-9c3a-4f2f-b5c2-1e5c5b1a4e6f",
  "ticker": "btc_usd",
  "price": 65548.22,
  "timestamp": "2026-03-16T12:34:56"
}
```

## Фоновые задачи

- В `src/tasks.py` определена задача `fetch_and_save_price`, которая:
  - Вызывает `src/utils/deribit_client.fetch_price` (метод `get_index_price` через `aiohttp`).
  - Сохраняет цену через `PriceService.create_price` внутри транзакционного контекста `SessionFactory`.
- `periodic_price_fetch` перебирает тикеры `btc_usd` и `eth_usd`, ставит в очередь `fetch_and_save_price.delay(ticker)` и запускается каждую минуту через планировщик Celery beat (`app/src/core/celeryconfig.py`).

## Кэширование и жизненный цикл

- `src/main.py` создает `RedisCacheManager` и `RedisClientFactory`, чтобы инициализировать `FastAPICache` и корректно закрыть клиент при завершении.
- `get_price_service` помечен `@lru_cache`, чтобы повторно использовать один экземпляр репозитория для всех запросов.

## Тестирование

```bash
cd app
pytest
```


## Структура проекта

```
+-- docker-compose.yml          # оркестрация FastAPI, Postgres, Redis, Celery worker/beat
+-- app/
|   +-- Dockerfile             # сборка Python 3.12 и установка зависимостей
|   +-- entrypoint.sh          # запускает `uvicorn src.main:app`
|   +-- requirements.txt       # фиксация зависимостей
|   +-- alembic/               # скрипты миграций и конфигурация
|   +-- src/
|   |   +-- main.py            # FastAPI-приложение и hooks жизненного цикла
|   |   +-- api/v1/prices_api.py # endpoint-ы цен
|   |   +-- services/price_service.py # логика репозитория и сервиса
|   |   +-- models/price_model.py     # декларативная модель SQLAlchemy
|   |   +-- schemas/price_schema.py   # DTO для создания/ответов/фильтра
|   |   +-- db/                 # хелперы подключения Postgres и Redis
|   |   +-- core/               # настройки, логгер, конфигурация Celery
|   |   +-- tasks.py            # Celery worker и обработчик
|   |   +-- utils/              # клиент Deribit и хелперы с ретраями
|   +-- tests/                  # набор pytest для сервиса и API
```



## Автор

Evgeny Kudryashov: https://github.com/GagarinRu