FROM ubuntu:20.04

WORKDIR /app

# Avoid interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install Python and other dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Use Python 3 as default
RUN ln -s /usr/bin/python3 /usr/bin/python

# Install vllm for CPU
RUN pip3 install --no-cache-dir vllm

# Install additional libraries
RUN pip3 install --no-cache-dir fastapi uvicorn pydantic

# Copy script to container
COPY spam_detector.py /app/

# Expose port for API
EXPOSE 8040

# Run the service
CMD ["python", "spam_detector.py"]