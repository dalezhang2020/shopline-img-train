# ============================================================================
# Production Dockerfile for SKU Recognition API
# ============================================================================
#
# Features:
# - Multi-stage build for optimized image size
# - Auto-download vector database from public S3 on startup (no credentials needed)
# - Gunicorn + Uvicorn workers for high performance
# - CPU-optimized (no GPU dependencies)
# - Non-root user for security
#
# Build:
#   docker build -t sku-recognition-api .
#
# Run (simple - vector database auto-downloads):
#   docker run -d -p 6007:6007 --name sku-recognition-api sku-recognition-api
#
# Run (custom URLs):
#   docker run -d -p 6007:6007 \
#     -e FAISS_URL="https://your-url/faiss_index_robust_5x.bin" \
#     -e METADATA_URL="https://your-url/sku_metadata_robust_5x.pkl" \
#     sku-recognition-api
#
# ============================================================================

# ============================================================================
# Stage 1: Builder - Install dependencies
# ============================================================================
FROM python:3.10-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    # Install boto3 for S3 access
    pip install --no-cache-dir boto3>=1.28.0 && \
    # Pre-download CLIP model to cache
    python -c "import open_clip; open_clip.create_model_and_transforms('ViT-L-14', pretrained='openai')"

# ============================================================================
# Stage 2: Runtime - Lightweight production image
# ============================================================================
FROM python:3.10-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1-mesa-glx \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash apiuser && \
    mkdir -p /app /app/logs /app/output /app/data/embeddings && \
    chown -R apiuser:apiuser /app

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /root/.cache /root/.cache

# Copy application code
COPY --chown=apiuser:apiuser . .

# Switch to non-root user
USER apiuser

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    DEVICE=cpu \
    CLIP_MODEL=ViT-L/14 \
    # Vector database download URLs (public S3)
    FAISS_URL="https://s3.us-east-2.amazonaws.com/tools.zgallerie.com/model/faiss_index_robust_5x.bin" \
    METADATA_URL="https://s3.us-east-2.amazonaws.com/tools.zgallerie.com/model/sku_metadata_robust_5x.pkl" \
    # Optional: Skip download if embeddings already exist
    SKIP_DOWNLOAD="false"

# Expose API port
EXPOSE 6007

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:6007/sku_recognition_fastapi/api/v1/health || exit 1

# ============================================================================
# Startup Script
# ============================================================================
# The entrypoint will:
# 1. Check if vector database exists
# 2. If not, download from S3 (if S3_BUCKET is set)
# 3. Start Gunicorn + Uvicorn workers
# ============================================================================

# Create startup script
USER root
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "==========================================="\n\
echo "SKU Recognition API - Starting..."\n\
echo "==========================================="\n\
\n\
FAISS_FILE="/app/data/embeddings/faiss_index_robust_5x.bin"\n\
METADATA_FILE="/app/data/embeddings/sku_metadata_robust_5x.pkl"\n\
\n\
# Check if vector database files exist\n\
if [ -f "$FAISS_FILE" ] && [ -f "$METADATA_FILE" ]; then\n\
    echo "✓ Vector database found locally"\n\
    ls -lh /app/data/embeddings/\n\
elif [ "$SKIP_DOWNLOAD" = "true" ]; then\n\
    echo "⚠ Vector database not found, but download is disabled"\n\
    echo "⚠ API may fail to start without vector database"\n\
else\n\
    echo "📥 Downloading vector database from S3..."\n\
    echo "   FAISS: $FAISS_URL"\n\
    echo "   Metadata: $METADATA_URL"\n\
    echo ""\n\
    \n\
    # Download FAISS index with progress\n\
    echo "Downloading FAISS index (345 MB)..."\n\
    curl -L --progress-bar -o "$FAISS_FILE" "$FAISS_URL"\n\
    \n\
    if [ $? -eq 0 ]; then\n\
        echo "✓ FAISS index downloaded"\n\
    else\n\
        echo "✗ Failed to download FAISS index"\n\
        exit 1\n\
    fi\n\
    \n\
    # Download metadata with progress\n\
    echo "Downloading SKU metadata (9.7 MB)..."\n\
    curl -L --progress-bar -o "$METADATA_FILE" "$METADATA_URL"\n\
    \n\
    if [ $? -eq 0 ]; then\n\
        echo "✓ SKU metadata downloaded"\n\
    else\n\
        echo "✗ Failed to download SKU metadata"\n\
        exit 1\n\
    fi\n\
    \n\
    echo ""\n\
    echo "✓ Vector database downloaded successfully"\n\
    ls -lh /app/data/embeddings/\n\
fi\n\
\n\
echo ""\n\
echo "Starting Gunicorn + Uvicorn workers..."\n\
echo "Port: 6007"\n\
echo "Workers: 4"\n\
echo "==========================================="\n\
echo ""\n\
\n\
# Start Gunicorn with Uvicorn workers\n\
exec gunicorn scripts.api_server:app \\\n\
    --bind 0.0.0.0:6007 \\\n\
    --workers 4 \\\n\
    --worker-class uvicorn.workers.UvicornWorker \\\n\
    --threads 2 \\\n\
    --timeout 120 \\\n\
    --keepalive 5 \\\n\
    --access-logfile - \\\n\
    --error-logfile - \\\n\
    --log-level info\n\
' > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh && \
    chown apiuser:apiuser /app/entrypoint.sh

USER apiuser

ENTRYPOINT ["/app/entrypoint.sh"]
