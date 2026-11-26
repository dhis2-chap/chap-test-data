.PHONY: help lint check test coverage docs docs-serve build
help: ## show the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-8s %s\n", $$1, $$2}'

lint: ## fix and format with ruff, then type check with mypy and pyright
	uv run ruff check --fix
	uv run ruff format
	uv run mypy
	uv run pyright

check: ## the same checks without changing files
	uv run ruff check
	uv run ruff format --check
	uv run mypy
	uv run pyright

test: ## run the tests (no Chap needed)
	uv run pytest -q

coverage: ## run the tests with coverage
	uv run coverage run -m pytest -q
	uv run coverage report

docs: ## build the docs site into site/, failing on warnings
	uv run mkdocs build --strict

docs-serve: ## serve the docs at http://127.0.0.1:8000 while you edit
	uv run mkdocs serve

build: ## build the wheel and sdist into dist/
	uv build
