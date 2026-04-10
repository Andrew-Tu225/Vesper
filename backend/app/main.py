from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from app.database import engine
from app.redis import close_redis_pool
from app.api.auth.google import router as google_auth_router
from app.api.health import router as health_router
from app.api.oauth.slack import router as slack_oauth_router
from app.api.oauth.linkedin import router as linkedin_oauth_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    yield
    # Shutdown
    await engine.dispose()
    await close_redis_pool()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Vesper",
        description="AI content assistant — Slack signals → LinkedIn posts",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(health_router, tags=["health"])
    app.include_router(google_auth_router, prefix="/api/auth")
    app.include_router(slack_oauth_router, prefix="/api/oauth")
    app.include_router(linkedin_oauth_router, prefix="/api/oauth")

    return app


app = create_app()
