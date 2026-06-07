"""
Scene Analyzer
==============

Lightweight per-clip motion / intensity / scene-cut detection using PyAV
(a thin Python binding to the same FFmpeg libraries we already ship in
the container -- no extra system packages needed because PyAV 12+ ships
manylinux wheels with bundled FFmpeg).

Why PyAV over OpenCV?  PyAV is ~10x smaller, has no GL/X11 system
dependencies, and re-uses our existing FFmpeg knowledge.

What we compute per clip
------------------------
* motion_score    : average per-frame luma diff, 0-255 scale
* intensity_score : luma standard deviation across the timeline, 0-127
* scene_cuts      : list of timestamps (s) where consecutive frames differ
                    sharply (anime hard cut / large camera move)
* score_1_to_10   : single "intensity rating" combining motion + variance
                    used by ClipSelector for smarter weighting
* action_segments : timestamp ranges where motion exceeds the clip mean
                    (use these as candidate windows for high-energy beats)
* calm_segments   : the inverse -- ideal for low-energy intro/outro shots

Memory profile
--------------
We decode at the source FPS but immediately downscale every frame to
160x90 grayscale uint8 (~14 KB) before any numpy work.  Peak resident
memory stays well under 50 MB even on long clips, which keeps us safely
within Railway's 512 MB trial container.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import av  # type: ignore
    _PYAV_AVAILABLE = True
    _PYAV_IMPORT_ERROR: Optional[str] = None
except Exception as exc:  # noqa: BLE001
    av = None  # type: ignore
    _PYAV_AVAILABLE = False
    _PYAV_IMPORT_ERROR = str(exc)

logger = logging.getLogger(__name__)


# Downscale target for analysis.  160x90 keeps detail for motion while
# being ~30x cheaper to diff than 1280x720.
_ANALYSIS_W = 160
_ANALYSIS_H = 90

# A normalised per-frame diff above this is considered a hard cut.
# (luma mean diff on a 0-255 scale)
_SCENE_CUT_DIFF = 28.0

# When deciding whether a section is "action" vs "calm" we use:
#   action  := motion > clip_mean + alpha * clip_std
#   calm    := motion < clip_mean - alpha * clip_std
_ACTION_ALPHA = 0.6


@dataclass
class SceneAnalysisResult:
    """Per-clip scene analysis summary."""

    clip_path: str
    duration: float
    frames_analyzed: int
    motion_score: float          # 0-255
    intensity_score: float       # 0-127 (luma std)
    score_1_to_10: float         # convenience composite, useful for UI
    scene_cuts: List[float]
    action_segments: List[Tuple[float, float]] = field(default_factory=list)
    calm_segments: List[Tuple[float, float]] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        d = asdict(self)
        return d


class SceneAnalyzer:
    """Compute motion + intensity + scene-cut metadata for a video clip."""

    def __init__(self, analysis_fps: int = 6):
        """
        Args:
            analysis_fps: how many frames per second to sample from the
                source. 6 fps gives enough motion granularity for AMV
                pacing while keeping decode time minimal.
        """
        self.analysis_fps = max(1, analysis_fps)
        if not _PYAV_AVAILABLE:
            logger.warning(
                "PyAV is not importable (%s) -- SceneAnalyzer will return "
                "degraded results based on probe metadata only.",
                _PYAV_IMPORT_ERROR,
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, video_path: str) -> SceneAnalysisResult:
        """
        Run scene analysis on `video_path`.

        Always returns a SceneAnalysisResult (never raises) so callers
        can degrade gracefully -- if PyAV is missing or the file is
        unreadable, we return a "neutral" result and log the cause.
        """
        path = Path(video_path)
        if not path.exists():
            return SceneAnalysisResult(
                clip_path=str(path),
                duration=0.0,
                frames_analyzed=0,
                motion_score=0.0,
                intensity_score=0.0,
                score_1_to_10=5.0,
                scene_cuts=[],
                error=f"file not found: {path}",
            )

        if not _PYAV_AVAILABLE:
            return SceneAnalysisResult(
                clip_path=str(path),
                duration=0.0,
                frames_analyzed=0,
                motion_score=0.0,
                intensity_score=0.0,
                score_1_to_10=5.0,
                scene_cuts=[],
                error=f"PyAV unavailable: {_PYAV_IMPORT_ERROR}",
            )

        try:
            return self._analyze_with_pyav(str(path))
        except Exception as exc:  # noqa: BLE001
            logger.exception("SceneAnalyzer failed for %s", path)
            return SceneAnalysisResult(
                clip_path=str(path),
                duration=0.0,
                frames_analyzed=0,
                motion_score=0.0,
                intensity_score=0.0,
                score_1_to_10=5.0,
                scene_cuts=[],
                error=f"analyzer error: {exc}",
            )

    def analyze_many(self, video_paths: List[str]) -> List[SceneAnalysisResult]:
        return [self.analyze(p) for p in video_paths]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _analyze_with_pyav(self, video_path: str) -> SceneAnalysisResult:
        assert av is not None  # for type checkers
        container = av.open(video_path)
        try:
            if not container.streams.video:
                raise ValueError("no video stream")
            stream = container.streams.video[0]
            stream.thread_type = "AUTO"

            avg_rate = float(stream.average_rate or 30.0)
            sample_every = max(1, int(round(avg_rate / self.analysis_fps)))
            duration = float(container.duration or 0) / av.time_base if container.duration else 0.0
            if duration <= 0 and stream.duration:
                duration = float(stream.duration * stream.time_base)

            prev_arr: Optional[np.ndarray] = None
            diffs: List[float] = []
            luma_means: List[float] = []
            frame_times: List[float] = []
            scene_cuts: List[float] = []

            frame_index = -1
            for frame in container.decode(stream):
                frame_index += 1
                if frame_index % sample_every != 0:
                    continue

                # to_ndarray is slow at full res; reformat first.
                try:
                    arr = (
                        frame.reformat(
                            width=_ANALYSIS_W,
                            height=_ANALYSIS_H,
                            format="gray8",
                        )
                        .to_ndarray()
                    )
                except Exception:
                    # Fallback path if reformat fails
                    arr = frame.to_ndarray(format="gray")
                    if arr.shape != (_ANALYSIS_H, _ANALYSIS_W):
                        # simple stride-based downsample
                        sh = max(1, arr.shape[0] // _ANALYSIS_H)
                        sw = max(1, arr.shape[1] // _ANALYSIS_W)
                        arr = arr[::sh, ::sw]

                t = float(frame.time) if frame.time is not None else (frame_index / avg_rate)
                frame_times.append(t)
                luma_means.append(float(arr.mean()))

                if prev_arr is not None and prev_arr.shape == arr.shape:
                    d = float(np.abs(arr.astype(np.int16) - prev_arr.astype(np.int16)).mean())
                    diffs.append(d)
                    if d > _SCENE_CUT_DIFF:
                        scene_cuts.append(t)
                prev_arr = arr
        finally:
            try:
                container.close()
            except Exception:
                pass

        if not diffs:
            return SceneAnalysisResult(
                clip_path=video_path,
                duration=duration,
                frames_analyzed=len(frame_times),
                motion_score=0.0,
                intensity_score=0.0,
                score_1_to_10=5.0,
                scene_cuts=[],
            )

        diffs_np = np.asarray(diffs, dtype=np.float32)
        lumas_np = np.asarray(luma_means, dtype=np.float32)

        motion_score = float(diffs_np.mean())
        intensity_score = float(lumas_np.std())

        # Composite 1-10 score: motion is the dominant axis; clamp to a
        # plausible range so a totally still clip scores ~1 and a frantic
        # battle scene scores ~10.
        # motion 0..40 -> 1..10  (linear, clamped)
        motion_norm = max(0.0, min(1.0, motion_score / 40.0))
        # intensity 0..50 -> bonus up to +1.5
        intensity_bonus = max(0.0, min(1.5, intensity_score / 33.0))
        score_1_to_10 = round(max(1.0, min(10.0, 1.0 + 9.0 * motion_norm + intensity_bonus)), 2)

        # Action vs calm segments (contiguous runs of high / low motion)
        threshold_hi = motion_score + _ACTION_ALPHA * float(diffs_np.std())
        threshold_lo = max(0.0, motion_score - _ACTION_ALPHA * float(diffs_np.std()))
        # diffs[i] corresponds to the transition from frame_times[i] -> frame_times[i+1]
        action_segments = self._runs(frame_times, diffs_np, lambda v: v >= threshold_hi)
        calm_segments = self._runs(frame_times, diffs_np, lambda v: v <= threshold_lo)

        result = SceneAnalysisResult(
            clip_path=video_path,
            duration=duration,
            frames_analyzed=len(frame_times),
            motion_score=motion_score,
            intensity_score=intensity_score,
            score_1_to_10=score_1_to_10,
            scene_cuts=scene_cuts,
            action_segments=action_segments,
            calm_segments=calm_segments,
        )
        logger.info(
            "SceneAnalyzer | %s | dur=%.2fs frames=%d motion=%.2f intensity=%.2f score=%.2f cuts=%d action_runs=%d calm_runs=%d",
            Path(video_path).name,
            duration,
            len(frame_times),
            motion_score,
            intensity_score,
            score_1_to_10,
            len(scene_cuts),
            len(action_segments),
            len(calm_segments),
        )
        return result

    @staticmethod
    def _runs(times: List[float], diffs: np.ndarray, predicate) -> List[Tuple[float, float]]:
        """Find contiguous runs in `diffs` where predicate(value) is true.
        Returns list of (start_time, end_time) using `times` as the index.
        Adjacent runs separated by <0.3s are merged."""
        runs: List[Tuple[float, float]] = []
        run_start: Optional[float] = None
        for i, v in enumerate(diffs):
            t0 = times[i]
            t1 = times[i + 1] if i + 1 < len(times) else times[i]
            if predicate(float(v)):
                if run_start is None:
                    run_start = t0
            else:
                if run_start is not None:
                    runs.append((float(run_start), float(t1)))
                    run_start = None
        if run_start is not None and times:
            runs.append((float(run_start), float(times[-1])))

        # merge near-adjacent runs
        if not runs:
            return runs
        merged = [runs[0]]
        for s, e in runs[1:]:
            ps, pe = merged[-1]
            if s - pe < 0.3:
                merged[-1] = (ps, e)
            else:
                merged.append((s, e))
        # drop micro-runs
        merged = [(s, e) for (s, e) in merged if (e - s) >= 0.4]
        return merged


def is_available() -> bool:
    """True when the underlying PyAV library imported successfully."""
    return _PYAV_AVAILABLE


def import_error() -> Optional[str]:
    return _PYAV_IMPORT_ERROR


__all__ = [
    "SceneAnalyzer",
    "SceneAnalysisResult",
    "is_available",
    "import_error",
]
