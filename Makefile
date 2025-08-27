.PHONY: help install install-dev test test-coverage lint format type-check clean run

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -e .

install-dev: ## Install development dependencies
	pip install --upgrade pip setuptools wheel
	pip install -e .[dev]

test: ## Run tests
	pytest tests/ -v

test-coverage: ## Run tests with coverage report
	pytest tests/ -v --cov=macfonts --cov-report=html --cov-report=term-missing

lint: ## Run linting checks
	flake8 macfonts/ server.py
	black --check macfonts/ server.py
	isort --check-only macfonts/ server.py

format: ## Format code
	black macfonts/ server.py
	isort macfonts/ server.py

type-check: ## Run type checking
	mypy macfonts/ server.py

clean: ## Clean up generated files
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf __pycache__/
	rm -rf */__pycache__/
	rm -rf .mypy_cache/
	find . -name "*.pyc" -delete

run: ## Run the MCP server
	python server.py

check: lint type-check test ## Run all checks (lint, type-check, test)

setup-dev: install-dev ## Setup development environment
	@echo "Development environment setup complete!"
	@echo "Run 'make check' to verify everything is working."