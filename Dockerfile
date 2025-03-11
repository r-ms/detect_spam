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
RUN python3.12 -m ensurepip && pip3 install --upgrade pip

# Create app directory
WORKDIR /app

# Install required packages
RUN pip install --no-cache-dir fastapi uvicorn pydantic requests diskcache

# Copy script to container
COPY spam_detector.py /app/

# Expose port for API
EXPOSE 8040

# Create symlink so python command works
RUN ln -sf /usr/local/bin/python3.12 /usr/local/bin/python

# Run the service
CMD ["python", "-m", "uvicorn", "spam_detector:app", "--host", "0.0.0.0", "--port", "8000"]