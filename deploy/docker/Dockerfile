# ==========================================
# Kairo Production API Dockerfile
# Multi-stage, non-root, hardened runtime
# ==========================================

# Stage 1: Dependency Builder
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Production Hardened Runner
FROM python:3.12-slim AS runner

ARG GIT_SHA=unknown
ARG BUILD_TIMESTAMP=unknown

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/install/lib/python3.12/site-packages:/app" \
    GIT_SHA=${GIT_SHA} \
    BUILD_TIMESTAMP=${BUILD_TIMESTAMP} \
    ENVIRONMENT=production

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dedicated non-root user and group
RUN groupadd -g 1000 kairo && \
    useradd -u 1000 -g kairo -s /bin/bash -m kairo

# Copy installed dependencies from builder stage
COPY --from=builder /install /install

# Copy application source code (excluding tests, docs, envs via .dockerignore)
COPY --chown=kairo:kairo backend/app /app/app
COPY --chown=kairo:kairo backend/alembic.ini /app/alembic.ini

# Switch to non-root user
USER kairo

EXPOSE 8000

# Docker healthcheck probe targeting liveness endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Production execution without reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
