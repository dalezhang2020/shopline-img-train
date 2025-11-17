# SKU Recognition System - Dockerfile
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    wget \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Install Grounding DINO
RUN pip3 install --no-cache-dir groundingdino-py

# Copy application code
COPY . .

# Download model weights (optional, can be mounted as volume)
RUN bash scripts/download_models.sh || echo "Model download failed, will use mounted weights"

# Set environment variables
ENV PYTHONPATH=/app
ENV DEVICE=cuda

# Expose port for API (if using)
EXPOSE 8000

# Default command
CMD ["python3", "scripts/run_inference.py", "--help"]
