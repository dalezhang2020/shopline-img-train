"""
SKU Recognition API Server
Fast API service for real-time SKU recognition from images
"""
import os
import sys
import io
import base64
import time
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
from PIL import Image
import numpy as np

from src.pipeline.inference import SKURecognitionPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========================
# Pydantic Models
# ========================

class RecognitionRequest(BaseModel):
    """Request model for base64 image recognition"""
    image_base64: str = Field(..., description="Base64 encoded image string")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of top results to return")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum confidence score")

class SKUMatch(BaseModel):
    """Model for a single SKU match result"""
    sku: str = Field(..., description="SKU code")
    similarity: float = Field(..., description="Similarity score (0-1)")
    product_title: Optional[str] = Field(None, description="Product title")
    category: Optional[str] = Field(None, description="Product category")
    retail_price: Optional[float] = Field(None, description="Retail price")
    image_url: Optional[str] = Field(None, description="Product image URL")
    barcode: Optional[str] = Field(None, description="Product barcode")

class RecognitionResponse(BaseModel):
    """Response model for SKU recognition"""
    success: bool = Field(..., description="Whether recognition succeeded")
    matches: List[SKUMatch] = Field(default=[], description="List of matched SKUs")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    timestamp: str = Field(..., description="ISO timestamp")
    message: Optional[str] = Field(None, description="Optional message or error")

class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    model_loaded: bool = Field(..., description="Whether model is loaded")
    database_size: int = Field(..., description="Number of SKUs in database")
    uptime_seconds: float = Field(..., description="Service uptime")

