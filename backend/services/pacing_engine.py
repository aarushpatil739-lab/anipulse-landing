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
    
    def __init__(self, bpm: float, audio_duration: float):
        """
        Initialize pacing engine
        
        Args:
            bpm: Beats per minute from audio analysis
            audio_duration: Total audio duration in seconds
        """
        self.bpm = bpm
        self.audio_duration = audio_duration
        self.beat_duration = 60.0 / bpm if bpm > 0 else 0.5
        
        # Categorize BPM
        if bpm >= 140:
            self.bpm_category = "high"
            self.base_cut_duration = self.beat_duration  # 1 beat per cut
        elif bpm >= 100:
            self.bpm_category = "medium"
            self.base_cut_duration = self.beat_duration * 1.5  # 1.5 beats per cut
        else:
            self.bpm_category = "low"
            self.base_cut_duration = self.beat_duration * 3  # 3 beats per cut
        
        logger.info(
            f"PacingEngine initialized: BPM={bpm:.1f} ({self.bpm_category}), "
            f"beat_duration={self.beat_duration:.3f}s, base_cut={self.base_cut_duration:.3f}s"
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
        
        # Clamp duration to reasonable bounds
        min_duration = 0.3  # 300ms minimum (very fast anime cuts)
        max_duration = 5.0  # 5s maximum (cinematic shots)
        
        return max(min_duration, min(duration, max_duration))
    
    def select_transition(
        self,
        energy_level: EnergyLevel,
        is_drop: bool = False,
        prev_transition: Optional[TransitionType] = None
    ) -> TransitionType:
        """
        Select appropriate transition type
        
        Args:
            energy_level: Current energy level
            is_drop: Whether this is at a drop
            prev_transition: Previous transition (for variety)
            
        Returns:
            Transition type
        """
        # Drops always get strong transitions
        if is_drop:
            # Alternate between flash and zoom for drops
            if prev_transition == TransitionType.FLASH:
                return TransitionType.ZOOM
            else:
                return TransitionType.FLASH
        
        # Energy-based transitions
        if energy_level == EnergyLevel.HIGH:
            # Fast transitions for high energy
            # Alternate for variety
            if prev_transition == TransitionType.FADE:
                return TransitionType.FLASH
            else:
                return TransitionType.FADE
        
        elif energy_level == EnergyLevel.MEDIUM:
            # Mostly smooth transitions
            return TransitionType.FADE
        
        else:  # LOW energy
            # Gentle transitions or none
            return TransitionType.FADE
    
    def select_effect(
        self,
        energy_level: EnergyLevel,
        is_drop: bool = False,
        cut_duration: float = 1.0
    ) -> Optional[EffectType]:
        """
        Select appropriate effect type
        
        Args:
            energy_level: Current energy level
            is_drop: Whether this is at a drop
            cut_duration: Duration of the cut
            
        Returns:
            Effect type or None
        """
        # Effects are applied selectively to avoid overuse
        
        # Drops get strong effects
        if is_drop:
            # Alternate shake and zoom for drops
            import random
            return random.choice([EffectType.SHAKE, EffectType.ZOOM])
        
        # High energy: occasional effects
        if energy_level == EnergyLevel.HIGH:
            # 30% chance of effect on high energy cuts
            import random
            if random.random() < 0.3:
                if cut_duration < 1.0:
                    # Fast cuts: use zoom
                    return EffectType.ZOOM
                else:
                    # Longer cuts: use shake or speed ramp
                    return random.choice([EffectType.SHAKE, EffectType.SPEED_RAMP])
        
        # Medium energy: rare effects
        elif energy_level == EnergyLevel.MEDIUM:
            # 10% chance of subtle effect
            import random
            if random.random() < 0.1:
                return EffectType.ZOOM
        
        # Low energy: no effects (cinematic)
        return EffectType.NONE
    
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
