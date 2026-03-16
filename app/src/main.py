import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from src.api.routers import main_router
from src.core.config import project_settings, redis_settings
from src.db.postgres import create_database
from src.db.redis_cache import RedisCacheManager, RedisClientFactory


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление ресурсами FastAPI."""
    redis_cache_manager = RedisCacheManager(redis_settings)
    redis_client = await RedisClientFactory.create(redis_settings.dsn)
    await create_database(redis_client)
    await redis_cache_manager.setup()

    try:
        await redis_cache_manager.setup()
        yield
    except Exception:
        traceback.print_exc()
        raise
    finally:
        await redis_cache_manager.tear_down()


app = FastAPI(
    title=project_settings.project_name,
    docs_url="/api/openapi",
    openapi_url="/api/openapi.json",
    default_response_class=ORJSONResponse,
    summary=project_settings.project_summary,
    version=project_settings.project_version,
    terms_of_service=project_settings.project_terms_of_service,
    openapi_tags=project_settings.project_tags,
    lifespan=lifespan,
)

app.include_router(main_router)
