"""
AI Timeline Generator

Generates structured edit timelines for AMV creation by:
- Mapping beats to cuts
- Mapping drops to transitions/effects
- Applying energy-based pacing
- Selecting clips intelligently
- Producing validated, render-ready timeline JSON
"""

import logging
from typing import List, Dict, Optional
from pathlib import Path

from services.pacing_engine import PacingEngine, EnergyLevel, TransitionType, EffectType
from services.clip_selector import ClipSelector, ClipMetadata
from models.generation_job import TimelineSegment, GeneratedTimeline

logger = logging.getLogger(__name__)


class TimelineGenerator:
    """
    AI Timeline Generator
    
    Produces structured edit timelines from audio analysis and video clips.
    """
    
    def __init__(
        self,
        audio_analysis: Dict,
        clips_metadata: List[Dict],
        max_duration: float = 180.0,  # 3 minute cap
        style: str = "amv_default",
        seed: Optional[int] = None
    ):
        """
        Initialize timeline generator
        
        Args:
            audio_analysis: Audio analysis results from AudioAnalyzer
            clips_metadata: List of clip metadata dicts
            max_duration: Maximum output duration (seconds)
            style: Generation style
            seed: Random seed for testing
        """
        self.audio_analysis = audio_analysis
        self.max_duration = min(max_duration, audio_analysis['duration'])
        self.style = style
        
        # Initialize engines
        self.pacing = PacingEngine(
            bpm=audio_analysis['bpm'],
            audio_duration=audio_analysis['duration']
        )
        
        # Convert clip metadata to ClipMetadata objects
        clip_objects = []
        for i, clip_meta in enumerate(clips_metadata):
            clip_obj = ClipMetadata(
                index=i,
                path=clip_meta['path'],
                duration=clip_meta['duration'],
                width=clip_meta.get('width', 1920),
                height=clip_meta.get('height', 1080),
                fps=clip_meta.get('fps', 30.0),
                bitrate=clip_meta.get('bitrate', 500000),
                has_audio=clip_meta.get('has_audio', True)
            )
            clip_objects.append(clip_obj)
        
        self.clip_selector = ClipSelector(clip_objects, seed=seed)
        
        # Timeline data
        self.segments: List[TimelineSegment] = []
        self.current_timeline_pos = 0.0
        
        logger.info(
            f"TimelineGenerator initialized: {len(clip_objects)} clips, "
            f"BPM={audio_analysis['bpm']:.1f}, duration={audio_analysis['duration']:.2f}s, "
            f"max_output={self.max_duration:.2f}s"
        )
    
    def generate(self) -> GeneratedTimeline:
        """
        Generate complete edit timeline
        
        Returns:
            GeneratedTimeline object
        """
        logger.info("Starting timeline generation...")
        
        # Minimum segment duration to prevent FFmpeg issues
        MIN_SEGMENT_DURATION = 0.5  # 500ms minimum for stable rendering
        
        beats = self.audio_analysis['beats']
        drops = self.audio_analysis['drops']
        energy_sections = self.audio_analysis['sections']
        
        if not beats:
            raise ValueError("No beats detected in audio analysis")
        
        # Generate segments beat by beat
        prev_transition = TransitionType.NONE
        transition_count = 0
        effect_count = 0
        
        beat_idx = 0
        while self.current_timeline_pos < self.max_duration and beat_idx < len(beats):
            beat_time = beats[beat_idx]
            
            # Skip if beat is beyond max duration
            if beat_time >= self.max_duration:
                break
            
            # Get context
            energy_level = self.pacing.get_energy_level(beat_time, energy_sections)
            is_drop = self.pacing.is_near_drop(beat_time, drops, tolerance=0.5)
            
            # Calculate cut duration
            cut_duration = self.pacing.calculate_cut_duration(
                energy_level,
                is_drop=is_drop,
                position_in_audio=beat_time
            )
            
            # STABILITY: Enforce minimum segment duration
            if cut_duration < MIN_SEGMENT_DURATION:
                logger.debug(f"Cut duration {cut_duration:.2f}s too short, enforcing minimum {MIN_SEGMENT_DURATION}s")
                cut_duration = MIN_SEGMENT_DURATION
            
            # Ensure we don't exceed max duration
            if self.current_timeline_pos + cut_duration > self.max_duration:
                cut_duration = self.max_duration - self.current_timeline_pos
                # Skip if remaining duration is too short for stable rendering
                if cut_duration < MIN_SEGMENT_DURATION:
                    logger.info(f"Remaining duration {cut_duration:.2f}s too short, stopping timeline generation")
                    break
            
            # Select clip
            clip_selection = self.clip_selector.select_clip(
                current_timeline_pos=self.current_timeline_pos,
                energy_level=energy_level.value,
                required_duration=cut_duration,
                cooldown=5.0,
                prefer_variety=True
            )
            
            if not clip_selection:
                logger.warning(f"No clip available at timeline_pos={self.current_timeline_pos:.2f}s, skipping")
                beat_idx += 1
                continue
            
            clip_index, source_start, source_end = clip_selection
            
            # STABILITY: Validate segment duration from clip selection
            actual_duration = source_end - source_start
            if actual_duration < MIN_SEGMENT_DURATION:
                logger.warning(f"Selected clip segment too short ({actual_duration:.2f}s), adjusting...")
                # Try to extend the segment if possible
                clip = self.clip_selector.clips[clip_index]
                if source_end + (MIN_SEGMENT_DURATION - actual_duration) <= clip.duration:
                    source_end = source_start + MIN_SEGMENT_DURATION
                    actual_duration = MIN_SEGMENT_DURATION
                else:
                    # Can't extend, skip this segment
                    logger.warning(f"Cannot extend segment, skipping")
                    beat_idx += 1
                    continue
            
            # Select transition and effect
            transition = self.pacing.select_transition(
                energy_level,
                is_drop=is_drop,
                prev_transition=prev_transition
            )
            
            effect = self.pacing.select_effect(
                energy_level,
                is_drop=is_drop,
                cut_duration=cut_duration
            )
            
            # Create segment
            segment = TimelineSegment(
                clip_path=self.clip_selector.clips[clip_index].path,
                clip_index=clip_index,
                start_time=source_start,
                end_time=source_end,
                timeline_start=self.current_timeline_pos,
                timeline_end=self.current_timeline_pos + actual_duration,
                transition=transition.value if transition != TransitionType.NONE else None,
                effect=effect.value if effect != EffectType.NONE else None,
                energy_level=energy_level.value,
                beat_aligned=True
            )
            
            self.segments.append(segment)
            
            # Mark clip as used
            self.clip_selector.mark_clip_used(
                clip_index,
                self.current_timeline_pos,
                source_start,
                source_end
            )
            
            # Update counters
            if transition != TransitionType.NONE:
                transition_count += 1
                prev_transition = transition
            
            if effect != EffectType.NONE:
                effect_count += 1
            
            # Advance timeline
            self.current_timeline_pos += actual_duration
            
            # Advance to next beat (or skip beats if cut was long)
            while beat_idx < len(beats) and beats[beat_idx] < self.current_timeline_pos:
                beat_idx += 1
        
        # Validate and create timeline
        timeline = self._validate_and_create_timeline(transition_count, effect_count)
        
        logger.info(
            f"Timeline generation complete: {len(self.segments)} segments, "
            f"{timeline.total_duration:.2f}s, {transition_count} transitions, {effect_count} effects"
        )
        
        return timeline
    
    def _validate_and_create_timeline(
        self,
        transition_count: int,
        effect_count: int
    ) -> GeneratedTimeline:
        """Validate timeline and create GeneratedTimeline object"""
        
        if not self.segments:
            raise ValueError("Timeline generation produced no segments")
        
        # Validation checks
        for i, segment in enumerate(self.segments):
            # Check valid times
            if segment.start_time < 0 or segment.end_time <= segment.start_time:
                raise ValueError(f"Segment {i}: Invalid source times {segment.start_time:.2f} to {segment.end_time:.2f}")
            
            if segment.timeline_start < 0 or segment.timeline_end <= segment.timeline_start:
                raise ValueError(f"Segment {i}: Invalid timeline times {segment.timeline_start:.2f} to {segment.timeline_end:.2f}")
            
            # Check clip exists
            if segment.clip_index >= len(self.clip_selector.clips):
                raise ValueError(f"Segment {i}: Invalid clip_index {segment.clip_index}")
            
            # Check clip duration
            clip = self.clip_selector.clips[segment.clip_index]
            if segment.end_time > clip.duration:
                raise ValueError(
                    f"Segment {i}: source end_time {segment.end_time:.2f}s exceeds clip duration {clip.duration:.2f}s"
                )
            
            # Check for overlaps (segments should be sequential)
            if i > 0:
                prev_segment = self.segments[i - 1]
                if segment.timeline_start < prev_segment.timeline_end:
                    raise ValueError(
                        f"Segment {i}: Overlaps with previous segment "
                        f"({segment.timeline_start:.2f} < {prev_segment.timeline_end:.2f})"
                    )
        
        # Calculate statistics
        total_duration = self.segments[-1].timeline_end if self.segments else 0.0
        cut_durations = [seg.timeline_end - seg.timeline_start for seg in self.segments]
        avg_cut_duration = sum(cut_durations) / len(cut_durations) if cut_durations else 0.0
        
        # Create timeline object
        timeline = GeneratedTimeline(
            segments=self.segments,
            total_duration=total_duration,
            transition_count=transition_count,
            effect_count=effect_count,
            avg_cut_duration=avg_cut_duration,
            style=self.style
        )
        
        logger.info(
            f"Timeline validated: {len(self.segments)} segments, "
            f"avg_cut={avg_cut_duration:.2f}s, duration={total_duration:.2f}s"
        )
        
        return timeline
    
    def get_generation_log(self) -> str:
        """Get detailed generation log for debugging"""
        log_lines = []
        log_lines.append("=== Timeline Generation Log ===\n")
        log_lines.append(f"Audio BPM: {self.audio_analysis['bpm']:.1f}")
        log_lines.append(f"Audio Duration: {self.audio_analysis['duration']:.2f}s")
        log_lines.append(f"Max Output Duration: {self.max_duration:.2f}s")
        log_lines.append(f"Total Beats: {len(self.audio_analysis['beats'])}")
        log_lines.append(f"Total Drops: {len(self.audio_analysis['drops'])}")
        log_lines.append(f"Style: {self.style}\n")
        
        log_lines.append("=== Pacing Stats ===")
        pacing_stats = self.pacing.get_pacing_stats()
        for key, value in pacing_stats.items():
            log_lines.append(f"{key}: {value}")
        log_lines.append("")
        
        log_lines.append("=== Clip Usage Stats ===")
        usage_stats = self.clip_selector.get_usage_stats()
        for clip_idx, stats in usage_stats.items():
            log_lines.append(
                f"Clip {clip_idx}: {stats['total_uses']} uses, "
                f"{stats['ranges_used']} ranges, "
                f"last_used={stats['last_used_time']:.2f}s"
            )
        log_lines.append("")
        
        log_lines.append("=== Generated Segments ===")
        for i, segment in enumerate(self.segments):
            log_lines.append(
                f"[{i:03d}] timeline={segment.timeline_start:.2f}-{segment.timeline_end:.2f}s, "
                f"clip={segment.clip_index}, source={segment.start_time:.2f}-{segment.end_time:.2f}s, "
                f"energy={segment.energy_level}, trans={segment.transition}, effect={segment.effect}"
            )
        
        return "\n".join(log_lines)
