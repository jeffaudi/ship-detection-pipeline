# Makefile for API

# Variables
PYTHON=python
FLASK=flask
PYTEST=pytest
ENV=development
PORT=5454

# Configuration
PROJECT_ID := dl4eo
REGION := europe-west1
SERVICE_NAME := ship-detection-api
IMAGE_NAME := ship-detection-api
TAG := latest

# Default target
all: install test run

# Install dependencies
install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pip install -e .

# Check if port is in use
check-port:
	@nc -z localhost $(PORT) 2>/dev/null && \
	echo "Port $(PORT) is in use. Will attempt to kill the process." || \
	echo "Port $(PORT) is available."

# Kill any process running on the specified port
kill-port:
	@echo "Checking for processes on port $(PORT)..."
	@if nc -z localhost $(PORT) 2>/dev/null; then \
		echo "Found process on port $(PORT). Attempting to kill it..."; \
		PID=$$(lsof -ti:$(PORT)) && \
		if [ ! -z "$$PID" ]; then \
			echo "Killing process $$PID..." && \
			kill -9 $$PID && \
			sleep 2 && \
			echo "Process killed successfully."; \
		fi \
	else \
		echo "No process found on port $(PORT)"; \
	fi

# Run the development server
run: check-port kill-port
	@echo "Starting Flask server on port $(PORT)..."
	@if nc -z localhost $(PORT) 2>/dev/null; then \
		echo "Error: Port $(PORT) is still in use after kill attempt. Please check manually."; \
		exit 1; \
	fi
	FLASK_APP=wsgi.py \
	FLASK_ENV=development \
	FLASK_DEBUG=1 \
	$(FLASK) run --port=$(PORT) --host=0.0.0.0

# Run tests
test:
	PYTHONPATH=. $(PYTEST) tests/ -v --cov=src

# Run tests and watch for changes
test-watch:
	PYTHONPATH=. $(PYTEST) tests/ -v --cov=src -f

# Check API
test-api:
	curl -X POST -H "Content-Type: application/json" -d '{"bbox": [[43.0, 2.0], [44.0, 3.0]], "date_from": "2024-01-01", "date_to": "2024-01-26", "cloud_cover": 20}' http://localhost:5454/api/sentinel/search

# Clean up Python cache files
clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name "htmlcov" -exec rm -r {} +
	rm -rf *.egg-info

# Local Development
.PHONY: dev
dev:
	uvicorn src.main:app --reload --port 8080

.PHONY: lint
lint:
	black .
	flake8 .
	isort .

# Security check before docker build
.PHONY: check-sensitive-files
check-sensitive-files:
	@echo "Checking for sensitive files..."
	@if [ -f .env ]; then \
		echo "Warning: .env file exists. Make sure it's in .dockerignore"; \
	fi
	@if [ -f credentials.json ]; then \
		echo "Warning: credentials.json exists. Make sure it's in .dockerignore"; \
	fi
	@if ls *.key 2>/dev/null; then \
		echo "Warning: .key files exist. Make sure they're in .dockerignore"; \
	fi
	@if ls *.pem 2>/dev/null; then \
		echo "Warning: .pem files exist. Make sure they're in .dockerignore"; \
	fi

# Docker Commands
.PHONY: docker-build
docker-build: check-sensitive-files
	docker build -t $(IMAGE_NAME):$(TAG) .

.PHONY: docker-run
docker-run:
	docker run -p 8080:8080 --env-file .env $(IMAGE_NAME):$(TAG)

# Google Cloud Commands
.PHONY: gcloud-build
gcloud-build:
	gcloud builds submit --tag gcr.io/$(PROJECT_ID)/$(IMAGE_NAME):$(TAG)

.PHONY: gcloud-deploy
gcloud-deploy:
	gcloud run deploy $(SERVICE_NAME) \
		--image gcr.io/$(PROJECT_ID)/$(IMAGE_NAME):$(TAG) \
		--platform managed \
		--region $(REGION) \
		--allow-unauthenticated \
		--memory 2Gi \
		--cpu 2 \
		--min-instances 0 \
		--max-instances 10 \
		--set-env-vars "SUPABASE_URL=$(SUPABASE_URL)" \
		--set-env-vars "SUPABASE_KEY=$(SUPABASE_KEY)" \
		--set-env-vars "CDSE_USERNAME=$(CDSE_USERNAME)" \
		--set-env-vars "CDSE_PASSWORD=$(CDSE_PASSWORD)"

# Combined Commands
.PHONY: deploy
deploy: docker-build gcloud-build gcloud-deploy

.PHONY: all install run test test-watch clean kill-port check-port dev lint
