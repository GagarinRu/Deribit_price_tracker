from src.api.v1 import prices_router

from fastapi import APIRouter

API_V1: str = "/api/v1"
main_router = APIRouter()
main_router.include_router(prices_router, prefix=f"{API_V1}/prices", tags=["prices"])
