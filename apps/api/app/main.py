"""Main FastAPI Application entrypoint for RecoverAI."""
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import Base, engine, AsyncSessionLocal
from app.core.logging import get_logger, setup_logging
from app.db.seed import seed_database

setup_logging()
logger = get_logger("recoverai.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown events."""
    logger.info("Starting RecoverAI API backend...")
    logger.info(f"Environment: {settings.ENVIRONMENT} | LLM Provider: {settings.LLM_PROVIDER} | Payment: {settings.PAYMENT_PROVIDER}")
    
    # Initialize database schema
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema verified.")

    # Auto-seed initial demo data if empty
    try:
        async with AsyncSessionLocal() as session:
            await seed_database(session)
        logger.info("Database demo seed checked & verified.")
    except Exception as exc:
        logger.warning(f"Seeding notice: {exc}")

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

# Robust CORS Middleware supporting all Vercel production and preview domains
origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    "https://razpay-ai-seven.vercel.app",
]
if isinstance(settings.CORS_ORIGINS, list):
    for o in settings.CORS_ORIGINS:
        if o not in origins and o != "*":
            origins.append(o)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app|http://localhost:\d+|http://127\.0\.0\.1:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add request timing and correlation ID to response headers."""
    start_time = time.time()
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time-Sec"] = f"{process_time:.4f}"
    response.headers["X-Correlation-ID"] = correlation_id
    return response


# Register API v1 Routers
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health"])
async def root_redirect():
    """Root redirect with service metadata."""
    return {
        "name": settings.APP_NAME,
        "tagline": "Detect revenue leakage. Decide the safest intervention. Recover the money. Prove the outcome.",
        "service": "RecoverAI Revenue Recovery Engine",
        "version": "1.0.0",
        "status": "operational",
        "docs_url": "/docs",
        "api_v1": settings.API_V1_STR,
    }
