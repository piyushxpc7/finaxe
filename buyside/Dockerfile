# Stage 1: Build dependency environment
FROM python:3.11-slim AS builder

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy dependency specifications
COPY pyproject.toml poetry.lock* ./

# Generate requirements and install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi --only main

# Stage 2: Lightweight runtime image
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production

# Copy installed Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy codebase
COPY src/ ./src
COPY pyproject.toml ./

# Install project in editable/metadata mode without reinstalling dependencies
RUN pip install --no-deps -e .

EXPOSE 8000

# Run uvicorn server
CMD ["uvicorn", "buyside.main:app", "--host", "0.0.0.0", "--port", "8000"]
