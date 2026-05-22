import librosa
import numpy as np
import logging
from typing import Dict, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class AudioAnalyzer:
    """Service for analyzing audio files to extract beats, BPM, drops, and energy"""
    
    def __init__(self):
        self.sr = 22050  # Sample rate
    
    async def analyze(self, audio_path: str) -> Dict:
        """
        Analyze audio file and extract musical features
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dict with BPM, beats, drops, and energy curve
        """
        try:
            logger.info(f"Starting audio analysis for {audio_path}")
            
            # Load audio file
            y, sr = librosa.load(audio_path, sr=self.sr)
            duration = librosa.get_duration(y=y, sr=sr)
            
            logger.info(f"Audio loaded: duration={duration:.2f}s, sr={sr}")
            
            # Detect BPM
            bpm, beats = self._detect_bpm_and_beats(y, sr)
            
            # Detect drops/intensity spikes
            drops = self._detect_drops(y, sr)
            
            # Calculate energy curve
            energy_curve = self._calculate_energy_curve(y, sr)
            
            # Detect sections (high energy vs low energy)
            sections = self._detect_sections(energy_curve, beats)
            
            result = {
                "duration": float(duration),
                "bpm": float(bpm),
                "beats": [float(b) for b in beats],
                "drops": [float(d) for d in drops],
                "energy_curve": energy_curve,
                "sections": sections,
                "beat_intervals": self._calculate_beat_intervals(beats)
            }
            
            logger.info(f"Audio analysis complete: BPM={bpm:.1f}, beats={len(beats)}, drops={len(drops)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Audio analysis failed: {e}", exc_info=True)
            raise
    
    def _detect_bpm_and_beats(self, y: np.ndarray, sr: int) -> Tuple[float, np.ndarray]:
        """Detect BPM and beat timestamps"""
        # Detect tempo
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units='frames')
        
        # Convert frames to timestamps
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        
        return tempo, beat_times
    
    def _detect_drops(self, y: np.ndarray, sr: int) -> List[float]:
        """
        Detect drops/intensity spikes in the audio
        
        Uses spectral flux and energy spikes to identify drops
        """
        # Calculate spectral flux
        spec = np.abs(librosa.stft(y))
        flux = np.sqrt(np.sum(np.diff(spec, axis=1)**2, axis=0))
        
        # Smooth flux
        flux_smooth = librosa.util.smooth(flux, 3)
        
        # Find peaks in flux (potential drops)
        peaks = librosa.util.peak_pick(
            flux_smooth,
            pre_max=3,
            post_max=3,
            pre_avg=3,
            post_avg=5,
            delta=0.5,
            wait=10
        )
        
        # Convert to timestamps
        drop_times = librosa.frames_to_time(peaks, sr=sr, hop_length=512)
        
        # Filter to keep only significant drops (high energy spikes)
        # Calculate RMS energy around each drop
        rms = librosa.feature.rms(y=y)[0]
        significant_drops = []
        
        for drop_time in drop_times:
            frame = librosa.time_to_frames(drop_time, sr=sr, hop_length=512)
            if frame < len(rms):
                # Check if this is a significant energy spike
                window_start = max(0, frame - 5)
                window_end = min(len(rms), frame + 5)
                local_energy = np.mean(rms[window_start:window_end])
                
                # Compare to overall energy
                if local_energy > np.percentile(rms, 70):  # Top 30% energy
                    significant_drops.append(float(drop_time))
        
        logger.info(f"Detected {len(significant_drops)} significant drops")
        return significant_drops
    
    def _calculate_energy_curve(self, y: np.ndarray, sr: int) -> List[Dict]:
        """
        Calculate energy curve over time
        
        Returns energy values sampled at regular intervals
        """
        # Calculate RMS energy
        rms = librosa.feature.rms(y=y, hop_length=512)[0]
        
        # Convert to timestamps
        times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=512)
        
        # Normalize energy (0-1)
        rms_normalized = rms / (np.max(rms) + 1e-8)
        
        # Sample every 0.1 seconds for the curve
        sample_interval = 0.1
        duration = times[-1]
        num_samples = int(duration / sample_interval)
        
        energy_curve = []
        for i in range(num_samples):
            t = i * sample_interval
            # Find nearest RMS value
            idx = np.argmin(np.abs(times - t))
            energy_curve.append({
                "time": float(t),
                "energy": float(rms_normalized[idx])
            })
        
        return energy_curve
    
    def _detect_sections(self, energy_curve: List[Dict], beats: np.ndarray) -> List[Dict]:
        """
        Detect high-energy and low-energy sections
        
        Used for intelligent clip selection
        """
        if not energy_curve:
            return []
        
        energies = [e["energy"] for e in energy_curve]
        median_energy = np.median(energies)
        
        sections = []
        current_type = None
        section_start = 0
        
        for i, e in enumerate(energy_curve):
            energy_type = "high" if e["energy"] > median_energy else "low"
            
            if energy_type != current_type:
                if current_type is not None:
                    # Save previous section
                    sections.append({
                        "type": current_type,
                        "start": float(section_start),
                        "end": float(e["time"]),
                        "avg_energy": float(np.mean([ec["energy"] for ec in energy_curve[int(section_start*10):i]]))
                    })
                current_type = energy_type
                section_start = e["time"]
        
        # Add final section
        if current_type is not None:
            sections.append({
                "type": current_type,
                "start": float(section_start),
                "end": float(energy_curve[-1]["time"]),
                "avg_energy": float(np.mean([e["energy"] for e in energy_curve[int(section_start*10):]]))
            })
        
        logger.info(f"Detected {len(sections)} energy sections")
        return sections
    
    def _calculate_beat_intervals(self, beats: np.ndarray) -> List[Dict]:
        """
        Calculate intervals between beats
        
        Used for determining cut timing
        """
        if len(beats) < 2:
            return []
        
        intervals = []
        for i in range(len(beats) - 1):
            intervals.append({
                "start_beat": float(beats[i]),
                "end_beat": float(beats[i + 1]),
                "duration": float(beats[i + 1] - beats[i])
            })
        
        return intervals
