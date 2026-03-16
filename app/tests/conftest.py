import importlib
import sys
import types
from pathlib import Path
from typing import Any


def _stub_postgres_module():
    """Возвращает заглушку с PostgresDAO и контекстным менеджером сессии."""
    module = types.ModuleType("src.db.postgres")

    class PostgresDAO:
        def __init__(self, session):
            self.session = session

        async def search(self, table, offset=0, limit=None, sort=None, filters=None):
            return []

    async def get_async_session():
        yield None

    module.PostgresDAO = PostgresDAO
    module.get_async_session = get_async_session
    return module


def _stub_price_module():
    """Создаёт минимальный price_model с классовым интерфейсом Price."""
    module = types.ModuleType("src.models.price_model")

    class Price:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    module.Price = Price
    return module


def _import_or_stub(name: str, builder):
    """Пытается импортировать модуль, и если его нет — регистрирует заглушку."""
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError:
        module = builder()
        sys.modules[name] = module
        return module


def _stub_pydantic_module():
    """Создаёт базовую версию pydantic.BaseModel и ConfigDict."""
    module = types.ModuleType("pydantic")

    class BaseModel:
        def __init__(self, **data):
            for key, value in data.items():
                setattr(self, key, value)

        def model_dump(self):
            return dict(self.__dict__)

        @classmethod
        def model_validate(cls, value):
            if isinstance(value, cls):
                return value
            if hasattr(value, "__dict__"):
                return cls(**value.__dict__)
            if isinstance(value, dict):
                return cls(**value)
            raise TypeError("Cannot validate value")

    class ConfigDict(dict):
        pass

    module.BaseModel = BaseModel
    module.ConfigDict = ConfigDict
    return module


def _stub_fastapi_module():
    """Строит минимальный набор объектов FastAPI для тестов."""
    module = types.ModuleType("fastapi")

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str | None = None):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class APIRouter:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            def decorator(fn):
                return fn

            return decorator

        def include_router(self, *args, **kwargs):
            pass

    def Depends(dependency):
        return dependency

    def Query(default: Any = None, **kwargs):
        return default

    encoders_module = types.ModuleType("fastapi.encoders")

    def jsonable_encoder(value: Any) -> Any:
        return value

    encoders_module.jsonable_encoder = jsonable_encoder
    module.encoders = encoders_module
    sys.modules["fastapi.encoders"] = encoders_module
    module.HTTPException = HTTPException
    module.APIRouter = APIRouter
    module.Depends = Depends
    module.Query = Query
    return module


def _import_postgres_module():
    """Гарантирует, что PostgresDAO и get_async_session доступны."""
    module = _import_or_stub("src.db.postgres", _stub_postgres_module)
    if not hasattr(module, "PostgresDAO"):
        stub = _stub_postgres_module()
        module.PostgresDAO = stub.PostgresDAO
        module.get_async_session = stub.get_async_session
    return module


def _ensure_sqlalchemy_ext_asyncio():
    """Подменяет sqlalchemy.ext.asyncio, если пакет отсутствует."""
    try:
        return importlib.import_module("sqlalchemy.ext.asyncio")
    except ModuleNotFoundError:
        sqlalchemy_module = types.ModuleType("sqlalchemy")
        ext_module = types.ModuleType("sqlalchemy.ext")
        asyncio_module = types.ModuleType("sqlalchemy.ext.asyncio")

        class AsyncSession:
            pass

        asyncio_module.AsyncSession = AsyncSession
        ext_module.asyncio = asyncio_module

        class DummySelect:
            def __init__(self, model):
                self.model = model

            def where(self, *args, **kwargs):
                return self

            def order_by(self, *args, **kwargs):
                return self

            def limit(self, *args, **kwargs):
                return self

        def select(model):
            return DummySelect(model)

        sqlalchemy_module.select = select
        orm_module = types.ModuleType("sqlalchemy.orm")

        class DeclarativeMeta:
            pass

        orm_module.DeclarativeMeta = DeclarativeMeta
        sqlalchemy_module.orm = orm_module
        sys.modules["sqlalchemy.orm"] = orm_module
        sqlalchemy_module.ext = ext_module
        sys.modules["sqlalchemy"] = sqlalchemy_module
        sys.modules["sqlalchemy.ext"] = ext_module
        sys.modules["sqlalchemy.ext.asyncio"] = asyncio_module
        return asyncio_module


_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

_import_or_stub("pydantic", _stub_pydantic_module)
_import_or_stub("fastapi", _stub_fastapi_module)
_ensure_sqlalchemy_ext_asyncio()
_import_or_stub("src.models.price_model", _stub_price_module)
_import_postgres_module()
