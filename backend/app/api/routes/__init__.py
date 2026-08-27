"""Route registry.

One router per surface, assembled here so `app.main` mounts a single object and
the URL prefix lives in exactly one place.

Routers are added as their phase lands. Anything listed here is fully
implemented; there are no placeholder endpoints.
"""

from fastapi import APIRouter

from app.api.routes import admin, auth, chat, files, health

api_router = APIRouter()

# Health first: it must stay reachable even if a later router fails to import.
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth")
api_router.include_router(files.router, prefix="/files")
api_router.include_router(admin.router)
# No prefix: the router already declares OpenAI-compatible paths
# (/chat/completions, /models), and API_V1_PREFIX is applied once in app.main.
api_router.include_router(chat.router)

__all__ = ["api_router"]
