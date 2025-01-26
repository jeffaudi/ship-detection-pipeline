# Makefile for API

# Variables
PYTHON=python
FLASK=flask
PYTEST=pytest
ENV=development
PORT=5454

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

.PHONY: all install run test test-watch clean kill-port check-port
