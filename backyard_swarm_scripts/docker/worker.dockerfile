# Backyard Swarm Worker
# Ray worker + GPU detection + PyTorch + CUDA runtime
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

LABEL maintainer="backyard-swarm"
LABEL description="GPU worker node for distributed AI mesh"

# Install system dependencies including nvidia-ml-py requirements
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy worker source code
COPY src/worker/ ./worker/

# Copy job scripts for local execution
COPY jobs/ ./jobs/

# Create data directories
RUN mkdir -p /data /models

# Environment variables with sensible defaults
ENV PYTHONUNBUFFERED=1
ENV COORD_ADDR=http://coordinator:8080
ENV NODE_NAME=worker
ENV HEARTBEAT_INTERVAL=30

# GPU environment variables
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Ensure CUDA is available
ENV PATH="/usr/local/cuda/bin:${PATH}"
ENV LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH}"

# Health check - verify worker can connect to coordinator
HEALTHCHECK --interval=60s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('${COORD_ADDR}/healthz', timeout=5)" || exit 1

# Run worker service
CMD ["python", "worker/main.py"]