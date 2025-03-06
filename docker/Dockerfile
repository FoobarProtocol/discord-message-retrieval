# Use Alpine Linux as base image
FROM python:3.10-alpine

# Set working directory
WORKDIR /app

# Add labels
LABEL maintainer="Your Name <your.email@example.com>"
LABEL description="Discord RAG Bot - AI-powered message retrieval and analysis"
LABEL version="0.1.0"

# Install system dependencies
# - build-base: Needed for compiling some Python packages
# - libpq-dev: Needed for PostgreSQL client
# - libffi-dev: Needed for cryptography
# - openssl-dev: Also needed for cryptography packages 
RUN apk add --no-cache \
    build-base \
    postgresql-dev \
    libffi-dev \
    openssl-dev

# Create non-root user for security
RUN addgroup -S botuser && adduser -S -G botuser botuser

# Set up virtual environment
RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code (owned by botuser)
COPY --chown=botuser:botuser . .

# Create directory for logs with proper permissions
RUN mkdir -p /app/logs && \
    chown -R botuser:botuser /app/logs

# Switch to non-root user
USER botuser

# Create a healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Set up environment variables with defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DISCORD_BOT_TOKEN="" \
    DB_HOST="postgres" \
    DB_PORT="5432" \
    DB_USER="postgres" \
    DB_PASSWORD="postgres" \
    DB_NAME="discord_rag" \
    LOG_LEVEL="INFO"

# Run the bot
CMD ["python", "-m", "src.main"]
