# Variables
PYTHON=python3
PIP=pip3
DOCKER=docker
NPM=npm

# Development setup
install:
	$(PIP) install -r requirements-dev.txt
	@echo "Checking for Flask installation..."
	@$(PYTHON) -c "import flask" || (echo "Flask is not installed. Please check your requirements." && exit 1)
	@echo "Checking for package.json in web directory..."
	@test -f web/package.json || (echo "package.json is missing in the web directory. Please ensure it exists." && exit 1)
	pre-commit install

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
	black .
	isort .
	flake8 .
	cd web && $(NPM) run lint

# Clean
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	cd web && rm -rf node_modules dist
	cd web && $(NPM) cache clean --force

# Help
.PHONY: help
help:
	@echo "Available commands:"
	@echo "  install        - Install dev dependencies"
	@echo "  dev            - Run both API and web servers"
	@echo "  dev-api        - Run API server only"
	@echo "  dev-web        - Run web server only"
	@echo "  test           - Run tests"
	@echo "  lint           - Run linting"
	@echo "  clean          - Clean build artifacts"
