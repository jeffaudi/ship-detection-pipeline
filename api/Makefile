# Makefile for API

# Variables
PYTHON=python
FLASK=flask
PYTEST=pytest
ENV=development
PORT=8180

# Configuration
PROJECT_ID := deep-learning-earth
PROJECT_NUMBER := 577713910386
REGION := europe-west1
SERVICE_ACCOUNT := ship-detection-pipeline@deep-learning-earth.iam.gserviceaccount.com
SERVICE_NAME := ship-pipeline-api
IMAGE_NAME := ship-pipeline-api
TAG := latest

# Secret names in Google Cloud Secret Manager
SUPABASE_URL_SECRET := ship-pipeline-supabase-url
SUPABASE_KEY_SECRET := ship-pipeline-supabase-key
CDSE_USERNAME_SECRET := ship-pipeline-cdse-username
CDSE_PASSWORD_SECRET := ship-pipeline-cdse-password
API_KEY_SECRET := ship-pipeline-api-key

.PHONY: help
help: ## Display this help message
	@echo '╔══════════════════════════════════════════════════════════════════╗'
	@echo '║                   Ship Detection API Makefile                    ║'
	@echo '╚══════════════════════════════════════════════════════════════════╝'
	@echo ''
	@echo 'Usage:'
	@echo '  make [target]'
	@echo ''
	@echo 'Development Targets:'
	@awk -F ':|##' '/^[^\t].+?:.*?##.*dev/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$NF }' $(MAKEFILE_LIST)
	@echo ''
	@echo 'Testing Targets:'
	@awk -F ':|##' '/^[^\t].+?:.*?##.*test/ { printf "  \033[33m%-20s\033[0m %s\n", $$1, $$NF }' $(MAKEFILE_LIST)
	@echo ''
	@echo 'Docker Targets:'
	@awk -F ':|##' '/^[^\t].+?:.*?##.*docker/ { printf "  \033[34m%-20s\033[0m %s\n", $$1, $$NF }' $(MAKEFILE_LIST)
	@echo ''
	@echo 'Cloud Run Targets:'
	@awk -F ':|##' '/^[^\t].+?:.*?##.*cloud/ { printf "  \033[35m%-20s\033[0m %s\n", $$1, $$NF }' $(MAKEFILE_LIST)
	@echo ''
	@echo 'Utility Targets:'
	@awk -F ':|##' '/^[^\t].+?:.*?##.*util/ { printf "  \033[32m%-20s\033[0m %s\n", $$1, $$NF }' $(MAKEFILE_LIST)


# Install dependencies
install: ## [dev] Install all dependencies including development packages
	pip install -r requirements.txt

# Check if port is in use
check-port:  ## [util] Check if the port is already in use
	@nc -z localhost $(PORT) 2>/dev/null && \
	echo "Port $(PORT) is in use. Will attempt to kill the process." || \
	echo "Port $(PORT) is available."

# Kill any process running on the specified port
kill-port:  ## [util] Kill any process using the specified port
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
run-local: check-port kill-port  ## [dev] Run the Flask development server locally
	@echo "Starting Flask server on port $(PORT)..."
	@if nc -z localhost $(PORT) 2>/dev/null; then \
		echo "Error: Port $(PORT) is still in use after kill attempt. Please check manually."; \
		exit 1; \
	fi
	FLASK_APP=wsgi.py \
	FLASK_ENV=development \
	FLASK_DEBUG=1 \
	$(FLASK) run --port=$(PORT) --host=0.0.0.0

# Test endpoints
test-health: ## [test] Test the local health endpoint
	curl -v http://localhost:$(PORT)/api/health

# Clean up Python cache files
clean: ## [dev] Clean up Python cache and test files
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name "htmlcov" -exec rm -r {} +
	rm -rf *.egg-info

lint: ## [dev] Run code formatting and linting
	black .
	flake8 .
	isort .

