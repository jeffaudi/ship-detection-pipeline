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
SERVICE_NAME := ship-pipeline-titiler
IMAGE_NAME := ship-pipeline-titiler
TAG := latest
REGION := europe-west1
SA_KEY_FILE := deep-learning-earth-d9ea763f10c9.json

# Secret names in Google Cloud Secret Manager
SUPABASE_URL_SECRET := ship-pipeline-supabase-url
SUPABASE_KEY_SECRET := ship-pipeline-supabase-key
API_KEY_SECRET := ship-pipeline-api-key
GOOGLE_APPLICATION_CREDENTIALS_SECRET := ship-pipeline-google-application-credentials
## LOCAL DEVELOPMENT SECTION

install: ## Install the dependencies
	pip install -r requirements.txt

.PHONY: dev
dev: ## Start the development server with auto-reload
	cd app && \
	export GOOGLE_APPLICATION_CREDENTIALS=$(PWD)/$(SA_KEY_FILE) && \
	uvicorn main:app --reload --port 8282

# Helper targets
.PHONY: test logs clean test-env shell docker-test docker-test-full

test: ## Run a basic health check
	@echo "Testing health check..." && \
	curl -s http://localhost:8282/health | python -m json.tool && \
	echo "\nChecking service status..." && \
	curl -s http://localhost:8282/health | grep -q '"status":"healthy"' && \
	echo "✅ Health check passed" || \
	(echo "❌ Health check failed" && exit 1)
	@echo "\nChecking individual services:" && \
	(curl -s http://localhost:8282/health | grep -q '"google_storage":true' && \
		echo "✅ Google Storage: Connected" || \
		echo "❌ Google Storage: Failed") && \
	(curl -s http://localhost:8282/health | grep -q '"supabase":true' && \
		echo "✅ Supabase: Connected" || \
		echo "❌ Supabase: Failed")

test-full: ## Run a full test of the TiTiler endpoints
	@echo "\nTesting TiTiler status endpoint..."
	@set -a && . ./.env && set +a && curl -s "http://localhost:8282/cog/status/b9f42c7b-13ab-484d-ab65-a994ad79441c" \
		-H "Content-Type: application/json" \
		-H "X-API-Key: $$(grep API_KEY .env | cut -d '=' -f2)" | python -m json.tool
	@echo "\nTesting TiTiler info endpoint..."
	@set -a && . ./.env && set +a && curl -s "http://localhost:8282/cog/info/$(GCS_BUCKET_NAME)/cogs/b9f42c7b-13ab-484d-ab65-a994ad79441c_rgb.tif" \
		-H "Content-Type: application/json" \
		-H "X-API-Key: $$(grep API_KEY .env | cut -d '=' -f2)" | python -m json.tool

## DOCKER SECTION

# Docker Commands
.PHONY: docker-build
docker-build: ## Build the Docker image
	docker build -t $(IMAGE_NAME):$(TAG) .

.PHONY: docker-run
docker-run: ## Run the Docker container locally
	docker run -p 8282:8080 \
		--env-file .env \
		--env GCS_BUCKET_NAME=$(GCS_BUCKET_NAME) \
		--env GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
		-v $(PWD)/$(SA_KEY_FILE):/app/credentials.json \
		$(IMAGE_NAME):$(TAG)

.PHONY: docker-run-dev
docker-run-dev: ## Run the Docker container in development mode with hot reload
	docker run -p 8282:8080 \
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
	curl -s http://localhost:8282/health | python -m json.tool && \
	curl -s http://localhost:8282/health | grep -q '"status":"healthy"' && \
	echo "✅ Health check passed" || \
	(echo "❌ Health check failed" && exit 1)

