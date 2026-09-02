from fastapi import APIRouter

from rus_map.api.routes import places

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(places.router)
