# Multi-stage Dockerfile for Orange Systems Sales Intelligence Platform
# Build stage
FROM python:3.11-slim as builder

WORKDIR /install

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Final runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies (libpq for postgresql, curl for healthchecks, libgomp1 for LightGBM OpenMP)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed dependencies from builder
COPY --from=builder /install /usr/local

# Create non-root user
RUN groupadd -g 1001 appuser && useradd -u 1001 -g appuser -m -s /bin/bash appuser

# Copy application source code
COPY bifidok_be /app/bifidok_be

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/bifidok_be:/app \
    PORT=8000

# Set ownership
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Health check probing /healthz
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/healthz || exit 1

CMD ["sh", "-c", "uvicorn bifidok_be.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
