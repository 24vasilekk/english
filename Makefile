.PHONY: help build up down logs shell migrate seed test

help:
	@echo "Available commands:"
	@echo "  build     - Build Docker images"
	@echo "  up        - Start all services"
	@echo "  down      - Stop all services"
	@echo "  logs      - Show logs"
	@echo "  shell     - Enter bot container shell"
	@echo "  migrate   - Run database migrations"
	@echo "  seed      - Seed database with initial data"
	@echo "  test      - Run tests"

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

shell:
	docker-compose exec bot bash

migrate:
	docker-compose exec bot alembic upgrade head

seed:
	docker-compose exec bot python -m utils.database_seeder

test:
	docker-compose exec bot python -m pytest

dev:
	docker-compose -f docker-compose.yml -f docker-compose.override.yml up