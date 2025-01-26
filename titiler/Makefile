# Variables
PROJECT_ID := deep-learning-earth
SERVICE_NAME := sentinel2-titiler
REGION := europe-west1
SA_KEY_FILE := deep-learning-earth-d9ea763f10c9.json

.PHONY: build run deploy clean

build:
	docker build -t $(SERVICE_NAME) .

run: build
	docker run -p 8282:8080 \
		-e PORT=8080 \
		-e GCP_PROJECT="$(PROJECT_ID)" \
		-e GCS_BUCKET_NAME="dl4eo-sentinel2-cogs" \
		-v "${PWD}/$(SA_KEY_FILE):/app/credentials.json:ro" \
		-e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
		$(SERVICE_NAME)

deploy:
	gcloud run deploy $(SERVICE_NAME) \
		--source . \
		--project $(PROJECT_ID) \
		--region $(REGION) \
		--platform managed \
		--allow-unauthenticated

clean:
	docker system prune -f
