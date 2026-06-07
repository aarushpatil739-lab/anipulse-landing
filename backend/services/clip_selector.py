"""
Clip Selection Engine

Intelligent clip selection system that:
- Avoids repetitive clips with cooldown tracking
- Prevents reusing same time ranges too frequently
- Applies energy-based weighting (high energy = motion-heavy clips)
- Uses weighted random selection for variety
"""

import random
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ClipMetadata:
    """Metadata about a video clip"""
    index: int
    path: str
    duration: float
    width: int
    height: int
    fps: float
    bitrate: int
    has_audio: bool
    
    # Derived attributes for selection heuristics
    motion_score: float = 0.0  # 0-1, higher = more motion-heavy (proxy: bitrate/resolution)
    
    def __post_init__(self):
        """Calculate motion score proxy"""
        # Proxy: higher bitrate relative to resolution suggests more motion/detail
        # Normalize by resolution (1080p baseline = 1920*1080)
        baseline_resolution = 1920 * 1080
        actual_resolution = self.width * self.height
        resolution_factor = actual_resolution / baseline_resolution if baseline_resolution > 0 else 1.0
        
        # Bitrate in kbps, normalized (500kbps as baseline for 1080p)
        bitrate_kbps = self.bitrate / 1000
        baseline_bitrate = 500.0
        bitrate_factor = min(bitrate_kbps / baseline_bitrate, 2.0) if baseline_bitrate > 0 else 1.0
        
        # Combine factors (higher bitrate + resolution = higher motion score)
        self.motion_score = min((bitrate_factor * resolution_factor) / 2.0, 1.0)


@dataclass
class ClipUsage:
    """Track clip usage to prevent repetition"""
    clip_index: int
    last_used_time: float = -999.0  # Timeline position when last used
    total_uses: int = 0
    used_ranges: List[Tuple[float, float]] = field(default_factory=list)  # [(start, end), ...]
    
    def can_use(self, current_timeline_pos: float, cooldown: float = 5.0) -> bool:
        """Check if clip can be used based on cooldown"""
        time_since_last_use = current_timeline_pos - self.last_used_time
        return time_since_last_use >= cooldown
    
    def mark_used(self, timeline_pos: float, source_start: float, source_end: float):
        """Mark clip as used"""
        self.last_used_time = timeline_pos
        self.total_uses += 1
        self.used_ranges.append((source_start, source_end))
    
    def range_overlap(self, start: float, end: float, tolerance: float = 1.0) -> float:
        """Calculate how much a range overlaps with previously used ranges"""
        total_overlap = 0.0
        for used_start, used_end in self.used_ranges:
            # Check for overlap
            overlap_start = max(start, used_start)
            overlap_end = min(end, used_end)
            if overlap_end > overlap_start:
                total_overlap += (overlap_end - overlap_start)
        
        # Normalize by requested range length
        range_len = end - start
        return total_overlap / range_len if range_len > 0 else 0.0


