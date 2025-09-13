# Backyard Swarm Coordinator
# Ray cluster head + FastAPI REST service + MinIO integration
FROM python:3.11-slim

LABEL maintainer="backyard-swarm"
LABEL description="Coordinator service for distributed GPU mesh"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy coordinator source code
COPY src/coordinator/ ./coordinator/

# Create data directories
RUN mkdir -p /data /models

# Expose ports
EXPOSE 8080 8265 10001

# Environment variables with sensible defaults
ENV PYTHONUNBUFFERED=1
ENV RAY_HEAD_PORT=10001
ENV API_PORT=8080
ENV STORAGE_URL=http://minio:9000
ENV STORAGE_BUCKET=backyard
ENV STORAGE_ACCESS=minio
ENV STORAGE_SECRET=minio123

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/healthz || exit 1

# Run coordinator service
CMD ["python", "coordinator/main.py"]