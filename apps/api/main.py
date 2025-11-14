"""
Main FastAPI application for Poolula Platform

Provides REST API for property management, financial tracking, and compliance

Run locally:
    uvicorn apps.api.main:app --reload --port 8082

API documentation (Swagger UI):
    http://localhost:8082/docs
"""

import os
from contextlib import asynccontextmanager
from typing import Dict, Any

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.database.connection import check_connection, close_engine
from core.logging_config import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown events for FastAPI application

    Startup:
        - Verify database connection
        - Log application startup

    Shutdown:
        - Close database connections
        - Log application shutdown
    """
    # Startup
    logger.info("Starting Poolula Platform API...")

    # Verify database connection
    if check_connection():
        logger.info("✅ Database connection verified")
    else:
        logger.error("❌ Database connection failed - application may not work correctly")

    logger.info("🚀 Poolula Platform API is ready")

    yield

    # Shutdown
    logger.info("Shutting down Poolula Platform API...")
    close_engine()
    logger.info("👋 Poolula Platform API stopped")


# Create FastAPI application
app = FastAPI(
    title="Poolula Platform API",
    description="Property management, financial tracking, and compliance API for Poolula LLC",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS (for frontend in Phase 4)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["health"])
def health_check() -> Dict[str, Any]:
    """
    Health check endpoint

    Returns API status and database connection status

    Returns:
        Dictionary with status information

    Example:
        >>> GET /health
        {
            "status": "healthy",
            "api_version": "0.1.0",
            "database_connected": true
        }
    """
    db_connected = check_connection()

    return {
        "status": "healthy" if db_connected else "degraded",
        "api_version": "0.1.0",
        "database_connected": db_connected,
    }


# Import and mount routes
from apps.api.routes import properties, chat

app.include_router(properties.router, prefix="/api/v1", tags=["properties"])
app.include_router(chat.router, prefix="/api", tags=["chat"])


# Mount static files for frontend
# Get project root (2 levels up from this file)
project_root = Path(__file__).parent.parent.parent
frontend_dir = project_root / "frontend"

if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
    logger.info(f"✅ Frontend mounted at: {frontend_dir}")
else:
    logger.warning(f"⚠️  Frontend directory not found: {frontend_dir}")


# Root endpoint
@app.get("/", tags=["root"])
def root() -> Dict[str, str]:
    """
    Root endpoint

    Returns welcome message and link to API documentation
    """
    return {
        "message": "Poolula Platform API",
        "docs": "/docs",
        "health": "/health",
    }
