# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
ENV POETRY_HOME="/opt/poetry" \
    POETRY_PATH="/opt/poetry/bin" \
    POETRY_VENV_IN_PROJECT=false \
    POETRY_CACHE_DIR=/tmp/poetry_cache

RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="$POETRY_PATH:$PATH"

# Configure Poetry for container use
RUN poetry config virtualenvs.create false

# Set working directory
WORKDIR /app

# Copy Poetry configuration files
COPY pyproject.toml poetry.lock ./

# Install dependencies (production only)
RUN poetry install --no-root --no-dev && rm -rf $POETRY_CACHE_DIR

# Create non-root user
RUN groupadd -r conport && useradd -r -g conport conport

# Copy source code
COPY src/ ./src/
COPY alembic.ini ./

# Install the project itself
RUN poetry install --no-dev

# Change ownership of the app directory to the conport user
RUN chown -R conport:conport /app

# Switch to non-root user
USER conport

# Set environment variables for the application
ENV PYTHONPATH="/app/src:$PYTHONPATH" \
    CONPORT_LOG_LEVEL=INFO \
    CONPORT_HOST=0.0.0.0 \
    CONPORT_PORT=8000

# Expose the default port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Set the entrypoint and default command
ENTRYPOINT ["python", "-m", "conport"]
CMD ["start"]

# Labels for metadata
LABEL org.opencontainers.image.title="NovaPort-MCP" \
      org.opencontainers.image.description="A robust, database-backed Model Context Protocol (MCP) server" \
      org.opencontainers.image.version="0.1.0-beta" \
      org.opencontainers.image.authors="Siroopfles <siroopfles@novaport.dev>" \
      org.opencontainers.image.source="https://github.com/novaport/novaport-mcp"