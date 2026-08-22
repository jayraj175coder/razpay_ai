"""Main FastAPI Application entrypoint for RecoverAI."""
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.logging import get_logger, setup_logging

setup_logging()
logger = get_logger("recoverai.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown events."""
    logger.info("Starting RecoverAI API backend...")
    logger.info(f"Environment: {settings.ENVIRONMENT} | LLM Provider: {settings.LLM_PROVIDER} | Payment: {settings.PAYMENT_PROVIDER}")
    
    # Initialize database tables for local/dev fallback
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema verified.")

    yield

    logger.info("Shutting down RecoverAI API backend...")
    await engine.dispose()
    logger.info("Database connections closed.")


app = FastAPI(
    title="RecoverAI API",
    description="Production-Grade AI Revenue Recovery Platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Inject X-Request-ID and log request timing."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
        process_time = (time.perf_counter() - start_time) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
        
        # Don't log health spam in info
        if "/health" not in request.url.path:
            logger.info(f"[{request_id}] {request.method} {request.url.path} -> {response.status_code} ({process_time:.2f}ms)")
        return response
    except Exception as exc:
        process_time = (time.perf_counter() - start_time) * 1000
        logger.error(f"[{request_id}] Unhandled error for {request.method} {request.url.path}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error", "request_id": request_id},
            headers={"X-Request-ID": request_id},
        )


# Include API v1 routes
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """Root metadata endpoint."""
    return {
        "name": settings.APP_NAME,
        "tagline": "Detect revenue leakage. Decide the safest intervention. Recover the money. Prove the outcome.",
        "version": "1.0.0",
        "docs": "/docs",
        "api_v1": settings.API_V1_STR,
    }
