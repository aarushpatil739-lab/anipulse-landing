# =============================================================================
# AniPulse Backend - Production Dockerfile
# =============================================================================
# This Dockerfile is the SOURCE OF TRUTH for the Railway production runtime.
# It installs the system-level `ffmpeg` and `ffprobe` binaries which are
# required by the rendering pipeline (services/ffmpeg_utils.py).
#
# Build context: ./backend
# Build command:  docker build -t anipulse-backend ./backend
# =============================================================================

FROM python:3.11-slim-bookworm

# Prevent interactive prompts during apt-get
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# -----------------------------------------------------------------------------
# 1) System dependencies
#    - ffmpeg            : required for trim/concat/transitions/export
#    - libsndfile1       : required by soundfile (librosa I/O backend)
#    - libgomp1          : required by numba / numpy runtime
#    - build-essential   : compile any pure-Python wheels that lack manylinux
#    - curl              : for healthchecks / debugging
# -----------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libsndfile1 \
        libsndfile1-dev \
        libgomp1 \
        build-essential \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && ffmpeg -version \
    && ffprobe -version

# -----------------------------------------------------------------------------
# 2) Application directory
# -----------------------------------------------------------------------------
WORKDIR /app

# -----------------------------------------------------------------------------
# 3) Python dependencies (cached separately from app source)
# -----------------------------------------------------------------------------
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r /app/requirements.txt

# -----------------------------------------------------------------------------
# 4) Application source
# -----------------------------------------------------------------------------
COPY . /app

# Pre-create runtime directories so non-root users (Railway) can write
RUN mkdir -p /app/temp /app/logs /app/uploads /app/exports /app/temp/jobs /app/exports/jobs \
    && chmod +x /app/start.sh

# -----------------------------------------------------------------------------
# 5) Healthcheck
# -----------------------------------------------------------------------------
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/api/status" || exit 1

# -----------------------------------------------------------------------------
# 6) Startup
#    The /app/start.sh script handles verify_deps.py + uvicorn launch
#    with proper line-buffered logging and error handling. It is the
#    SINGLE source of truth for how the process starts (used by both
#    Docker CMD and Railway startCommand).
# -----------------------------------------------------------------------------
EXPOSE 8000

CMD ["/app/start.sh"]