class ClipSelector:
    """
    Intelligent clip selection engine with anti-repetition and energy-based weighting
    """
    
    def __init__(self, clips: List[ClipMetadata], seed: Optional[int] = None):
        """
        Initialize clip selector
        
        Args:
            clips: List of clip metadata
            seed: Random seed for deterministic selection (testing)
        """
        self.clips = clips
        self.usage_tracker = {clip.index: ClipUsage(clip.index) for clip in clips}
        
        # Random seed for deterministic behavior in tests
        if seed is not None:
            random.seed(seed)
            self.rng = random.Random(seed)
        else:
            self.rng = random.Random()
        
        logger.info(f"ClipSelector initialized with {len(clips)} clips")
    
    def select_clip(
        self,
        current_timeline_pos: float,
        energy_level: str,  # "low", "medium", "high"
        required_duration: float,
        cooldown: float = 5.0,
        prefer_variety: bool = True
    ) -> Optional[Tuple[int, float, float]]:
        """
        Select a clip intelligently based on energy level and usage history
        
        Args:
            current_timeline_pos: Current position in output timeline
            energy_level: Energy level ("low", "medium", "high")
            required_duration: How long of a clip segment is needed
            cooldown: Minimum timeline distance before reusing a clip
            prefer_variety: Penalize frequently-used clips
            
        Returns:
            Tuple of (clip_index, source_start, source_end) or None if no suitable clip
        """
        # Filter clips that are available (not in cooldown and have sufficient duration)
        # We try with the requested cooldown first; if that leaves zero
        # candidates, we progressively halve the cooldown until at least
        # one clip qualifies.  Result: no more "No available clips" warnings.
        attempts = [cooldown, cooldown / 2.0, cooldown / 4.0, 0.0]
        available_clips: List[ClipMetadata] = []
        used_cooldown = cooldown
        for c in attempts:
            cand = []
            for clip in self.clips:
                usage = self.usage_tracker[clip.index]
                if not usage.can_use(current_timeline_pos, c):
                    continue
                if clip.duration < required_duration:
                    continue
                cand.append(clip)
            if cand:
                available_clips = cand
                used_cooldown = c
                break

        if not available_clips:
            # Even with cooldown=0 we got nothing -- that means every clip
            # is shorter than required_duration.  Pick the longest clip
            # and force-fit (the caller will trim its end_time to the
            # clip duration on the way out).
            logger.warning(
                "All clips shorter than required_duration=%.2fs at "
                "timeline_pos=%.2fs; picking longest clip as fallback.",
                required_duration,
                current_timeline_pos,
            )
            longest = max(self.clips, key=lambda c: c.duration)
            return (longest.index, 0.0, min(required_duration, longest.duration))

        if used_cooldown < cooldown:
            logger.debug(
                "Relaxed cooldown %.2fs->%.2fs at timeline_pos=%.2fs "
                "(found %d candidates)",
                cooldown,
                used_cooldown,
                current_timeline_pos,
                len(available_clips),
            )
        
        # Calculate weights based on energy level and usage
        weights = []
        for clip in available_clips:
            weight = self._calculate_clip_weight(
                clip,
                energy_level,
                current_timeline_pos,
                required_duration,
                prefer_variety
            )
            weights.append(weight)
        
        # Weighted random selection
        selected_clip = self.rng.choices(available_clips, weights=weights, k=1)[0]
        
        # Select a segment from the clip
        return self._select_segment_from_clip(selected_clip, required_duration)
    
    def _calculate_clip_weight(
        self,
        clip: ClipMetadata,
        energy_level: str,
        current_timeline_pos: float,
        required_duration: float,
        prefer_variety: bool
    ) -> float:
        """Calculate selection weight for a clip"""
        weight = 1.0
        
        # Energy-based weighting
        if energy_level == "high":
            # Prefer motion-heavy clips (higher bitrate/resolution)
            motion_weight = 0.5 + (clip.motion_score * 1.5)  # Range: 0.5 to 2.0
            weight *= motion_weight
        
        elif energy_level == "low":
            # Prefer calmer clips (lower motion score)
            calm_weight = 0.5 + ((1.0 - clip.motion_score) * 1.5)  # Range: 0.5 to 2.0
            weight *= calm_weight
        
        # Medium energy: neutral weighting (no adjustment)
        
        # Usage-based penalty (prefer variety)
        if prefer_variety:
            usage = self.usage_tracker[clip.index]
            # Penalize frequently used clips
            usage_penalty = 1.0 / (1.0 + usage.total_uses * 0.3)
            weight *= usage_penalty
            
            # Penalize recent usage (cooldown proximity)
            time_since_last = current_timeline_pos - usage.last_used_time
            if 0 < time_since_last < 10.0:  # Within 10s of last use
                recency_penalty = time_since_last / 10.0  # 0.0 to 1.0
                weight *= recency_penalty
        
        # Duration bonus: prefer clips that are much longer than required (more flexibility)
        if clip.duration > required_duration * 2:
            duration_bonus = 1.2
            weight *= duration_bonus
        
        return max(weight, 0.01)  # Minimum weight to avoid zero
    
    def _select_segment_from_clip(
        self,
        clip: ClipMetadata,
        required_duration: float
    ) -> Optional[Tuple[int, float, float]]:
        """
        Select a specific time range from a clip, avoiding previously used ranges
        
        Returns:
            (clip_index, source_start, source_end)
        """
        if clip.duration < required_duration:
            return None
        
        usage = self.usage_tracker[clip.index]
        
        # Try to find a segment with minimal overlap with used ranges
        best_segment = None
        best_overlap = float('inf')
        
        # Sample several random positions
        num_samples = min(10, int(clip.duration / required_duration) + 1)
        max_start = clip.duration - required_duration
        
        for _ in range(num_samples):
            start = self.rng.uniform(0, max_start)
            end = start + required_duration
            
            overlap = usage.range_overlap(start, end)
            
            if overlap < best_overlap:
                best_overlap = overlap
                best_segment = (clip.index, start, end)
            
            # If we found a completely fresh segment, use it
            if overlap == 0:
                break
        
        return best_segment
    
    def mark_clip_used(
        self,
        clip_index: int,
        timeline_pos: float,
        source_start: float,
        source_end: float
    ):
        """Mark a clip segment as used"""
        if clip_index in self.usage_tracker:
            self.usage_tracker[clip_index].mark_used(timeline_pos, source_start, source_end)
            logger.debug(
                f"Marked clip {clip_index} used: timeline_pos={timeline_pos:.2f}s, "
                f"source={source_start:.2f}-{source_end:.2f}s, "
                f"total_uses={self.usage_tracker[clip_index].total_uses}"
            )
    
    def get_usage_stats(self) -> Dict:
        """Get usage statistics for all clips"""
        stats = {}
        for clip_index, usage in self.usage_tracker.items():
            stats[clip_index] = {
                "total_uses": usage.total_uses,
                "last_used_time": usage.last_used_time,
                "ranges_used": len(usage.used_ranges)
            }
        return stats
    
    def reset(self):
        """Reset all usage tracking"""
        for usage in self.usage_tracker.values():
            usage.last_used_time = -999.0
            usage.total_uses = 0
            usage.used_ranges.clear()
        logger.info("ClipSelector usage tracking reset")
