FROM debian:10

# Install dependencies including OpenSSL
RUN apt-get update && apt-get install -y \
    wget \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libncurses5-dev \
    libncursesw5-dev \
    libreadline-dev \
    libsqlite3-dev \
    libgdbm-dev \
    libdb5.3-dev \
    libbz2-dev \
    libexpat1-dev \
    liblzma-dev \
    libffi-dev \
    openssl \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Download and install Python 3.12
WORKDIR /tmp
RUN wget https://www.python.org/ftp/python/3.12.0/Python-3.12.0.tgz \
    && tar xzf Python-3.12.0.tgz \
    && cd Python-3.12.0 \
    && ./configure --enable-optimizations \
    && make -j $(nproc) \
    && make install \
    && cd .. \
    && rm -rf Python-3.12.0 Python-3.12.0.tgz

# Install pip and upgrade it
RUN python3.12 -m ensurepip && python3.12 -m pip install --upgrade pip

# Create proper symlinks for Python
RUN ln -sf /usr/local/bin/python3.12 /usr/local/bin/python3 && \
    ln -sf /usr/local/bin/python3 /usr/local/bin/python && \
    ln -sf /usr/local/bin/pip3.12 /usr/local/bin/pip3 && \
    ln -sf /usr/local/bin/pip3 /usr/local/bin/pip

# Verify Python installation
RUN python --version && pip --version

# Create app directory
WORKDIR /app

# Install Hugging Face hub and transformers instead of vllm
RUN pip install --no-cache-dir huggingface_hub transformers accelerate

# Install additional libraries
RUN pip install --no-cache-dir fastapi uvicorn pydantic

# Copy script to container
COPY spam_detector.py /app/

# Expose port for API
EXPOSE 8040

# Set environment variable placeholder for HF token
ENV HF_TOKEN=""

# Run the service
CMD ["python", "spam_detector.py"]