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
RUN mkdir -p /app/temp /app/logs /app/uploads /app/exports /app/temp/jobs /app/exports/jobs

# -----------------------------------------------------------------------------
# 5) Healthcheck
# -----------------------------------------------------------------------------
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/api/status" || exit 1

# -----------------------------------------------------------------------------
# 6) Startup
#    - Runs verify_deps.py first (logs ffmpeg/ffprobe versions, writes JSON
#      status to /app/logs/deps_status.json).  We DO NOT exit on failure here;
#      the API will return HTTP 503 with a clear message instead of crashing.
#    - Then launches uvicorn.
# -----------------------------------------------------------------------------
EXPOSE 8000

CMD ["sh", "-c", "python verify_deps.py || true; exec uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --log-level info"]
