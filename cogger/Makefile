.PHONY: help build run deploy

# Set help as the default target
.DEFAULT_GOAL := help

# Help target that automatically lists all targets with descriptions
help:  ## Display this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@echo "----------------"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Example: make dev"

# Configuration
PROJECT_ID := deep-learning-earth
PROJECT_NUMBER := 577713910386
GCS_BUCKET_NAME := dl4eo-sentinel2-cogs
SERVICE_ACCOUNT := ship-detection-pipeline@deep-learning-earth.iam.gserviceaccount.com
SERVICE_NAME := sentinel2-cog-converter
IMAGE_NAME := ship-pipeline-cogger
TAG := latest
REGION := europe-west1
SA_KEY_FILE := deep-learning-earth-d9ea763f10c9.json

# Test image IDs (Sentinel-2A and Sentinel-2B)
#TEST_IMAGE_ID := 5ba786ba-eda0-4174-8879-63406fb84804
TEST_IMAGE_ID := e38f9a88-4586-46ad-8f12-d397d8844fc7

# Secret names in Google Cloud Secret Manager
SUPABASE_URL_SECRET := ship-pipeline-supabase-url
SUPABASE_KEY_SECRET := ship-pipeline-supabase-key
CDSE_USERNAME_SECRET := ship-pipeline-cdse-username
CDSE_PASSWORD_SECRET := ship-pipeline-cdse-password
API_KEY_SECRET := ship-pipeline-api-key

## LOCAL DEVELOPMENT SECTION

.PHONY: dev
dev: ## Start the development server with auto-reload
	cd app && \
	export GOOGLE_APPLICATION_CREDENTIALS=$(PWD)/$(SA_KEY_FILE) && \
	uvicorn main:app --reload --port 8181

# Helper targets
.PHONY: test logs clean test-full test-env shell docker-test docker-test-full

test: ## Run a basic health check
	echo "Testing health check..." && \
	curl http://localhost:8181/health

test-full: ## Run a full conversion test
	@echo "Testing full conversion process with image ID: ${TEST_IMAGE_ID}-"
	@set -a && . ./.env && set +a && curl -X POST http://localhost:8181/convert \
		-H "Content-Type: application/json" \
		-H "X-API-Key: $$(grep API_KEY .env | cut -d '=' -f2)" \
		-d "{\"sentinel_id\": \"${TEST_IMAGE_ID}\"}"

## DOCKER SECTION

# Docker Commands
.PHONY: docker-build
docker-build: ## Build the Docker image
	docker build -t $(IMAGE_NAME):$(TAG) .

.PHONY: docker-run
docker-run: ## Run the Docker container locally
	docker run -p 8081:8080 \
		--env-file .env \
		--env GCS_BUCKET_NAME=$(GCS_BUCKET_NAME) \
		--env GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
		-v $(PWD)/$(SA_KEY_FILE):/app/credentials.json \
		$(IMAGE_NAME):$(TAG)

.PHONY: docker-run-dev
docker-run-dev: ## Run the Docker container in development mode with hot reload
	docker run -p 8081:8080 \
		--env-file .env \
		--env GCS_BUCKET_NAME=$(GCS_BUCKET_NAME) \
		--env GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
		-v $(PWD)/$(SA_KEY_FILE):/app/credentials.json \
		-v $(PWD):/app \
		--entrypoint python \
		$(IMAGE_NAME):$(TAG) \
		-m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

docker-test: ## Run a basic health check against the Docker container
	@CONTAINER_ID=$$(docker ps -q --filter ancestor=$(IMAGE_NAME):$(TAG)) && \
	if [ -z "$$CONTAINER_ID" ]; then \
		echo "No running container found. Please run 'make docker-run' first."; \
		exit 1; \
	fi && \
	echo "Testing Docker container health endpoint..." && \
	curl -s http://localhost:8081/health

