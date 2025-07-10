# Multi-stage build for production optimization
FROM python:3.12-slim-bookworm AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Development stage
FROM base AS development

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command for development
CMD ["python", "-m", "src.cli", "pipeline"]

# Production stage
FROM base AS production

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir supervisor

# Copy only necessary files
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser configs/ ./configs/
COPY --chown=appuser:appuser .env.example ./.env.example

# Create directories for logs and data
RUN mkdir -p /app/logs /app/data && \
    chown -R appuser:appuser /app/logs /app/data

# Copy supervisor configuration
COPY --chown=appuser:appuser configs/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Switch to non-root user
USER appuser

# Health check with actual application endpoint
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "from src.core.health import check_health; check_health()" || exit 1

# Expose port for future web interface
EXPOSE 8000

# Use supervisor for process management in production
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]