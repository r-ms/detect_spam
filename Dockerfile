FROM python:3.10-slim

WORKDIR /app

# Install required dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install vllm for CPU
RUN pip install --no-cache-dir vllm

# Install additional libraries
RUN pip install --no-cache-dir fastapi uvicorn pydantic

# Copy script to container
COPY spam_detector.py /app/

# Expose port for API
EXPOSE 8040

# Run the service
CMD ["python", "spam_detector.py"]