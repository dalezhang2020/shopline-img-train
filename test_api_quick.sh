#!/bin/bash
# Quick API test with single worker for faster debugging

set -e

echo "=========================================="
echo "Quick API Test (Single Worker)"
echo "=========================================="
echo ""

# Set environment variables
export PYTHONUNBUFFERED=1
export DEVICE=cpu
export CLIP_MODEL="ViT-L/14"
export OMP_NUM_THREADS=4

echo "Starting Gunicorn with 1 worker for testing..."
echo "Port: 6007"
echo "Access: http://localhost:6007/sku_recognition_fastapi/docs"
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start with just 1 worker for faster startup and debugging
gunicorn scripts.api_server:app \
    --bind 0.0.0.0:6007 \
    --workers 1 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level debug \
    --reload
