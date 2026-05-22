#!/bin/sh
# AniPulse backend startup script (for Railway / any container runtime).
#
# This script exists because chaining `verify_deps.py` and `uvicorn` in
# a single `sh -c "..."` startCommand was failing silently in production
# (verify_deps.py would finish, but uvicorn would never start). Putting
# the logic in a real script gives us:
#   - explicit error-trapping at every step
#   - clear, line-buffered logs in the Railway dashboard
#   - one source of truth that works under Docker CMD and Railway
#     startCommand alike.
set -u  # treat unset vars as errors
# Note: we deliberately do NOT use `set -e` because verify_deps.py is
# best-effort -- a non-zero exit there must not stop uvicorn.

PORT="${PORT:-8000}"

echo "============================================================"
echo " AniPulse backend startup script"
echo " time:        $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo " cwd:         $(pwd)"
echo " PORT (env):  ${PORT}"
echo " PATH:        ${PATH}"
echo "============================================================"

echo "[start.sh] Running verify_deps.py (best-effort)..."
python verify_deps.py || echo "[start.sh] verify_deps.py exited non-zero -- continuing anyway"

echo "[start.sh] Locating uvicorn binary..."
UVICORN_BIN="$(command -v uvicorn || true)"
if [ -z "${UVICORN_BIN}" ]; then
    echo "[start.sh] ERROR: 'uvicorn' not found on PATH. Falling back to 'python -m uvicorn'."
    UVICORN_CMD="python -m uvicorn"
else
    echo "[start.sh] uvicorn binary: ${UVICORN_BIN}"
    UVICORN_CMD="${UVICORN_BIN}"
fi

echo "[start.sh] Launching: ${UVICORN_CMD} server:app --host 0.0.0.0 --port ${PORT} --workers 1 --log-level info --timeout-keep-alive 65"
echo "[start.sh] ---- uvicorn output begins ----"

# `exec` replaces this shell with uvicorn so SIGTERM goes straight to it.
exec ${UVICORN_CMD} server:app \
    --host 0.0.0.0 \
    --port "${PORT}" \
    --workers 1 \
    --log-level info \
    --timeout-keep-alive 65
