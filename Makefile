.PHONY: help build up down logs install dev-frontend dev-backend clean

# Default target
help:
	@echo "DataLix-AI Makefile"
	@echo "==================="
	@echo "Usage:"
	@echo "  make build          - Build Docker containers"
	@echo "  make up             - Start Docker containers in detached mode"
	@echo "  make down           - Stop and remove Docker containers"
	@echo "  make logs           - View Docker logs"
	@echo "  make install        - Install local dependencies (Node + Python)"
	@echo "  make dev-frontend   - Run frontend dev server"
	@echo "  make dev-backend    - Run backend dev server"
	@echo "  make clean          - Remove node_modules, Python cache, and temp files"

# Docker commands
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

# Local development commands
install:
	npm install
	cd python_backend && pip install -r requirements.txt

dev-frontend:
	npm run dev

dev-backend:
	cd python_backend && uvicorn main:app --reload --port 8001

# Cleanup
clean:
	rm -rf node_modules
	rm -rf dist
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf python_backend/venv
	rm -rf /tmp/datalix_exports/*
	@echo "Clean complete."
