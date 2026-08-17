FROM python:3.12-slim

# Install system dependencies (including ffmpeg and build essentials)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:0.6.5 /uv /uvx /bin/

WORKDIR /app

# Install project dependencies
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN uv pip install --system --no-cache -e .

# Copy scripts and migrations
COPY scripts/ ./scripts/
COPY alembic.ini ./
COPY migrations/ ./migrations/

# Create storage data directory
RUN mkdir -p /app/data/storage

EXPOSE 8000

CMD ["uvicorn", "src.api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
