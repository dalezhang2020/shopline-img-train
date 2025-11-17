# Makefile for SKU Recognition System

.PHONY: help install download build inference clean test

help:
	@echo "SKU Recognition System - Makefile Commands"
	@echo ""
	@echo "Available commands:"
	@echo "  make install         - Install dependencies"
	@echo "  make download        - Download SKU data from Shopline"
	@echo "  make build           - Build vector database"
	@echo "  make inference IMG=<path> - Run inference on image"
	@echo "  make clean           - Clean generated files"
	@echo "  make test            - Run tests"
	@echo ""

install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	pip install groundingdino-py
	@echo "✓ Installation complete"

download:
	@echo "Downloading SKU data..."
	python scripts/download_sku_data.py --download-images
	@echo "✓ Download complete"

build:
	@echo "Building vector database..."
	python scripts/build_vector_db.py
	@echo "✓ Build complete"

inference:
	@echo "Running inference..."
ifndef IMG
	@echo "Error: Please specify image path with IMG=<path>"
	@echo "Example: make inference IMG=test.jpg"
	@exit 1
endif
	python scripts/run_inference.py $(IMG) --visualize
	@echo "✓ Inference complete"

clean:
	@echo "Cleaning generated files..."
	rm -rf data/raw/*
	rm -rf data/images/*
	rm -rf data/embeddings/*
	rm -rf output/*
	rm -rf logs/*
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "✓ Clean complete"

test:
	@echo "Running tests..."
	pytest tests/ -v
	@echo "✓ Tests complete"

# Combined workflow
all: install download build
	@echo "✓ Complete workflow finished"
