# Makefile for Web

# Variables
NPM=npm

# Default target
all: install run

# Install dependencies
install:
	$(NPM) install

# Run the development server
run:
	$(NPM) run dev

# Build the project for production
build:
	$(NPM) run build

# Clean up node_modules and build artifacts
clean:
	rm -rf node_modules
	rm -rf dist  # Adjust if your build output directory is different

# Run tests
test:
	$(NPM) test  # Adjust if you have a different test command