docker-test-full: ## Run a full conversion test against the Docker container
	@CONTAINER_ID=$$(docker ps -q --filter ancestor=$(IMAGE_NAME):$(TAG)) && \
	if [ -z "$$CONTAINER_ID" ]; then \
		echo "No running container found. Please run 'make docker-run' first."; \
		exit 1; \
	fi && \
	echo "Testing full conversion process in Docker container..." && \
	curl -s -X POST http://localhost:8081/convert \
		-H "Content-Type: application/json" \
		-H "X-API-Key: $$(grep API_KEY .env | cut -d '=' -f2)" \
		-d "{\"sentinel_id\": \"${TEST_IMAGE_ID}\"}" | \
	tee /dev/stderr | grep -q '"status":"success"' && \
	echo "✅ Conversion test passed" || \
	(echo "❌ Conversion test failed" && exit 1)

docker-shell: ## Get an interactive shell inside the running container
	@CONTAINER_ID=$$(docker ps -q --filter ancestor=$(IMAGE_NAME):$(TAG)) && \
	if [ -z "$$CONTAINER_ID" ]; then \
		echo "No running container found. Starting a new one..."; \
		docker run -it --rm --entrypoint=/bin/bash $(IMAGE_NAME):$(TAG); \
	else \
		echo "Connecting to running container..."; \
		docker exec -it $$CONTAINER_ID /bin/bash; \
	fi

docker-test-env: ## Test environment variables in the container
	@echo "Testing environment variables in container..."
	@CONTAINER_ID=$$(docker ps -q --filter ancestor=$(IMAGE_NAME):$(TAG)) && \
	if [ -z "$$CONTAINER_ID" ]; then \
		echo "No running container found. Please run 'make docker-run' first."; \
		exit 1; \
	fi && \
	echo "\nEnvironment:" && \
	docker exec $$CONTAINER_ID env | grep VITE_ENV || true && \
	echo "\nCDSE credentials:" && \
	docker exec $$CONTAINER_ID env | grep CDSE || true && \
	echo "\nGoogle Cloud settings:" && \
	docker exec $$CONTAINER_ID env | grep -E "PROJECT_ID|GCS_" || true && \
	echo "\nSupabase configuration:" && \
	docker exec $$CONTAINER_ID env | grep SUPABASE || true && \
	echo "\nAPI configuration:" && \
	docker exec $$CONTAINER_ID env | grep API_KEY | sed 's/\(API_KEY=\).*/\1****/' || true && \
	echo "\nGDAL configuration:" && \
	docker exec $$CONTAINER_ID env | grep -E "GDAL_|VSI_" || true

docker-clean: ## Remove Docker containers
	docker rm -f $$(docker ps -aq --filter ancestor=$(SERVICE_NAME)) 2>/dev/null || true

docker-logs: ## View Docker container logs
	docker logs $$(docker ps -q --filter ancestor=$(SERVICE_NAME))

# GOOGLE CLOUD SECTION

# Create secrets in Google Cloud Secret Manager
.PHONY: create-secrets
create-secrets: ## Create/update secrets in Google Cloud Secret Manager
	@echo "Creating secrets in Google Cloud Secret Manager..."
	@if [ -f .env ]; then \
		source .env && \
		echo "Creating/updating SUPABASE_URL secret..." && \
		echo "$$SUPABASE_URL" | tr -d '\n\r' | xargs | gcloud secrets create $(SUPABASE_URL_SECRET) --data-file=- --project $(PROJECT_ID) || \
		echo "$$SUPABASE_URL" | tr -d '\n\r' | xargs | gcloud secrets versions add $(SUPABASE_URL_SECRET) --data-file=- --project $(PROJECT_ID) && \
		echo "Creating/updating SUPABASE_KEY secret..." && \
		echo "$$SUPABASE_KEY" | tr -d '\n\r' | xargs | gcloud secrets create $(SUPABASE_KEY_SECRET) --data-file=- --project $(PROJECT_ID) || \
		echo "$$SUPABASE_KEY" | tr -d '\n\r' | xargs | gcloud secrets versions add $(SUPABASE_KEY_SECRET) --data-file=- --project $(PROJECT_ID) && \
		echo "Creating/updating API_KEY secret..." && \
		echo "$$API_KEY" | tr -d '\n\r' | xargs | gcloud secrets create $(API_KEY_SECRET) --data-file=- --project $(PROJECT_ID) || \
		echo "$$API_KEY" | tr -d '\n\r' | xargs | gcloud secrets versions add $(API_KEY_SECRET) --data-file=- --project $(PROJECT_ID); \
	else \
		echo "Error: .env file not found"; \
		exit 1; \
	fi

