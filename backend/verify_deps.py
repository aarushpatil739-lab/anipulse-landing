#!/usr/bin/env python3
"""
Startup verification script for the AniPulse backend.

Responsibilities
----------------
1. Verify all Python dependencies can be imported.
2. Verify the `ffmpeg` and `ffprobe` system binaries are available,
   logging their resolved paths and full version banners.
3. Persist the verification result to `/app/backend/logs/deps_status.json`
   so the running API process (and the /api/health/ffmpeg endpoint) can
   surface a clear, structured status to clients without re-shelling out.
4. NEVER exits non-zero in production: a missing system binary must not
   crash the container. The API itself will return HTTP 503 with a clear
   message until the issue is resolved.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(os.environ.get("ANIPULSE_LOG_DIR", "/app/backend/logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)
STATUS_FILE = LOG_DIR / "deps_status.json"


def _banner(title: str) -> None:
    print("=" * 70)
    print(f" {title}")
    print("=" * 70)


def check_python_module(module_name: str, display_name: str | None = None) -> dict:
    display_name = display_name or module_name
    try:
        __import__(module_name)
        version = "unknown"
        try:
            mod = sys.modules[module_name]
            version = getattr(mod, "__version__", "unknown")
        except Exception:
            pass
        print(f"  [ok]   {display_name:<28} (version={version})")
        return {"name": display_name, "ok": True, "version": version, "error": None}
    except Exception as exc:  # noqa: BLE001
        print(f"  [FAIL] {display_name:<28} -> {exc}")
        return {"name": display_name, "ok": False, "version": None, "error": str(exc)}


def check_system_binary(cmd: str) -> dict:
    path = shutil.which(cmd)
    if not path:
        print(f"  [FAIL] {cmd:<10} -> binary NOT FOUND on PATH")
        return {"name": cmd, "ok": False, "path": None, "version": None, "error": "binary not found on PATH"}

    try:
        result = subprocess.run(
            [cmd, "-version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0:
            tail = (result.stderr or result.stdout or "")[-300:]
            print(f"  [FAIL] {cmd:<10} -> returncode={result.returncode}, output_tail={tail!r}")
            return {
                "name": cmd,
                "ok": False,
                "path": path,
                "version": None,
                "error": f"{cmd} -version returned {result.returncode}",
            }
        first_line = (result.stdout or "").splitlines()[0] if result.stdout else ""
        print(f"  [ok]   {cmd:<10} -> {path}")
        print(f"           {first_line}")
        return {"name": cmd, "ok": True, "path": path, "version": first_line, "error": None}
    except subprocess.TimeoutExpired:
        print(f"  [FAIL] {cmd:<10} -> timeout running '{cmd} -version'")
        return {"name": cmd, "ok": False, "path": path, "version": None, "error": "timeout"}
    except Exception as exc:  # noqa: BLE001
        print(f"  [FAIL] {cmd:<10} -> {exc}")
        return {"name": cmd, "ok": False, "path": path, "version": None, "error": str(exc)}


def main() -> int:
    started = datetime.now(timezone.utc).isoformat()
    _banner("AniPulse Backend - Startup Verification")
    print(f"Time:        {started}")
    print(f"Python:      {sys.version.split()[0]} ({sys.executable})")
    print(f"Working dir: {os.getcwd()}")
    print(f"PATH:        {os.environ.get('PATH', '')}")
    print()

    _banner("System binaries")
    ffmpeg_info = check_system_binary("ffmpeg")
    ffprobe_info = check_system_binary("ffprobe")
    print()

    _banner("Python packages")
    python_checks = [
        check_python_module("fastapi", "FastAPI"),
        check_python_module("uvicorn", "Uvicorn"),
        check_python_module("motor", "Motor (MongoDB)"),
        check_python_module("librosa", "librosa"),
        check_python_module("soundfile", "soundfile"),
        check_python_module("numpy", "NumPy"),
        check_python_module("scipy", "SciPy"),
        check_python_module("numba", "Numba"),
        check_python_module("ffmpeg", "ffmpeg-python"),
    ]
    print()

    all_python_ok = all(c["ok"] for c in python_checks)
    binaries_ok = ffmpeg_info["ok"] and ffprobe_info["ok"]
    overall_ok = all_python_ok and binaries_ok

    status = {
        "checked_at": started,
        "overall_ok": overall_ok,
        "python_ok": all_python_ok,
        "binaries_ok": binaries_ok,
        "ffmpeg": ffmpeg_info,
        "ffprobe": ffprobe_info,
        "python": python_checks,
        "path": os.environ.get("PATH", ""),
    }

    try:
        STATUS_FILE.write_text(json.dumps(status, indent=2))
        print(f"Wrote status file: {STATUS_FILE}")
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: could not persist status file: {exc}")

    _banner("Summary")
    print(f"  Overall:   {'OK' if overall_ok else 'DEGRADED'}")
    print(f"  Python:    {'OK' if all_python_ok else 'FAIL'}")
    print(f"  Binaries:  {'OK' if binaries_ok else 'FAIL'}")
    if not binaries_ok:
        print()
        print("  >>> FFmpeg/FFprobe missing. API will start but rendering endpoints")
        print("  >>> will return HTTP 503 until system binaries are installed.")
        print("  >>> Fix: ensure the Docker image installs `ffmpeg` (see backend/Dockerfile).")

    # We intentionally always exit 0 so a missing binary does not crash the
    # container. The API will report degraded health via /api/health/ffmpeg.
    return 0


if __name__ == "__main__":
    sys.exit(main())
