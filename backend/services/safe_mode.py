"""
Safe Mode + Memory Guard
========================

Lightweight runtime utilities that detect when the render container is
under memory pressure or has been handed an impossible job (too little
footage for too long a song) and switch the pipeline into a degraded but
reliable mode.

Safe Mode effects (applied wherever the code consults these helpers):
  * cap output resolution to 720p (already the default)
  * use 'fast' quality preset (ultrafast x264, smaller mem footprint)
  * skip per-segment effects (zoom / shake / speed_ramp)
  * downgrade complex transitions to plain cuts
  * tighter segment cap

We deliberately avoid heavy ML / psutil-dependent gymnastics; this whole
module is ~80 lines of pure-python with one optional psutil import.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import psutil  # type: ignore
    _HAS_PSUTIL = True
except Exception:  # noqa: BLE001
    psutil = None  # type: ignore
    _HAS_PSUTIL = False


# Tunables (overridable via env)
SAFE_MODE_FORCE = os.environ.get("ANIPULSE_SAFE_MODE", "auto").lower()  # 'on'|'off'|'auto'
MEM_WARN_PERCENT = float(os.environ.get("ANIPULSE_MEM_WARN_PCT", "78"))
MEM_DANGER_PERCENT = float(os.environ.get("ANIPULSE_MEM_DANGER_PCT", "88"))


@dataclass
class SafeModeDecision:
    """Result of evaluating whether a job should run in safe mode."""

    enabled: bool
    reason: Optional[str]


def memory_pressure_percent() -> Optional[float]:
    """Return system memory pressure as a 0-100 percent, or None.

    Uses psutil's virtual_memory if available; falls back to None.
    """
    if not _HAS_PSUTIL:
        return None
    try:
        vm = psutil.virtual_memory()
        return float(vm.percent)
    except Exception:  # noqa: BLE001
        return None


def evaluate(
    clip_count: int,
    total_clip_duration: float,
    audio_duration: float,
    preset: str,
) -> SafeModeDecision:
    """
    Decide if this render should run in safe mode.

    Triggers (any of):
      * env override (`ANIPULSE_SAFE_MODE=on`)
      * footage pool is < 12s OR < 25% of audio duration
      * audio duration > 180s on the small Railway plan
      * memory pressure already >= MEM_WARN_PERCENT before we even start
    """
    if SAFE_MODE_FORCE == "on":
        return SafeModeDecision(True, "ANIPULSE_SAFE_MODE=on")
    if SAFE_MODE_FORCE == "off":
        return SafeModeDecision(False, None)

    reasons = []
    if clip_count <= 1 and total_clip_duration < 25.0:
        reasons.append("single short clip")
    if total_clip_duration > 0 and audio_duration > 0 and (
        total_clip_duration / audio_duration < 0.25
    ):
        reasons.append("clip pool < 25% of audio")
    if audio_duration > 180.0:
        reasons.append("audio > 180s")

    pct = memory_pressure_percent()
    if pct is not None and pct >= MEM_WARN_PERCENT:
        reasons.append(f"baseline memory at {pct:.0f}%")

    if reasons:
        return SafeModeDecision(True, "; ".join(reasons))
    return SafeModeDecision(False, None)


def mid_render_memory_danger() -> bool:
    """Check at hot-spots (e.g. before each export) whether we're in the
    red zone and should aggressively simplify the rest of the pipeline.
    """
    pct = memory_pressure_percent()
    if pct is None:
        return False
    if pct >= MEM_DANGER_PERCENT:
        logger.warning("Memory pressure DANGER: %.0f%% >= %.0f%%", pct, MEM_DANGER_PERCENT)
        return True
    return False


__all__ = [
    "SafeModeDecision",
    "evaluate",
    "memory_pressure_percent",
    "mid_render_memory_danger",
]