# Google Cloud Commands
.PHONY: gcloud-build
gcloud-build: ## Build the image using Google Cloud Build
	gcloud builds submit --project $(PROJECT_ID) --tag gcr.io/$(PROJECT_ID)/$(IMAGE_NAME):$(TAG)

.PHONY: gcloud-deploy
gcloud-deploy: ## Deploy the service to Cloud Run
	gcloud run deploy $(SERVICE_NAME) \
		--image gcr.io/$(PROJECT_ID)/$(IMAGE_NAME):$(TAG) \
		--platform managed \
		--project $(PROJECT_ID) \
		--region $(REGION) \
		--service-account $(SERVICE_ACCOUNT) \
		--allow-unauthenticated \
		--memory 8Gi \
		--cpu 4 \
		--timeout 3600 \
		--min-instances 0 \
		--max-instances 5 \
		--concurrency 1 \
		--set-env-vars="GDAL_CACHEMAX=4096" \
		--set-env-vars="GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR" \
		--set-env-vars="GDAL_HTTP_MERGE_CONSECUTIVE_RANGES=YES" \
		--set-env-vars="GDAL_HTTP_MULTIPLEX=YES" \
		--set-env-vars="GDAL_HTTP_VERSION=2" \
		--set-env-vars="VSI_CACHE=TRUE" \
		--set-env-vars="VSI_CACHE_SIZE=1000000000" \
		--set-env-vars="GCS_BUCKET_NAME=$(GCS_BUCKET_NAME)" \
		--set-secrets="CDSE_USERNAME=$(CDSE_USERNAME_SECRET):latest" \
		--set-secrets="CDSE_PASSWORD=$(CDSE_PASSWORD_SECRET):latest" \
		--set-secrets="SUPABASE_URL=$(SUPABASE_URL_SECRET):latest" \
		--set-secrets="SUPABASE_KEY=$(SUPABASE_KEY_SECRET):latest" \
		--set-secrets="API_KEY=$(API_KEY_SECRET):latest"

# Service account setup
.PHONY: gcloud-setup
gcloud-setup:
	@echo "Setting up service account authentication..."
	@if [ ! -f "${SA_KEY_FILE}" ]; then \
		gcloud iam service-accounts keys create ${SA_KEY_FILE} \
			--iam-account=${SERVICE_ACCOUNT}; \
	fi
	gcloud projects add-iam-policy-binding $(PROJECT_ID) \
    	--member="serviceAccount:$(SERVICE_ACCOUNT)" \
    	--role="roles/secretmanager.secretAccessor"

gcloud-logs: ## View Docker container logs
	gcloud run services logs $(SERVICE_NAME) --project $(PROJECT_ID) --region $(REGION)

gcloud-test: ## Run a basic health check
	@echo "Testing health check on https://$(SERVICE_NAME)-$(PROJECT_NUMBER).$(REGION).run.app" && \
	curl -X GET https://$(SERVICE_NAME)-$(PROJECT_NUMBER).$(REGION).run.app/health | python -m json.tool

gcloud-test-full: ## Run a full conversion test
	@echo "Testing full conversion process with image ID: ${TEST_IMAGE_ID}-"
	@set -a && . ./.env && set +a && curl -X POST https://$(SERVICE_NAME)-$(PROJECT_NUMBER).$(REGION).run.app/convert \
		-H "Content-Type: application/json" \
		-H "X-API-Key: $$(grep API_KEY .env | cut -d '=' -f2)" \
		-d "{\"sentinel_id\": \"${TEST_IMAGE_ID}\"}"

# CODE QUALITY SECTION
.PHONY: format lint check-all

format: ## Format code using black and isort
	@echo "Formatting code..."
	black . --line-length=100
	isort . --profile black --filter-files

lint: ## Run code linting (black, flake8, isort)
	black .
	flake8 . --max-line-length=100
	isort .

check-all: format lint ## Run all code quality checks
	@echo "All code quality checks completed"

# Note: To bypass pre-commit hooks when committing, use: git commit --no-verify

# Combined Commands
.PHONY: deploy
deploy: create-secrets docker-build gcloud-build gcloud-deploy ## Full deployment process: create secrets, build and deploy
