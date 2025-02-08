# Makefile for Web

.PHONY: help install run build clean test all use-dev use-prod config

# Default target
.DEFAULT_GOAL := help

# Help command
help:  ## Display this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@awk -F '##' '/^[a-zA-Z_-]+:.*?##/ { printf "  %-15s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# Main commands
install: ## Install dependencies
	@echo "Installing dependencies..."
	npm install

run-dev: install use-dev ## Run development server
	@echo "Starting development server..."
	npm run dev

run-prod: install use-prod ## Run production build and preview
	@echo "Starting production server..."
	npm run build
	npm run preview

build: install use-prod ## Build for production
	@echo "Building for production..."
	npm run build

clean: ## Clean build artifacts
	@echo "Cleaning build artifacts..."
	rm -rf dist
	rm -rf node_modules


# Environment commands
use-dev: ## Switch to development environment (local API)
	@echo "Switching to development environment..."
	@cp .env.development .env
	@make config

use-prod: ## Switch to production environment (CloudRun API)
	@echo "Switching to production environment..."
	@cp .env.production .env
	@make config

config: ## Show current environment configuration
	@echo "\nCurrent Environment Configuration:"
	@echo "--------------------------------"
	@if [ "$$(cat .env | grep VITE_ENV | cut -d'=' -f2)" = "production" ]; then \
		echo "Environment: PRODUCTION"; \
		echo "API URL: $$(cat .env | grep VITE_API_URL | cut -d'=' -f2)"; \
		echo "WS URL:  $$(cat .env | grep VITE_WS_URL | cut -d'=' -f2)"; \
		echo "COGGER URL:  $$(cat .env | grep VITE_COGGER_URL | cut -d'=' -f2)"; \
		echo "TITILER URL:  $$(cat .env | grep VITE_TITILER_URL | cut -d'=' -f2)"; \
	else \
		echo "Environment: DEVELOPMENT"; \
		echo "API URL: $$(cat .env | grep VITE_API_URL | cut -d'=' -f2)"; \
		echo "WS URL:  $$(cat .env | grep VITE_WS_URL | cut -d'=' -f2)"; \
		echo "COGGER URL:  $$(cat .env | grep VITE_COGGER_URL | cut -d'=' -f2)"; \
		echo "TITILER URL:  $$(cat .env | grep VITE_TITILER_URL | cut -d'=' -f2)"; \
	fi
	@echo "--------------------------------\n"

all: install build run-dev ## Install dependencies, build and start the development server
