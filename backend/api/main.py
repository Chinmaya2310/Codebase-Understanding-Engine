"""FastAPI application factory — Windows-safe asyncio configuration."""
from __future__ import annotations
import asyncio
import logging
import sys
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import analysis, diagrams, questions, repositories
from backend.core.config import get_settings
from backend.core.security import create_access_token
from backend.db.database import init_db

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Windows asyncio fix ───────────────────────────────────────────────────────
# WinError 10055 = socket buffer exhaustion under heavy async I/O.
# Switching to the SelectorEventLoop (instead of ProactorEventLoop) and
# limiting the connection pool prevents this on Windows.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — initialising database")
    await init_db()
    logger.info("Application startup complete")
    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="AI-powered codebase analysis engine",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def timing(request: Request, call_next) -> Response:
        t = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Process-Time"] = f"{time.perf_counter()-t:.4f}s"
        return response

    app.include_router(repositories.router)
    app.include_router(analysis.router)
    app.include_router(diagrams.router)
    app.include_router(questions.router)

    @app.post("/api/auth/token")
    async def login(username: str = "dev", password: str = "dev"):
        return {"access_token": create_access_token(username), "token_type": "bearer"}

    @app.get("/health", tags=["system"])
    async def health():
        return {"status": "ok", "app": settings.app_name, "version": "2.0.0"}

    return app


app = create_app()