docker-test-full: ## Run a full test against the Docker container
	@CONTAINER_ID=$$(docker ps -q --filter ancestor=$(IMAGE_NAME):$(TAG)) && \
	if [ -z "$$CONTAINER_ID" ]; then \
		echo "No running container found. Please run 'make docker-run' first."; \
		exit 1; \
	fi && \
	echo "\nTesting TiTiler endpoints in Docker container..." && \
	curl -s "http://localhost:8282/cog/info/$(GCS_BUCKET_NAME)/cogs/b9f42c7b-13ab-484d-ab65-a994ad79441c_rgb.tif" \
		-H "X-API-Key: $$(grep API_KEY .env | cut -d '=' -f2)" | \
	python -m json.tool

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
	echo "\nGoogle Cloud settings:" && \
	docker exec $$CONTAINER_ID env | grep -E "PROJECT_ID|GCS_" || true && \
	echo "\nAPI configuration:" && \
	docker exec $$CONTAINER_ID env | grep API_KEY | sed 's/\(API_KEY=\).*/\1****/' || true && \

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
		echo "$$SUPABASE_URL" | gcloud secrets create $(SUPABASE_URL_SECRET) --data-file=- --project $(PROJECT_ID) || \
		echo "$$SUPABASE_URL" | gcloud secrets versions add $(SUPABASE_URL_SECRET) --data-file=- --project $(PROJECT_ID) && \
		echo "Creating/updating SUPABASE_KEY secret..." && \
		echo "$$SUPABASE_KEY" | gcloud secrets create $(SUPABASE_KEY_SECRET) --data-file=- --project $(PROJECT_ID) || \
		echo "$$SUPABASE_KEY" | gcloud secrets versions add $(SUPABASE_KEY_SECRET) --data-file=- --project $(PROJECT_ID) && \
		echo "Creating/updating API_KEY secret..." && \
		echo "$$API_KEY" | tr -d '\n\r' | xargs | gcloud secrets create $(API_KEY_SECRET) --data-file=- --project $(PROJECT_ID) || \
		echo "$$API_KEY" | tr -d '\n\r' | xargs | gcloud secrets versions add $(API_KEY_SECRET) --data-file=- --project $(PROJECT_ID); \
		echo "Creating/updating GOOGLE_APPLICATION_CREDENTIALS secret..." && \
		cat "$$GOOGLE_APPLICATION_CREDENTIALS" | gcloud secrets create $(GOOGLE_APPLICATION_CREDENTIALS_SECRET) --data-file=- --project $(PROJECT_ID) || \
		cat "$$GOOGLE_APPLICATION_CREDENTIALS" | gcloud secrets versions add $(GOOGLE_APPLICATION_CREDENTIALS_SECRET) --data-file=- --project $(PROJECT_ID); \	else \
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
		--memory 1Gi \
		--cpu 1 \
		--min-instances 1 \
		--max-instances 20 \
		--concurrency 80 \
		--cpu-boost \
		--set-env-vars="GCS_BUCKET_NAME=$(GCS_BUCKET_NAME)" \
		--set-secrets="API_KEY=$(API_KEY_SECRET):latest" \
		--set-secrets="SUPABASE_URL=$(SUPABASE_URL_SECRET):latest" \
		--set-secrets="SUPABASE_KEY=$(SUPABASE_KEY_SECRET):latest"

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

gcloud-logs: ## View Cloud Run logs
	gcloud run services logs $(SERVICE_NAME) --project $(PROJECT_ID) --region $(REGION)

gcloud-test: ## Run a basic health check
	@echo "Testing health check on https://$(SERVICE_NAME)-$(PROJECT_NUMBER).$(REGION).run.app" && \
	curl -s -X GET https://$(SERVICE_NAME)-$(PROJECT_NUMBER).$(REGION).run.app/health | python -m json.tool

gcloud-test-full: ## Run a full test of the endpoints
	@echo "\nTesting TiTiler endpoints on Cloud Run..."
	@set -a && . ./.env && set +a && curl -s "https://$(SERVICE_NAME)-$(PROJECT_NUMBER).$(REGION).run.app/cog/info/$(GCS_BUCKET_NAME)/cogs/b9f42c7b-13ab-484d-ab65-a994ad79441c_rgb.tif" \
		-H "X-API-Key: $$(grep API_KEY .env | cut -d '=' -f2)" | \
	python -m json.tool

gcloud-deploy-full: gcloud-build gcloud-deploy gcloud-test-full


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

# Combined Commands
.PHONY: deploy
deploy: create-secrets docker-build gcloud-build gcloud-deploy ## Full deployment process: create secrets, build and deploy
