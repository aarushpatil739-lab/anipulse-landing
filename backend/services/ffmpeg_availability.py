"""
FFmpeg availability check (process-wide, cached).

We resolve `ffmpeg` and `ffprobe` once at import time, log the result, and
expose helpers used by both the HTTP layer (to return HTTP 503) and the
background worker (to mark jobs as failed with a clear message).

This module deliberately has *no* heavy imports so it is safe to import
from anywhere in the codebase, including startup paths.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BinaryStatus:
    """Resolved status for a single binary."""
    name: str
    available: bool
    path: Optional[str]
    version: Optional[str]
    error: Optional[str]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "available": self.available,
            "path": self.path,
            "version": self.version,
            "error": self.error,
        }


class FFmpegBinaryMissingError(RuntimeError):
    """Raised when ffmpeg/ffprobe binaries are not installed in the runtime.

    The HTTP layer catches this and returns HTTP 503; the worker catches it
    and marks the job as failed with an actionable message.
    """

    def __init__(self, message: str, missing: list[str] | None = None):
        super().__init__(message)
        self.missing = missing or []


def _probe_binary(name: str) -> BinaryStatus:
    path = shutil.which(name)
    if not path:
        return BinaryStatus(
            name=name,
            available=False,
            path=None,
            version=None,
            error=f"`{name}` binary not found on PATH",
        )
    try:
        result = subprocess.run(
            [name, "-version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0:
            tail = (result.stderr or result.stdout or "").strip()[-200:]
            return BinaryStatus(
                name=name,
                available=False,
                path=path,
                version=None,
                error=f"`{name} -version` exit={result.returncode}: {tail}",
            )
        version = (result.stdout or "").splitlines()[0] if result.stdout else ""
        return BinaryStatus(name=name, available=True, path=path, version=version, error=None)
    except subprocess.TimeoutExpired:
        return BinaryStatus(name=name, available=False, path=path, version=None, error="timeout running -version")
    except Exception as exc:  # noqa: BLE001
        return BinaryStatus(name=name, available=False, path=path, version=None, error=str(exc))


# Resolved exactly once per process. Re-importing this module always returns
# the same cached snapshot, which is what we want for stable behaviour.
FFMPEG_STATUS: BinaryStatus = _probe_binary("ffmpeg")
FFPROBE_STATUS: BinaryStatus = _probe_binary("ffprobe")

if FFMPEG_STATUS.available and FFPROBE_STATUS.available:
    logger.info(
        "FFmpeg toolchain OK | ffmpeg=%s | ffprobe=%s",
        FFMPEG_STATUS.version,
        FFPROBE_STATUS.version,
    )
else:
    logger.error(
        "FFmpeg toolchain MISSING/BROKEN | ffmpeg.available=%s (err=%s) | ffprobe.available=%s (err=%s)",
        FFMPEG_STATUS.available,
        FFMPEG_STATUS.error,
        FFPROBE_STATUS.available,
        FFPROBE_STATUS.error,
    )


def is_available() -> bool:
    """True iff both ffmpeg and ffprobe are usable in this process."""
    return FFMPEG_STATUS.available and FFPROBE_STATUS.available


def missing_binaries() -> list[str]:
    missing: list[str] = []
    if not FFMPEG_STATUS.available:
        missing.append("ffmpeg")
    if not FFPROBE_STATUS.available:
        missing.append("ffprobe")
    return missing


def ensure_available() -> None:
    """Raise FFmpegBinaryMissingError if the toolchain is not usable."""
    if is_available():
        return
    missing = missing_binaries()
    raise FFmpegBinaryMissingError(
        (
            f"Required system binaries missing: {', '.join(missing)}. "
            "The backend container is misconfigured: please ensure `ffmpeg` "
            "(which provides both `ffmpeg` and `ffprobe`) is installed in the runtime image. "
            "See backend/Dockerfile."
        ),
        missing=missing,
    )


def status_dict() -> dict:
    """Serialisable snapshot for the /api/health/ffmpeg endpoint."""
    return {
        "available": is_available(),
        "missing": missing_binaries(),
        "ffmpeg": FFMPEG_STATUS.to_dict(),
        "ffprobe": FFPROBE_STATUS.to_dict(),
    }
