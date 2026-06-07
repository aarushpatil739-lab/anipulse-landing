"""
Pacing Engine

Dynamic pacing engine that determines cut timing, transitions, and effects based on:
- BPM (higher BPM = faster cuts)
- Energy levels (high/medium/low)
- Drops and intensity spikes
- Beat alignment
- Anime-style AMV aesthetics
"""

import logging
from typing import List, Dict, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class EnergyLevel(str, Enum):
    """Energy level categories"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TransitionType(str, Enum):
    """Available transition types"""
    NONE = "none"
    FADE = "fade"
    FLASH = "flash"
    ZOOM = "zoom"


class EffectType(str, Enum):
    """Available effect types"""
    NONE = "none"
    ZOOM = "zoom"
    SHAKE = "shake"
    SPEED_RAMP = "speed_ramp"


class PacingEngine:
    """
    Dynamic pacing engine for anime-style AMV generation
    
    Rules:
    - High BPM (>140) → faster cuts (0.5-1.0s per beat)
    - Medium BPM (100-140) → moderate cuts (1.0-2.0s per 1-2 beats)
    - Low BPM (<100) → slower cuts (2.0-4.0s per 2-4 beats)
    - High energy → fast aggressive cuts + strong effects
    - Low energy → longer cinematic shots + smooth transitions
    - Drops → flash/zoom transitions + shake/zoom effects
    - Calm sections → fade transitions + minimal effects
    """
    
    def __init__(
        self,
        bpm: float,
        audio_duration: float,
        clip_count: int = 1,
        total_clip_duration: float = 0.0,
        preset: str = "cinematic",
    ):
        """
        Initialize pacing engine

        Args:
            bpm: Beats per minute from audio analysis
            audio_duration: Total audio duration in seconds
            clip_count: Number of source clips available (drives adaptive
                pacing -- few clips => longer cuts so we don't recycle
                the same frames every half second).
            total_clip_duration: Sum of all source clip durations.
            preset: One of 'cinematic', 'emotional', 'velocity', 'phonk',
                'aggressive'. Drives the cut-density / effect-density mix.
        """
        self.bpm = bpm
        self.audio_duration = audio_duration
        self.clip_count = max(1, clip_count)
        self.total_clip_duration = max(0.0, total_clip_duration)
        self.preset = (preset or "cinematic").lower()
        self.beat_duration = 60.0 / bpm if bpm > 0 else 0.5

        # ---- BPM-derived base cut ---------------------------------------
        # The previous version cut every beat at high BPM which yielded
        # 0.4s clips on top-40 tempos.  We now use *multiple* beats per
        # cut to give the eye time to read each frame.
        if bpm >= 140:
            self.bpm_category = "high"
            beats_per_cut = 2.0  # was 1.0
        elif bpm >= 100:
            self.bpm_category = "medium"
            beats_per_cut = 3.0  # was 1.5
        else:
            self.bpm_category = "low"
            beats_per_cut = 4.0  # was 3.0
        self.base_cut_duration = self.beat_duration * beats_per_cut

        # ---- Preset weighting -------------------------------------------
        # Multiplier applied to base_cut_duration. Lower => faster cuts.
        preset_speed = {
            "cinematic": 1.30,
            "emotional": 1.55,
            "velocity":  0.80,
            "phonk":     0.85,
            "aggressive": 0.70,
        }.get(self.preset, 1.0)
        self.base_cut_duration *= preset_speed
        self.preset_speed = preset_speed

        # ---- Adaptive minimum cut ----------------------------------------
        # If we only have a handful of clips, force longer cuts so the
        # eye doesn't see the same frames every second.
        # Heuristic: each clip should appear at most ~ceil(audio/N) times
        # in the timeline -> min_cut = audio / (clips * 4).
        adaptive_min = max(1.0, self.audio_duration / max(1, self.clip_count * 4))
        self.min_cut_duration = min(2.5, adaptive_min)

        # Effect / transition density caps (cinematic baseline; preset can
        # override).  Counted per minute of output.
        preset_density = {
            "cinematic":  {"tr": 14, "fx": 6},
            "emotional":  {"tr": 10, "fx": 4},
            "velocity":   {"tr": 28, "fx": 14},
            "phonk":      {"tr": 24, "fx": 12},
            "aggressive": {"tr": 32, "fx": 18},
        }.get(self.preset, {"tr": 18, "fx": 8})
        self.max_transitions_per_minute = preset_density["tr"]
        self.max_effects_per_minute = preset_density["fx"]

        # Rolling counters: list of timestamps (seconds in output)
        self._transition_times: List[float] = []
        self._effect_times: List[float] = []
        self._heavy_effect_times: List[float] = []  # zoom / shake

        logger.info(
            "PacingEngine | BPM=%.1f (%s) preset=%s base_cut=%.2fs "
            "min_cut=%.2fs clips=%d audio=%.1fs caps={tr=%d/min, fx=%d/min}",
            bpm,
            self.bpm_category,
            self.preset,
            self.base_cut_duration,
            self.min_cut_duration,
            self.clip_count,
            self.audio_duration,
            self.max_transitions_per_minute,
            self.max_effects_per_minute,
        )
    
    def calculate_cut_duration(
        self,
        energy_level: EnergyLevel,
        is_drop: bool = False,
        position_in_audio: float = 0.0
    ) -> float:
        """
        Calculate cut duration based on energy level and context
        
        Args:
            energy_level: Current energy level
            is_drop: Whether this is at a drop/intensity spike
            position_in_audio: Position in audio (for intro/outro adjustment)
            
        Returns:
            Cut duration in seconds
        """
        duration = self.base_cut_duration
        
        # Energy-based adjustment
        if energy_level == EnergyLevel.HIGH:
            # Fast aggressive cuts
            if is_drop:
                duration *= 0.6  # Very fast at drops (anime AMV style)
            else:
                duration *= 0.8  # Fast during high energy
        
        elif energy_level == EnergyLevel.MEDIUM:
            # Moderate pacing
            duration *= 1.0  # Base duration
        
        elif energy_level == EnergyLevel.LOW:
            # Longer cinematic shots
            duration *= 1.8  # Slower, more contemplative
        
        # Intro/outro adjustment (slightly longer cuts for buildup/resolution)
        intro_duration = min(10.0, self.audio_duration * 0.1)
        outro_duration = min(10.0, self.audio_duration * 0.1)
        
        if position_in_audio < intro_duration:
            # Intro: slightly longer cuts for buildup
            intro_factor = 1.0 + (0.3 * (1.0 - position_in_audio / intro_duration))
            duration *= intro_factor
        
        elif position_in_audio > (self.audio_duration - outro_duration):
            # Outro: slightly longer cuts for resolution
            outro_progress = (position_in_audio - (self.audio_duration - outro_duration)) / outro_duration
            outro_factor = 1.0 + (0.2 * outro_progress)
            duration *= outro_factor
        
        # Clamp duration to reasonable bounds.
        # Lower bound is now adaptive (driven by clip count) so AMVs with
        # 3 clips don't cycle the same frames every 0.5s.
        min_duration = self.min_cut_duration
        max_duration = 6.0  # was 5.0 -- allow more cinematic holds
        
        return max(min_duration, min(duration, max_duration))
    
    # ------------------------------------------------------------------
    # Density helpers
    # ------------------------------------------------------------------

    def _within_cap(self, times: List[float], position: float, cap_per_minute: int) -> bool:
        """True if adding a marker at `position` keeps us under the cap.

        We measure density over the trailing 60-second window in the
        output timeline.  This stops short bursts of cuts from looking
        like chaos: even if the music has 8 drops in 4 seconds, we will
        still enforce e.g. <=14 transitions/min cinematic-wide.
        """
        if cap_per_minute <= 0:
            return False
        window_start = position - 60.0
        recent = [t for t in times if t >= window_start]
        # Scale cap proportionally for very short tracks.
        scale = min(1.0, max(0.1, position / 60.0)) if position > 0 else 0.1
        scaled_cap = max(2, int(round(cap_per_minute * scale + 0.5)))
        return len(recent) < scaled_cap

    def record_transition(self, position: float) -> None:
        self._transition_times.append(position)

    def record_effect(self, position: float, heavy: bool = False) -> None:
        self._effect_times.append(position)
        if heavy:
            self._heavy_effect_times.append(position)

    def select_transition(
        self,
        energy_level: EnergyLevel,
        is_drop: bool = False,
        prev_transition: Optional[TransitionType] = None,
        position: float = 0.0,
    ) -> TransitionType:
        """
        Select an appropriate transition, honouring per-minute density caps.

        On low-energy passages and when the cap is reached we deliberately
        return TransitionType.NONE -- the renderer will use a clean hard
        cut, which is the actual AMV / anime aesthetic.
        """
        # Drops still get strong transitions -- but only if we are below
        # the heavy-transition cap.  When we have to skip a drop, we use
        # FADE instead of NONE so the moment still reads.
        if is_drop:
            heavy_ok = self._within_cap(
                self._heavy_effect_times, position, self.max_effects_per_minute
            )
            if heavy_ok:
                self.record_effect(position, heavy=True)
                if prev_transition == TransitionType.FLASH:
                    return TransitionType.ZOOM
                return TransitionType.FLASH
            return TransitionType.FADE

        # Non-drop transition density check
        if not self._within_cap(self._transition_times, position, self.max_transitions_per_minute):
            return TransitionType.NONE

        if energy_level == EnergyLevel.HIGH:
            if prev_transition == TransitionType.FADE:
                return TransitionType.FLASH
            return TransitionType.FADE
        if energy_level == EnergyLevel.MEDIUM:
            return TransitionType.FADE
        # LOW: gentler
        return TransitionType.FADE

    def select_effect(
        self,
        energy_level: EnergyLevel,
        is_drop: bool = False,
        cut_duration: float = 1.0,
        position: float = 0.0,
    ) -> Optional[EffectType]:
        """
        Pick an effect, throttled by the per-minute cap and a
        per-clip-type cooldown.  Heavy effects (zoom/shake) need at
        least 4s between applications so the timeline doesn't feel
        spammy.
        """
        # Hard cap first
        if not self._within_cap(self._effect_times, position, self.max_effects_per_minute):
            return EffectType.NONE

        # Heavy-effect cooldown (4s)
        heavy_cooldown_ok = (
            not self._heavy_effect_times
            or (position - self._heavy_effect_times[-1]) >= 4.0
        )

        import random as _rng

        if is_drop and heavy_cooldown_ok:
            choice = _rng.choice([EffectType.SHAKE, EffectType.ZOOM])
            self.record_effect(position, heavy=True)
            return choice

        if energy_level == EnergyLevel.HIGH and _rng.random() < 0.20:
            # Bias toward speed_ramp (cheap, no zoom risk on tiny clips)
            if cut_duration < 1.0 and heavy_cooldown_ok:
                self.record_effect(position, heavy=True)
                return EffectType.ZOOM
            self.record_effect(position, heavy=False)
            return EffectType.SPEED_RAMP

        if energy_level == EnergyLevel.MEDIUM and _rng.random() < 0.05:
            if heavy_cooldown_ok:
                self.record_effect(position, heavy=True)
                return EffectType.ZOOM

        return EffectType.NONE

    # ------------------------------------------------------------------
    # Legacy single-arg overload (kept for any external callers)
    # ------------------------------------------------------------------

    def get_energy_level(
        self,
        position: float,
        energy_sections: List[Dict]
    ) -> EnergyLevel:
        """
        Get energy level at a specific position
        
        Args:
            position: Position in audio (seconds)
            energy_sections: List of energy sections from audio analysis
            
        Returns:
            Energy level
        """
        for section in energy_sections:
            if section['start'] <= position < section['end']:
                section_type = section.get('type', 'medium')
                avg_energy = section.get('avg_energy', 0.5)
                
                # Map to energy level
                if section_type == 'high' or avg_energy > 0.6:
                    return EnergyLevel.HIGH
                elif section_type == 'low' or avg_energy < 0.4:
                    return EnergyLevel.LOW
                else:
                    return EnergyLevel.MEDIUM
        
        # Default to medium if no section found
        return EnergyLevel.MEDIUM
    
    def is_near_drop(
        self,
        position: float,
        drops: List[float],
        tolerance: float = 0.5
    ) -> bool:
        """
        Check if position is near a drop
        
        Args:
            position: Position in audio (seconds)
            drops: List of drop timestamps
            tolerance: How close to consider "near" (seconds)
            
        Returns:
            True if near a drop
        """
        for drop in drops:
            if abs(position - drop) <= tolerance:
                return True
        return False
    
    def align_to_beat(
        self,
        position: float,
        beats: List[float],
        tolerance: float = 0.2
    ) -> float:
        """
        Align position to nearest beat
        
        Args:
            position: Target position (seconds)
            beats: List of beat timestamps
            tolerance: Maximum adjustment (seconds)
            
        Returns:
            Beat-aligned position
        """
        if not beats:
            return position
        
        # Find nearest beat
        nearest_beat = min(beats, key=lambda b: abs(b - position))
        
        # Only align if within tolerance
        if abs(nearest_beat - position) <= tolerance:
            return nearest_beat
        
        return position
    
    def calculate_transition_duration(
        self,
        transition_type: TransitionType,
        energy_level: EnergyLevel
    ) -> float:
        """
        Calculate transition duration
        
        Args:
            transition_type: Type of transition
            energy_level: Current energy level
            
        Returns:
            Transition duration in seconds
        """
        if transition_type == TransitionType.NONE:
            return 0.0
        
        # Base transition duration
        base_duration = 0.5
        
        # Adjust by energy
        if energy_level == EnergyLevel.HIGH:
            return base_duration * 0.6  # Fast transitions
        elif energy_level == EnergyLevel.LOW:
            return base_duration * 1.2  # Slower transitions
        else:
            return base_duration
    
    def get_pacing_stats(self) -> Dict:
        """Get pacing engine statistics"""
        return {
            "bpm": self.bpm,
            "bpm_category": self.bpm_category,
            "beat_duration": self.beat_duration,
            "base_cut_duration": self.base_cut_duration,
            "audio_duration": self.audio_duration
        }
