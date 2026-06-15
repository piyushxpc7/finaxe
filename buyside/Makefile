.PHONY: install run docker-build docker-up docker-down test lint format clean

# Install dependencies using Poetry
install:
	poetry install

# Run the application locally
run:
	poetry run uvicorn buyside.main:app --host 0.0.0.0 --port 8000 --reload

# Build docker containers
docker-build:
	docker compose build

# Run docker containers
docker-up:
	docker compose up -d

# Stop docker containers
docker-down:
	docker compose down

# Run unit and integration tests
test:
	poetry run pytest

# Lint the codebase
lint:
	poetry run ruff check .
	poetry run black --check .

# Format the codebase
format:
	poetry run ruff check --fix .
	poetry run black .

# Clean temporary Python files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
