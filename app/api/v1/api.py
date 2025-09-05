"""
Main API router for v1 endpoints.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import stations, analytics, users, auth, notifications, citizen_science, geospatial

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    stations.router,
    prefix="/stations",
    tags=["stations"]
)

api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["analytics"]
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"]
)

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

api_router.include_router(
    notifications.router,
    prefix="/notifications",
    tags=["notifications"]
)

api_router.include_router(
    citizen_science.router,
    prefix="/citizen-science",
    tags=["citizen-science"]
)

api_router.include_router(
    geospatial.router,
    prefix="/geospatial",
    tags=["geospatial"]
)
