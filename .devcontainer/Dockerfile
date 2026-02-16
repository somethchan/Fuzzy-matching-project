FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER root

# Install Python tooling
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Create venv (avoids Ubuntu 24.04 pip restrictions)
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install deps in venv
RUN pip install --no-cache-dir -U pip \
 && pip install --no-cache-dir pandas rapidfuzz

USER vscode
WORKDIR /workspace
