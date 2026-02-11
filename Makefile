.PHONY: install dev test lint format typecheck docker-up docker-down check-uv

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
check-uv:
	@command -v uv >/dev/null 2>&1 || { echo "Error: uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }

install: check-uv
	uv sync --all-extras

# ---------------------------------------------------------------------------
# Development
# ---------------------------------------------------------------------------
dev: check-uv
	uv run uvicorn matrix_hive_driver.api.app:app --host 0.0.0.0 --port 7000 --reload

# ---------------------------------------------------------------------------
# Quality
# ---------------------------------------------------------------------------
test: check-uv
	uv run pytest -q

test-cov: check-uv
	uv run pytest --cov=matrix_hive_driver --cov-report=term-missing -q

lint: check-uv
	uv run ruff check .
	uv run ruff format --check .

format: check-uv
	uv run ruff format .
	uv run ruff check . --fix

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------
docker-up:
	docker compose -f docker/docker-compose.yml up --build

docker-down:
	docker compose -f docker/docker-compose.yml down -v
