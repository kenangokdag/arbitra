.PHONY: help install dev test test-unit lint format typecheck clean precommit

UV := uv

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## uv sync (lock-aware install, dev extra dahil)
	$(UV) sync --extra dev

dev:  ## uvicorn dev server (port 8000, --reload)
	$(UV) run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

test:  ## pytest unit + integration
	$(UV) run pytest -v

test-unit:  ## sadece unit testleri
	$(UV) run pytest -v -m unit tests/unit/

lint:  ## ruff check
	$(UV) run ruff check api/ tests/

format:  ## ruff format
	$(UV) run ruff format api/ tests/

typecheck:  ## mypy strict
	$(UV) run mypy api/

clean:  ## __pycache__ + .pytest_cache + .mypy_cache + .ruff_cache + dist temizle
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov/ dist/ build/ *.egg-info

precommit: lint typecheck test  ## tüm pre-commit gate'ler
