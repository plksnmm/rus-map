from fastapi import APIRouter

from rus_map.api.routes import (
    admin_auth,
    admin_submissions,
    geocoding,
    places,
    submissions,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(places.router)
api_router.include_router(admin_auth.router)
api_router.include_router(admin_submissions.router)
api_router.include_router(submissions.router)
api_router.include_router(geocoding.router)
