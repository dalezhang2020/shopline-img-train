"""
Main application entry point with FastAPI
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db, test_connection
from scraper import sync_shopline_skuinfo
from models import SyncResponse

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Shopline Scraper API...")
    logger.info(f"Shopline Domain: {settings.SHOPLINE_DOMAIN}")
    logger.info(f"API Version: {settings.API_VERSION}")

    # Test database connection
    if await test_connection():
        logger.info("Database connection verified")
    else:
        logger.warning("Database connection test failed")

    yield

    # Shutdown
    logger.info("Shutting down Shopline Scraper API...")


app = FastAPI(
    title="Shopline Scraper API",
    description="API for scraping and syncing Shopline product data",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Shopline Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "sync": "/sync",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_status = await test_connection()
    return {
        "status": "healthy" if db_status else "degraded",
        "database": "connected" if db_status else "disconnected",
        "service": "shopline-scraper"
    }


@app.post("/sync", response_model=SyncResponse)
async def sync_products(
    mode: str = Query(default="replace", regex="^(replace|append)$"),
    save_history: bool = Query(default=True),
    db: AsyncSession = Depends(get_db)
):
    """
    Sync Shopline products to database

    Args:
        mode: Sync mode - 'replace' (truncate first) or 'append' (add to existing)
        save_history: Whether to save history records
        db: Database session

    Returns:
        SyncResponse with operation details
    """
    try:
        logger.info(f"Sync request received - mode: {mode}, save_history: {save_history}")
        result = await sync_shopline_skuinfo(db, mode=mode, save_history=save_history)
        return result
    except Exception as e:
        logger.error(f"Sync failed with exception: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Sync operation failed",
                "error": str(e)
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