class StatsResponse(BaseModel):
    """Statistics response"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_processing_time_ms: float
    uptime_seconds: float

# ========================
# FastAPI Application
# ========================

app = FastAPI(
    title="SKU Recognition API",
    description="Real-time product SKU recognition using CLIP and FAISS",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    root_path="/sku_recognition_fastapi"  # AWS 反向代理路径前缀
)

# CORS Configuration
# Allow Next.js frontend to call API
ALLOWED_ORIGINS = [
    # 本地开发环境
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    # AWS 生产环境
    "https://tools.zgallerie.com",
    "https://zgallerie.com",
    "https://www.zgallerie.com",
    "https://zg-wms-store.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================
# Global State
# ========================

class APIState:
    """Global application state"""
    def __init__(self):
        self.pipeline: Optional[SKURecognitionPipeline] = None
        self.start_time = time.time()
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_processing_time': 0.0
        }

state = APIState()

# ========================
# Startup & Shutdown
# ========================

@app.on_event("startup")
async def startup_event():
    """Initialize model and database on startup"""
    logger.info("🚀 Starting SKU Recognition API Server...")

    try:
        # Load configuration
        config_path = PROJECT_ROOT / 'config' / 'config.yaml'
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        # Initialize pipeline
        logger.info("📦 Loading SKU recognition pipeline...")
        state.pipeline = SKURecognitionPipeline(config_path=str(config_path))

        # Load vector database
        index_path = PROJECT_ROOT / 'data' / 'embeddings' / 'faiss_index.bin'
        metadata_path = PROJECT_ROOT / 'data' / 'embeddings' / 'sku_metadata.pkl'

        if not index_path.exists() or not metadata_path.exists():
            raise FileNotFoundError(
                f"Vector database not found. Please run:\n"
                f"python scripts/build_robust_vector_db.py --augment-per-image 2"
            )

        state.pipeline.load_database(
            index_path=str(index_path),
            metadata_path=str(metadata_path)
        )

        logger.info(f"✅ Pipeline loaded successfully!")
        logger.info(f"📊 Database size: {len(state.pipeline.sku_metadata)} SKUs")
        logger.info(f"🎯 Ready to process recognition requests")

    except Exception as e:
        logger.error(f"❌ Failed to initialize: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("👋 Shutting down SKU Recognition API Server...")

# ========================
# Helper Functions
# ========================

def decode_base64_image(base64_string: str) -> Image.Image:
    """Decode base64 string to PIL Image"""
    try:
        # Remove data URL prefix if present
        if ',' in base64_string:
            base64_string = base64_string.split(',', 1)[1]

        # Decode base64
        image_bytes = base64.b64decode(base64_string)
        image = Image.open(io.BytesIO(image_bytes))

        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')

        return image
    except Exception as e:
        raise ValueError(f"Failed to decode base64 image: {e}")

def validate_image(image: Image.Image) -> None:
    """Validate image properties"""
    # Check dimensions
    width, height = image.size
    if width < 50 or height < 50:
        raise ValueError(f"Image too small: {width}x{height}. Minimum: 50x50")

    if width > 4096 or height > 4096:
        raise ValueError(f"Image too large: {width}x{height}. Maximum: 4096x4096")

    # Check file size (approximate)
    img_bytes = io.BytesIO()
    image.save(img_bytes, format='JPEG')
    size_mb = len(img_bytes.getvalue()) / (1024 * 1024)

    if size_mb > 10:
        raise ValueError(f"Image too large: {size_mb:.1f}MB. Maximum: 10MB")

def format_sku_match(result: Dict[str, Any]) -> SKUMatch:
    """Format recognition result to SKUMatch model"""
    return SKUMatch(
        sku=result['sku'],
        similarity=float(result['similarity']),
        product_title=result.get('product_title'),
        category=result.get('category'),
        retail_price=result.get('retail_price'),
        image_url=result.get('image_url'),
        barcode=result.get('barcode')
    )

# ========================
# API Endpoints
# ========================

@app.get("/", response_model=dict)
async def root():
    """Root endpoint - API information"""
    return {
        "service": "SKU Recognition API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/api/v1/health",
            "recognize_upload": "/api/v1/recognize (POST with file)",
            "recognize_base64": "/api/v1/recognize/base64 (POST with JSON)",
            "stats": "/api/v1/stats",
            "docs": "/docs"
        }
    }

@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy" if state.pipeline else "unhealthy",
        version="1.0.0",
        model_loaded=state.pipeline is not None,
        database_size=len(state.pipeline.sku_metadata) if state.pipeline else 0,
        uptime_seconds=time.time() - state.start_time
    )

@app.get("/api/v1/stats", response_model=StatsResponse)
async def get_stats():
    """Get API statistics"""
    avg_time = (
        state.stats['total_processing_time'] / state.stats['total_requests']
        if state.stats['total_requests'] > 0
        else 0.0
    )

    return StatsResponse(
        total_requests=state.stats['total_requests'],
        successful_requests=state.stats['successful_requests'],
        failed_requests=state.stats['failed_requests'],
        average_processing_time_ms=avg_time,
        uptime_seconds=time.time() - state.start_time
    )

@app.post("/api/v1/recognize", response_model=RecognitionResponse)
async def recognize_upload(
    file: UploadFile = File(...),
    top_k: int = Query(default=5, ge=1, le=20),
    confidence_threshold: float = Query(default=0.7, ge=0.0, le=1.0)
):
    """
    Recognize SKU from uploaded image file

    - **file**: Image file (JPEG, PNG, WebP)
    - **top_k**: Number of top results to return (1-20)
    - **confidence_threshold**: Minimum confidence score (0.0-1.0)
    """
    start_time = time.time()
    state.stats['total_requests'] += 1

    try:
        # Check if model is loaded
        if not state.pipeline:
            raise HTTPException(status_code=503, detail="Model not loaded")

        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.content_type}. Must be an image."
            )

        # Read and decode image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))

        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Validate image
        validate_image(image)

        # Process image
        results = state.pipeline.process_image(
            image,
            top_k=top_k,
            confidence_threshold=confidence_threshold
        )

        # Format results
        matches = [format_sku_match(r) for r in results]

        # Update stats
        processing_time = (time.time() - start_time) * 1000
        state.stats['successful_requests'] += 1
        state.stats['total_processing_time'] += processing_time

        return RecognitionResponse(
            success=True,
            matches=matches,
            processing_time_ms=processing_time,
            timestamp=datetime.utcnow().isoformat(),
            message=f"Found {len(matches)} matches" if matches else "No matches found"
        )

    except HTTPException:
        raise
    except Exception as e:
        state.stats['failed_requests'] += 1
        logger.error(f"Recognition failed: {e}")
        processing_time = (time.time() - start_time) * 1000

        return RecognitionResponse(
            success=False,
            matches=[],
            processing_time_ms=processing_time,
            timestamp=datetime.utcnow().isoformat(),
            message=f"Recognition failed: {str(e)}"
        )

@app.post("/api/v1/recognize/base64", response_model=RecognitionResponse)
async def recognize_base64(request: RecognitionRequest):
    """
    Recognize SKU from base64 encoded image

    - **image_base64**: Base64 encoded image string
    - **top_k**: Number of top results to return (1-20)
    - **confidence_threshold**: Minimum confidence score (0.0-1.0)
    """
    start_time = time.time()
    state.stats['total_requests'] += 1

    try:
        # Check if model is loaded
        if not state.pipeline:
            raise HTTPException(status_code=503, detail="Model not loaded")

        # Decode base64 image
        image = decode_base64_image(request.image_base64)

        # Validate image
        validate_image(image)

        # Process image
        results = state.pipeline.process_image(
            image,
            top_k=request.top_k,
            confidence_threshold=request.confidence_threshold
        )

        # Format results
        matches = [format_sku_match(r) for r in results]

        # Update stats
        processing_time = (time.time() - start_time) * 1000
        state.stats['successful_requests'] += 1
        state.stats['total_processing_time'] += processing_time

        return RecognitionResponse(
            success=True,
            matches=matches,
            processing_time_ms=processing_time,
            timestamp=datetime.utcnow().isoformat(),
            message=f"Found {len(matches)} matches" if matches else "No matches found"
        )

    except HTTPException:
        raise
    except Exception as e:
        state.stats['failed_requests'] += 1
        logger.error(f"Recognition failed: {e}")
        processing_time = (time.time() - start_time) * 1000

        return RecognitionResponse(
            success=False,
            matches=[],
            processing_time_ms=processing_time,
            timestamp=datetime.utcnow().isoformat(),
            message=f"Recognition failed: {str(e)}"
        )

@app.post("/api/v1/recognize/batch", response_model=Dict[str, Any])
async def recognize_batch(
    files: List[UploadFile] = File(...),
    top_k: int = Query(default=5, ge=1, le=20),
    confidence_threshold: float = Query(default=0.7, ge=0.0, le=1.0)
):
    """
    Recognize SKUs from multiple images in batch

    - **files**: List of image files
    - **top_k**: Number of top results per image
    - **confidence_threshold**: Minimum confidence score
    """
    start_time = time.time()

    if len(files) > 20:
        raise HTTPException(
            status_code=400,
            detail="Too many files. Maximum 20 images per batch."
        )

    results = []
    for idx, file in enumerate(files):
        try:
            # Process each image
            contents = await file.read()
            image = Image.open(io.BytesIO(contents))

            if image.mode != 'RGB':
                image = image.convert('RGB')

            matches = state.pipeline.process_image(
                image,
                top_k=top_k,
                confidence_threshold=confidence_threshold
            )

            results.append({
                'filename': file.filename,
                'success': True,
                'matches': [format_sku_match(m).dict() for m in matches]
            })

        except Exception as e:
            results.append({
                'filename': file.filename,
                'success': False,
                'error': str(e)
            })

    processing_time = (time.time() - start_time) * 1000

    return {
        'success': True,
        'total_images': len(files),
        'results': results,
        'processing_time_ms': processing_time,
        'timestamp': datetime.utcnow().isoformat()
    }

# ========================
# Main Entry Point
# ========================

if __name__ == "__main__":
    # Run server
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Set to True for development
        log_level="info"
    )
