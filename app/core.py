from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.providers.gemini import GeminiProvider
from app.routers import gemini, openai_compat


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    provider = GeminiProvider()
    try:
        await provider.init()
        app.state.gemini_provider = provider
        logger.info("All providers ready")
    except Exception as e:
        logger.warning(f"Gemini provider failed to initialize: {e}")
        app.state.gemini_provider = None

    yield

    # --- Shutdown ---
    logger.info("Shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Gemini Local API",
        description="Local REST API proxy for Gemini web interface",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(gemini.router)
    app.include_router(openai_compat.router)

    return app
