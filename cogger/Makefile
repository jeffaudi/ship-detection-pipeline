.PHONY: build run deploy

# Configuration
GCP_PROJECT := deep-learning-earth
GCS_BUCKET_NAME := dl4eo-sentinel2-cogs
SERVICE_ACCOUNT := ship-detection-pipeline@deep-learning-earth.iam.gserviceaccount.com
TEST_IMAGE_ID := 5ba786ba-eda0-4174-8879-63406fb84804
SA_KEY_FILE := deep-learning-earth-d9ea763f10c9.json
SERVICE_NAME := sentinel2-cog-converter

build:
	docker build -t $(SERVICE_NAME) .

run: build
	set -a && . ./.env && set +a && docker run -p 8181:8080 \
		-e PORT=8181 \
		-e GCP_PROJECT="${GCP_PROJECT}" \
		-e GCS_BUCKET_NAME="${GCS_BUCKET_NAME}" \
		-e CDSE_USERNAME="$$CDSE_USERNAME" \
		-e CDSE_PASSWORD="$$CDSE_PASSWORD" \
		-v "${PWD}/${SA_KEY_FILE}:/app/credentials.json:ro" \
		-e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
		$(SERVICE_NAME)

shell: build
	@echo "Starting interactive shell in container..."
	set -a && . ./.env && set +a && docker run -it --rm \
		-e PORT=8181 \
		-e GCP_PROJECT="${GCP_PROJECT}" \
		-e GCS_BUCKET_NAME="${GCS_BUCKET_NAME}" \
		-e CDSE_USERNAME="$$CDSE_USERNAME" \
		-e CDSE_PASSWORD="$$CDSE_PASSWORD" \
		-v "${PWD}/${SA_KEY_FILE}:/app/credentials.json:ro" \
		-e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
		-v "${PWD}/app:/app/dev:ro" \
		$(SERVICE_NAME) /bin/bash

deploy:
	set -a && . ./.env && set +a && gcloud builds submit --tag gcr.io/${GCP_PROJECT}/sentinel-cog-converter && \
	gcloud run deploy $(SERVICE_NAME) \
		--image gcr.io/${GCP_PROJECT}/sentinel-cog-converter \
		--platform managed \
		--region europe-west1 \
		--service-account=${SERVICE_ACCOUNT} \
		--set-env-vars="GCS_BUCKET_NAME=${GCS_BUCKET_NAME},GCP_PROJECT=${GCP_PROJECT},CDSE_USERNAME=$$CDSE_USERNAME,CDSE_PASSWORD=$$CDSE_PASSWORD"

# Helper targets
.PHONY: test logs clean test-full test-env shell

test:
	curl http://localhost:8181/

test-full:
	@echo "Testing full conversion process with image ID: ${TEST_IMAGE_ID}"
	@set -a && . ./.env && set +a && curl -X POST http://localhost:8181/convert \
		-H "Content-Type: application/json" \
		-d "{\"sentinel_id\": \"${TEST_IMAGE_ID}\"}"

logs:
	docker logs $$(docker ps -q --filter ancestor=$(SERVICE_NAME))

clean:
	docker rm -f $$(docker ps -aq --filter ancestor=$(SERVICE_NAME)) 2>/dev/null || true

# Service account setup
.PHONY: setup-auth

setup-auth:
	@echo "Setting up service account authentication..."
	@if [ ! -f "${SA_KEY_FILE}" ]; then \
		gcloud iam service-accounts keys create ${SA_KEY_FILE} \
			--iam-account=${SERVICE_ACCOUNT}; \
	fi

test-env:
	@echo "Testing environment variables in container..."
	@CONTAINER_ID=$$(docker ps -q --filter ancestor=$(SERVICE_NAME)) && \
	if [ -z "$$CONTAINER_ID" ]; then \
		echo "No running container found. Please run 'make run' first."; \
		exit 1; \
	fi && \
	echo "\nCDSE variables:" && \
	docker exec $$CONTAINER_ID env | grep CDSE || true && \
	echo "\nGoogle Cloud variables:" && \
	docker exec $$CONTAINER_ID env | grep -E "GCP_|GCS_" || true && \
	echo "\nCredentials file:" && \
	docker exec $$CONTAINER_ID ls -l $$GOOGLE_APPLICATION_CREDENTIALS || true

# Code quality targets
.PHONY: format lint check-all

format:
	@echo "Formatting code..."
	black . --line-length=100
	isort . --profile black --filter-files

lint:
	@echo "Linting code..."
	flake8 . --max-line-length=100
	mypy .

check-all: format lint
	@echo "All code quality checks completed"

# Note: To bypass pre-commit hooks when committing, use: git commit --no-verify
