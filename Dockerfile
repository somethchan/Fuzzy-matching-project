FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip 
RUN python3 -m pip install --upgrade pip

# Install Python dependencies
RUN python3 -m pip install --no-cache-dir \
    pandas \
    rapidfuzz

# Create working directory
WORKDIR /workspace

# Default command
CMD [ "bash" ]
