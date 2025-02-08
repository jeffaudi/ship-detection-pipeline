FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    gcc \
    g++ \
    python3-dev \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL environment variables
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR
ENV GDAL_HTTP_MERGE_CONSECUTIVE_RANGES=YES
ENV GDAL_HTTP_MULTIPLEX=YES
ENV GDAL_HTTP_VERSION=2
ENV VSI_CACHE=TRUE
ENV VSI_CACHE_SIZE=536870912

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app files
COPY app/ .

# Container configuration
EXPOSE 8080
ENV PORT=8080

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