# Create secrets in Google Cloud Secret Manager
create-secrets: ## [cloud] Create or update secrets in Google Cloud Secret Manager
	@echo "Creating secrets in Google Cloud Secret Manager..."
	@if [ -f .env ]; then \
		source .env && \
		echo "Creating/updating SUPABASE_URL secret..." && \
		printf "%s" "$$SUPABASE_URL" | gcloud secrets create $(SUPABASE_URL_SECRET) --data-file=- --project $(PROJECT_ID) || \
		printf "%s" "$$SUPABASE_URL" | gcloud secrets versions add $(SUPABASE_URL_SECRET) --data-file=- --project $(PROJECT_ID) && \
		echo "Creating/updating SUPABASE_KEY secret..." && \
		printf "%s" "$$SUPABASE_KEY" | gcloud secrets create $(SUPABASE_KEY_SECRET) --data-file=- --project $(PROJECT_ID) || \
		printf "%s" "$$SUPABASE_KEY" | gcloud secrets versions add $(SUPABASE_KEY_SECRET) --data-file=- --project $(PROJECT_ID) && \
		echo "Creating/updating CDSE_USERNAME secret..." && \
		printf "%s" "$$CDSE_USERNAME" | gcloud secrets create $(CDSE_USERNAME_SECRET) --data-file=- --project $(PROJECT_ID) || \
		printf "%s" "$$CDSE_USERNAME" | gcloud secrets versions add $(CDSE_USERNAME_SECRET) --data-file=- --project $(PROJECT_ID) && \
		echo "Creating/updating CDSE_PASSWORD secret..." && \
		printf "%s" "$$CDSE_PASSWORD" | gcloud secrets create $(CDSE_PASSWORD_SECRET) --data-file=- --project $(PROJECT_ID) || \
		printf "%s" "$$CDSE_PASSWORD" | gcloud secrets versions add $(CDSE_PASSWORD_SECRET) --data-file=- --project $(PROJECT_ID) && \
		echo "Creating/updating API_KEY secret..." && \
		printf "%s" "$$API_KEY" | gcloud secrets create $(API_KEY_SECRET) --data-file=- --project $(PROJECT_ID) || \
		printf "%s" "$$API_KEY" | gcloud secrets versions add $(API_KEY_SECRET) --data-file=- --project $(PROJECT_ID); \
	else \
		echo "Error: .env file not found"; \
		exit 1; \
	fi

# Docker Commands
docker-build: ## [docker] Build the Docker image
	docker build -t $(IMAGE_NAME):$(TAG) .

docker-shell: ## [docker] Open an interactive shell in the running container
	docker run -it --env-file .env $(IMAGE_NAME):$(TAG) /bin/bash

run: docker-build ## [docker] Run the application in Docker
	docker run -p $(PORT):8080 --env-file .env $(IMAGE_NAME):$(TAG)

gcloud-deploy: ## [cloud] Deploy the application to Cloud Run
	gcloud run deploy $(SERVICE_NAME) \
		--source . \
		--service-account $(SERVICE_ACCOUNT) \
		--project $(PROJECT_ID) \
		--platform managed \
		--region $(REGION) \
		--allow-unauthenticated \
		--set-secrets "SUPABASE_URL=$(SUPABASE_URL_SECRET):latest" \
		--set-secrets "SUPABASE_KEY=$(SUPABASE_KEY_SECRET):latest" \
		--set-secrets "CDSE_USERNAME=$(CDSE_USERNAME_SECRET):latest" \
		--set-secrets "CDSE_PASSWORD=$(CDSE_PASSWORD_SECRET):latest" \
		--set-secrets "API_KEY=$(API_KEY_SECRET):latest" \
		--memory 2Gi \
		--cpu 2 \
		--min-instances 0 \
		--max-instances 10

test-health-cloud: ## [cloud] Test the Cloud Run health endpoint
	curl -v https://$(SERVICE_NAME)-$(PROJECT_NUMBER).$(REGION).run.app/api/health

# Combined Commands
deploy: gcloud-deploy ## [cloud] Build and deploy to Cloud Run

.PHONY: install run test test-watch clean kill-port check-port dev lint docker-build create-secrets deploy test-health test-health-cloud docker-shell
