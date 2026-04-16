.PHONY: help install test lint cov clean build docker-build docker-run docs

PYTHON := python3
POETRY := poetry
PYTEST := pytest
SRC := bantu_os
TESTS := tests
COV_DIR := htmlcov

help:
	@echo "Bantu-OS Build System"
	@echo ""
	@echo "Available targets:"
	@echo "  install      Install dependencies via Poetry"
	@echo "  test         Run pytest test suite"
	@echo "  lint         Run Ruff linter"
	@echo "  cov          Generate coverage report"
	@echo "  clean        Remove build artifacts and cache"
	@echo "  build        Build Python package"
	@echo "  docker-build Build Docker image"
	@echo "  docker-run   Run Docker container"
	@echo "  docs         Generate documentation"

install:
	$(POETRY) install --with dev

test:
	$(POETRY) run $(PYTEST) $(TESTS)/ --cov=$(SRC) --cov-report=term-missing:skip-covered

lint:
	$(POETRY) run ruff check $(SRC)/ $(TESTS)/

cov:
	$(POETRY) run $(PYTEST) $(TESTS)/ --cov=$(SRC) --cov-report=html --cov-report=term-missing
	@echo "Coverage report: file://$$(pwd)/$(COV_DIR)/index.html"

clean:
	rm -rf build/ dist/ *.egg-info
	rm -rf $(COV_DIR)/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .ruff_cache

build:
	$(POETRY) build

docker-build:
	docker build -t bantu-os:latest .

docker-run:
	docker run --rm -it bantu-os:latest

docs:
	$(POETRY) run pydoc-markdown -p bantu_os > docs/api.md 2>/dev/null || echo "docs generation skipped"