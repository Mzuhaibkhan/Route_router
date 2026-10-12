# ==============================================================================
# Stage 1: Build Frontend React SPA
# ==============================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy dependency manifests first for efficient layer caching
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install

# Copy frontend source code and compile production Vite bundle
COPY frontend/ ./
RUN npm run build

# ==============================================================================
# Stage 2: Python Backend & Production Runtime for Render
# ==============================================================================
FROM python:3.12-slim AS runner

# Prevent Python from writing .pyc files and enable unbuffered output streaming
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000 \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

# Install runtime dependencies (curl for container health check)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install backend Python dependencies
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend application source code
COPY backend/ /app/backend/

# Copy compiled frontend assets from Stage 1 into expected directory
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Collect static files into backend/staticfiles for WhiteNoise
RUN python backend/manage.py collectstatic --noinput

# Expose Render web service port
EXPOSE 10000

# Container healthcheck targeting lightweight /healthz endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-10000}/healthz || exit 1

# Start Gunicorn binding dynamically to Render $PORT
CMD ["sh", "-c", "gunicorn config.wsgi:application --chdir backend --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 4 --timeout 120"]
