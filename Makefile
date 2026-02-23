.PHONY: help run format pre-commit

.DEFAULT_GOAL := help

help: ## Display this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

run: ## Run the application
	uv run tourism_assistant/backend/main.py

format: ## Format code with ruff
	uvx ruff check --fix .
	uvx ruff format .

pre-commit: ## Run pre-commit hooks (ruff + pre-commit)
	uvx ruff check --fix .
	uvx ruff format .
	uvx pre-commit run --all-files
