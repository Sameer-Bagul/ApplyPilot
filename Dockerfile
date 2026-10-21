# syntax=docker/dockerfile:1
# ApplyPilot End-to-End Container
# Autonomous AI Job Application Agent & Low-AI Scripting Engine

FROM python:3.12-slim-bookworm AS base

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PATH="/home/applypilot/.local/bin:${PATH}"

# Install minimal OS dependencies for compiling C-extensions and running Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    ca-certificates \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    fonts-liberation \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root user
RUN groupadd -g 1000 applypilot && \
    useradd -u 1000 -g applypilot -m -s /bin/bash applypilot

# Setup directories with proper permissions
RUN mkdir -p /ms-playwright \
    /home/applypilot/.applypilot \
    /home/applypilot/.gmail-mcp \
    /home/applypilot/data \
    /home/applypilot/app && \
    chown -R applypilot:applypilot /ms-playwright /home/applypilot

WORKDIR /home/applypilot/app

# Pre-install Playwright and Chromium browser engine
RUN pip install --upgrade pip setuptools wheel && \
    pip install playwright>=1.40.0 patchright>=1.50.0 && \
    playwright install --with-deps chromium && \
    chown -R applypilot:applypilot /ms-playwright

# Copy application and install ApplyPilot package
COPY --chown=applypilot:applypilot . .
RUN pip install .

# Setup entrypoint
COPY --chown=applypilot:applypilot docker/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Persist data volumes
VOLUME ["/home/applypilot/.applypilot", "/home/applypilot/.gmail-mcp"]

# Switch to non-root user
USER applypilot

# Expose ports: 8080 (Web Dashboard), 8000 (MCP Server HTTP transport)
EXPOSE 8080 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["status"]
