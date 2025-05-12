# ===============================
# 🔧 Build Stage: Export from Poetry
# ===============================
FROM python:3.12-slim as build

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VERSION=1.8.3 \
    PATH="/opt/poetry/bin:$PATH"

WORKDIR /app

# Install Poetry + required system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry via official installer
RUN curl -sSL https://install.python-poetry.org | python3 -

# Copy lockfiles only
COPY pyproject.toml poetry.lock ./

# Export dependencies to requirements.txt
RUN poetry export --without-hashes --only main -f requirements.txt -o requirements.txt


# ===============================
# 🚀 Final Stage: Minimal Runtime
# ===============================
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 supervisor curl wget vim \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 --no-create-home appuser

# Copy exported requirements.txt from build stage
COPY --from=build /app/requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your app
COPY . .
COPY supervisord.conf /etc/supervisor/supervisord.conf

# Create Supervisor log dir
RUN mkdir -p /var/log/supervisor && \
    chown -R appuser:appgroup /var/log /var/log/supervisor && \
    chmod -R 755 /var/log/supervisor

USER appuser

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]

