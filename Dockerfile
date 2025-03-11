FROM python:3.12-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install required packages
RUN pip install --no-cache-dir fastapi uvicorn pydantic requests diskcache

# Copy script to container
COPY spam_detector.py /app/

# Expose port for API
EXPOSE 8040

# Run the service
CMD ["python", "-m", "uvicorn", "spam_detector:app", "--host", "0.0.0.0", "--port", "8000"]