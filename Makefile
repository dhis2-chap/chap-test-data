.PHONY: help lint check build
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

build: ## build the wheel and sdist into dist/
	uv build
