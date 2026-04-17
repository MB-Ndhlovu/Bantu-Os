.PHONY: help test lint cov clean build docker-build docker-run docs fmt

PYTHON := python3
PYTEST := pytest
SRC := bantu_os
TESTS := tests
COV_DIR := htmlcov
BLACK := black
RUFF := ruff
CLANG := clang-format
RUSTFMT := rustfmt

help:
	@echo "Bantu-OS Build System"
	@echo ""
	@echo "Available targets:"
	@echo "  test         Run all tests (Python + Rust + C)"
	@echo "  format       Format code (black, rustfmt, clang-format)"
	@echo "  lint         Lint Python (ruff)"
	@echo "  clean        Remove build artifacts and cache"
	@echo "  build        Build Python package"
	@echo "  docs         Generate documentation"
	@echo "  docker-build Build Docker image"
	@echo "  docker-run   Run Docker container"

# ── Python tests ────────────────────────────────────────────────────────────
test-python:
	$(PYTHON) -m pytest $(TESTS)/ -v --tb=short

# ── Rust tests ─────────────────────────────────────────────────────────────
test-rust:
	cd shell && cargo test --lib --tests

# ── C compile check ─────────────────────────────────────────────────────────
test-c:
	cd init && make clean && make

# ── All tests ───────────────────────────────────────────────────────────────
test: test-python test-rust test-c

# ── Format ──────────────────────────────────────────────────────────────────
format-python:
	$(BLACK) $(SRC)/ $(TESTS)/

format-rust:
	cd shell && cargo fmt

format-c:
	find init/ -name "*.c" -o -name "*.h" | xargs $(CLANG) -i

format: format-python format-rust format-c

# ── Lint ────────────────────────────────────────────────────────────────────
lint:
	$(RUFF) check $(SRC)/ $(TESTS)/

# ── Clean ───────────────────────────────────────────────────────────────────
clean:
	rm -rf build/ dist/ *.egg-info
	rm -rf $(COV_DIR)/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .ruff_cache
	cd shell && cargo clean
	cd init && make clean

# ── Build ───────────────────────────────────────────────────────────────────
build:
	$(PYTHON) -m pip install -e . 2>/dev/null || true

# ── Docs ────────────────────────────────────────────────────────────────────
docs:
	$(PYTHON) -m pydoc_markdown -p bantu_os > docs/api.md 2>/dev/null || \
		echo "pydoc-markdown not available – install with: pip install pydoc-markdown"

# ── Docker ──────────────────────────────────────────────────────────────────
docker-build:
	docker build -t bantu-os:latest .

docker-run:
	docker run --rm -it bantu-os:latest