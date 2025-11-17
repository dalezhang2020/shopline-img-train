.PHONY: help install run test clean docker-up docker-down

help:
	@echo "Shopline Scraper - Available commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make run          - Run API server"
	@echo "  make cli          - Run CLI scraper"
	@echo "  make test-db      - Test database connection"
	@echo "  make docker-up    - Start Docker containers"
	@echo "  make docker-down  - Stop Docker containers"
	@echo "  make clean        - Clean Python cache files"

install:
	pip install -r requirements.txt

run:
	python main.py

cli:
	python cli.py --mode replace

test-db:
	python cli.py --test-db

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
