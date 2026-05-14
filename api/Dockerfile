# ── Base image ────────────────────────────────────────────────────────────────
# python:3.11-slim is a minimal Debian Linux image with Python 3.11 pre-installed.
# "slim" omits unnecessary system packages — keeps the image small (~150MB vs ~1GB).
# Pinned to 3.11 to match the conda environment in environment.yml.
FROM python:3.11-slim

# ── Working directory ─────────────────────────────────────────────────────────
# All subsequent commands run from /app inside the container.
# This is the standard convention for Python web applications.
WORKDIR /app

# ── Install dependencies ──────────────────────────────────────────────────────
# Copy requirements.txt first, before copying application code.
# Docker caches each build step — if requirements.txt hasn't changed,
# Docker reuses the cached pip install layer and skips it on the next build.
# This makes rebuilds after code-only changes significantly faster.
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy application code ─────────────────────────────────────────────────────
# Copy the api/ directory into /app/api/ inside the container.
# Done after pip install to maximise Docker layer caching.
COPY api/ ./api/

# ── Port ──────────────────────────────────────────────────────────────────────
# Cloud Run injects the PORT environment variable and expects the container
# to listen on it. Cloud Run always routes traffic to port 8080 externally,
# but the internal port is configurable. We hardcode 8080 to match.
EXPOSE 8080

# ── Startup command ───────────────────────────────────────────────────────────
# Runs uvicorn when the container starts.
# --host 0.0.0.0: listen on all network interfaces (required inside a container)
# --port 8080: match Cloud Run's expected port
# --workers 1: single worker is sufficient for Cloud Run's concurrency model
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]