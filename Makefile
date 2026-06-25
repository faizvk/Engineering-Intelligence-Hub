# Reproducibility is a feature: a reviewer should never reverse-engineer the workflow.
.PHONY: help up down logs db-shell install ingest run test eval lint fmt

help:        ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

up:          ## Start Postgres + pgvector (and backend) via docker-compose
	docker compose up -d
	@echo "Waiting for DB healthcheck..." && sleep 3
	docker compose ps

down:        ## Stop everything (keeps the pgdata volume)
	docker compose down

logs:        ## Tail container logs
	docker compose logs -f

db-shell:    ## psql into the running database
	docker compose exec db psql -U eih -d eih

install:     ## Sync deps into .venv from pyproject (uv) or pip fallback
	uv sync --all-extras || pip install -e ".[dev,eval]"

ingest:      ## Run the offline ingestion pipeline over the demo corpus
	uv run python -m ingestion.run || python -m ingestion.run

run:         ## Run the FastAPI backend with autoreload
	uv run uvicorn backend.main:app --reload --port 8000 || \
		uvicorn backend.main:app --reload --port 8000

test:        ## Run the test suite
	uv run pytest -q || pytest -q

eval:        ## Run the RAGAS + retrieval eval suite
	uv run python -m evals.run || python -m evals.run

lint:        ## Lint and type-check
	uv run ruff check . && uv run mypy core backend ingestion

fmt:         ## Auto-format and fix
	uv run ruff format . && uv run ruff check --fix .
