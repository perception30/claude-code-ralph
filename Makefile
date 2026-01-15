.PHONY: help install dev clean build publish test lint format

PYTHON := python3
PIP := pip3

help:
	@echo "Ralph CLI - Build Commands"
	@echo ""
	@echo "  make install     Install the package locally"
	@echo "  make dev         Install with dev dependencies"
	@echo "  make build       Build wheel and sdist"
	@echo "  make publish     Publish to PyPI"
	@echo "  make test        Run tests"
	@echo "  make lint        Run linter"
	@echo "  make format      Format code"
	@echo "  make clean       Clean build artifacts"
	@echo "  make standalone  Build standalone executable"
	@echo ""

install:
	$(PIP) install -e .

dev:
	$(PIP) install -e ".[dev]"

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf ralph/*.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

build: clean
	$(PYTHON) -m build

publish: build
	$(PYTHON) -m twine upload dist/*

publish-test: build
	$(PYTHON) -m twine upload --repository testpypi dist/*

test:
	$(PYTHON) -m pytest tests/ -v --cov=ralph

lint:
	$(PYTHON) -m ruff check ralph/
	$(PYTHON) -m mypy ralph/

format:
	$(PYTHON) -m black ralph/
	$(PYTHON) -m ruff check --fix ralph/

# Build standalone executable with PyInstaller
standalone:
	$(PIP) install pyinstaller
	pyinstaller --onefile --name ralph ralph/__main__.py

# Build with shiv (self-contained zipapp)
zipapp:
	$(PIP) install shiv
	shiv -c ralph -o ralph.pyz .
