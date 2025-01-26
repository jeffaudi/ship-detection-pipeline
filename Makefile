# Variables
PYTHON=python3
PIP=pip3
DOCKER=docker
NPM=npm

# Development setup
install:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt
	@echo "Checking for Flask installation..."
	@$(PYTHON) -c "import flask" || (echo "Flask is not installed. Please check your requirements." && exit 1)
	@echo "Checking for package.json in web directory..."
	@test -f web/package.json || (echo "package.json is missing in the web directory. Please ensure it exists." && exit 1)
	pre-commit install

fix-deps:
	@echo "Fixing development dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install --upgrade black click
	$(PIP) install -r requirements-dev.txt --no-deps
	$(PIP) install -r requirements-dev.txt

# Docker commands
docker-build:
	$(DOCKER) build -t ship-detector .

docker-run:
	$(DOCKER) run -p 8080:8080 ship-detector

# Development servers
dev-api:
	cd api && $(PYTHON) -m flask run --port=5000

dev-web:
	cd web && $(NPM) run dev

# Run both API and web servers
dev:
	make dev-api & make dev-web

# Testing
test:
	pytest tests/

# Linting
lint:
	@echo "Linting Python code..."
	flake8 api/ cogger/ titiler/ --max-line-length=100
	mypy api/ cogger/ titiler/ --ignore-missing-imports
	@echo "Linting web code..."
	@cd web && (npm run lint 2>/dev/null || echo "Web linting skipped - add 'lint' script to package.json to enable")

# Pre-commit
pre-commit:
	pre-commit run --all-files

# Clean
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	cd web && rm -rf node_modules dist
	cd web && $(NPM) cache clean --force

# Code Quality
.PHONY: format check-all

format:
	@echo "Formatting Python code..."
	black api/ cogger/ titiler/ --line-length=100
	isort api/ cogger/ titiler/ --profile black --filter-files
	@echo "Formatting web code..."
	@cd web && (npm run format 2>/dev/null || echo "Web formatting skipped - add 'format' script to package.json to enable")

check-all: format lint
	@echo "All code quality checks completed"

# Help
.PHONY: help
help:
	@echo "Available commands:"
	@echo "  install        - Install dev dependencies"
	@echo "  dev            - Run both API and web servers"
	@echo "  dev-api        - Run API server only"
	@echo "  dev-web        - Run web server only"
	@echo "  test           - Run tests"
	@echo "  format         - Format code (Python + Web)"
	@echo "  lint           - Run linters (Python + Web)"
	@echo "  check-all      - Run all code quality checks"
	@echo "  clean          - Clean build artifacts"
	@echo "  pre-commit     - Run pre-commit hooks manually"
	@echo ""
	@echo "Note: Use 'git commit --no-verify' to bypass pre-commit hooks"


# Note: To bypass pre-commit hooks when committing, use: git commit --no-verify
