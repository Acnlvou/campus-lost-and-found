from fastapi import APIRouter

from app.api.routes import admin, auth, claims, health, items

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(items.router, tags=["items"])
api_router.include_router(claims.router, tags=["claims"])
api_router.include_router(admin.router, tags=["admin"])
