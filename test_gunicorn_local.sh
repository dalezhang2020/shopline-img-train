#!/bin/bash
# Local Gunicorn test script
# This mimics the production environment without Docker

set -e

echo "=========================================="
echo "Local Gunicorn Test"
echo "=========================================="
echo ""

# Check if vector database exists
FAISS_FILE="data/embeddings/faiss_index_robust_5x.bin"
METADATA_FILE="data/embeddings/sku_metadata_robust_5x.pkl"

if [ -f "$FAISS_FILE" ] && [ -f "$METADATA_FILE" ]; then
    echo "✓ Vector database found"
    ls -lh data/embeddings/*.bin data/embeddings/*.pkl
else
    echo "❌ Vector database not found"
    echo "Expected files:"
    echo "  $FAISS_FILE"
    echo "  $METADATA_FILE"
    exit 1
fi

echo ""
echo "Starting Gunicorn with production settings..."
echo "Port: 6007"
echo "Workers: 2"
echo "Preload: enabled"
echo "=========================================="
echo ""

# Set environment variables (same as Docker)
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONWARNINGS="ignore::UserWarning,ignore::FutureWarning"
export DEVICE=cpu
export CLIP_MODEL="ViT-L/14"
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4

# Check if gunicorn is installed
if ! command -v gunicorn &> /dev/null; then
    echo "❌ Gunicorn not found. Installing..."
    pip install gunicorn
fi

# Start Gunicorn (same config as Docker)
gunicorn scripts.api_server:app \
    --bind 0.0.0.0:6007 \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --preload \
    --timeout 120 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
