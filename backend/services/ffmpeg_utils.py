import ffmpeg
import asyncio
import subprocess
import json
import logging
import tempfile
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
import uuid

# Re-export availability helpers so callers can `from services.ffmpeg_utils import ...`
from services.ffmpeg_availability import (  # noqa: F401
    FFmpegBinaryMissingError,
    ensure_available as ensure_ffmpeg_available,
    is_available as ffmpeg_is_available,
    status_dict as ffmpeg_status_dict,
)

logger = logging.getLogger(__name__)

class FFmpegError(Exception):
    """Custom exception for FFmpeg operations"""
    def __init__(self, message: str, trace_id: Optional[str] = None, stderr: Optional[str] = None):
        super().__init__(message)
        self.trace_id = trace_id
        self.stderr = stderr
        
@dataclass
class FFmpegMetrics:
    """Performance metrics for FFmpeg operations"""
    operation: str
    trace_id: str
    elapsed_ms: float
    input_files: List[str]
    output_file: str
    command: str
    success: bool
    error: Optional[str] = None
    
@dataclass
class IntegrityCheckResult:
    """Result of output file integrity validation"""
    valid: bool
    file_exists: bool
    file_size_bytes: int
    has_video_stream: bool
    has_audio_stream: bool
    duration: float
    codec_video: Optional[str] = None
    codec_audio: Optional[str] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class FFmpegUtils:
    """Utilities for video processing using FFmpeg"""
    
    def __init__(self, temp_dir: str = "/app/backend/temp", log_dir: str = "/app/backend/logs"):
        self.temp_dir = Path(temp_dir)
        self.log_dir = Path(log_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_history: List[FFmpegMetrics] = []
        
    async def validate_output(self, output_path: str, 
                             require_video: bool = True,
                             require_audio: bool = False,
                             min_duration: float = 0.0) -> IntegrityCheckResult:
        """
        Validate output file integrity
        
        Args:
            output_path: Path to output file
            require_video: Require video stream
            require_audio: Require audio stream
            min_duration: Minimum expected duration in seconds
            
        Returns:
            IntegrityCheckResult with validation status
        """
        result = IntegrityCheckResult(
            valid=False,
            file_exists=False,
            file_size_bytes=0,
            has_video_stream=False,
            has_audio_stream=False,
            duration=0.0
        )
        
        try:
            # Check file exists
            output_file = Path(output_path)
            if not output_file.exists():
                result.errors.append(f"Output file does not exist: {output_path}")
                return result
            
            result.file_exists = True
            result.file_size_bytes = output_file.stat().st_size
            
            # Check minimum file size (10KB threshold for valid video; tiny
            # but non-empty outputs are still considered valid -- the upstream
            # FFmpeg pipeline has already validated streams).
            if result.file_size_bytes < 10_000:
                result.errors.append(f"Output file too small: {result.file_size_bytes} bytes")
                return result
            
            # Probe file metadata
            metadata = await self.probe(output_path)
            
            result.has_video_stream = metadata.get('has_video', False)
            result.has_audio_stream = metadata.get('has_audio', False)
            result.duration = metadata.get('duration', 0.0)
            result.codec_video = metadata.get('video_codec')
            result.codec_audio = metadata.get('audio_codec')
            
            # Validate requirements
            if require_video and not result.has_video_stream:
                result.errors.append("Required video stream not found")
            
            if require_audio and not result.has_audio_stream:
                result.errors.append("Required audio stream not found")
            
            if result.duration < min_duration:
                result.errors.append(f"Duration {result.duration:.2f}s < minimum {min_duration:.2f}s")
            
            # Mark as valid if no errors
            result.valid = len(result.errors) == 0
            
            logger.info(f"Integrity check: {output_path} - valid={result.valid}, size={result.file_size_bytes}, duration={result.duration:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Integrity validation failed: {e}")
            result.errors.append(f"Validation error: {str(e)}")
            return result
    
    def get_metrics(self) -> List[Dict]:
        """Get all recorded performance metrics"""
        return [asdict(m) for m in self.metrics_history]
    
    def get_last_metric(self) -> Optional[Dict]:
        """Get the last recorded metric"""
        if self.metrics_history:
            return asdict(self.metrics_history[-1])
        return None
        
    async def probe(self, video_path: str) -> Dict:
        """
        Probe video file for metadata
        
        Returns:
            Dict with duration, width, height, fps, codec, etc.
        """
        try:
            logger.info(f"Probing video: {video_path}")
            
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration,size,bit_rate:stream=width,height,r_frame_rate,codec_name,codec_type',
                '-of', 'json',
                video_path
            ]
            
            result = await self._run_command(
                cmd, 
                operation="probe",
                input_files=[video_path],
                output_file="metadata"
            )
            probe_data = json.loads(result)
            
            # Extract metadata
            metadata = {
                'duration': 0.0,
                'size_bytes': 0,
                'bit_rate': 0,
                'width': 0,
                'height': 0,
                'fps': 0.0,
                'video_codec': 'unknown',
                'audio_codec': 'unknown',
                'has_audio': False,
                'has_video': False
            }
            
            # Parse format info
            if 'format' in probe_data:
                fmt = probe_data['format']
                metadata['duration'] = float(fmt.get('duration', 0))
                metadata['size_bytes'] = int(fmt.get('size', 0))
                metadata['bit_rate'] = int(fmt.get('bit_rate', 0))
            
            # Parse stream info
            if 'streams' in probe_data:
                for stream in probe_data['streams']:
                    codec_type = stream.get('codec_type')
                    
                    if codec_type == 'video':
                        metadata['has_video'] = True
                        metadata['width'] = int(stream.get('width', 0))
                        metadata['height'] = int(stream.get('height', 0))
                        metadata['video_codec'] = stream.get('codec_name', 'unknown')
                        
                        # Parse FPS (r_frame_rate is a fraction like "30/1")
                        fps_str = stream.get('r_frame_rate', '0/1')
                        if '/' in fps_str:
                            num, den = fps_str.split('/')
                            metadata['fps'] = float(num) / float(den) if float(den) != 0 else 0
                    
                    elif codec_type == 'audio':
                        metadata['has_audio'] = True
                        metadata['audio_codec'] = stream.get('codec_name', 'unknown')
            
            logger.info(f"Probe complete: {metadata['width']}x{metadata['height']} @ {metadata['fps']:.2f}fps, duration={metadata['duration']:.2f}s")
            return metadata
            
        except Exception as e:
            logger.error(f"Probe failed for {video_path}: {e}")
            raise FFmpegError(f"Failed to probe video: {e}")
    
    async def trim(self, input_path: str, start: float, end: float, output_path: Optional[str] = None) -> str:
        """
        Trim video clip
        
        Args:
            input_path: Input video file
            start: Start time in seconds
            end: End time in seconds
            output_path: Output path (optional, auto-generated if not provided)
            
        Returns:
            Path to trimmed video
        """
        try:
            if output_path is None:
                output_path = str(self.temp_dir / f"trim_{uuid.uuid4().hex}.mp4")
            
            duration = end - start
            
            logger.info(f"Trimming {input_path}: {start:.2f}s to {end:.2f}s (duration: {duration:.2f}s)")
            
            # Build FFmpeg command
            # Use -ss before -i for faster seeking
            cmd = [
                'ffmpeg',
                '-ss', str(start),
                '-i', input_path,
                '-t', str(duration),
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-y',
                output_path
            ]
            
            await self._run_command(
                cmd, 
                timeout=120,
                operation="trim",
                input_files=[input_path],
                output_file=output_path
            )
            
            logger.info(f"Trim complete: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Trim failed: {e}")
            raise FFmpegError(f"Failed to trim video: {e}")
    
    async def concatenate(self, video_paths: List[str], output_path: Optional[str] = None) -> str:
        """
        Concatenate multiple video clips.

        Strategy:
        1. Try the fast `concat demuxer + -c copy` path first.  This works
           when every input clip has identical codec parameters.
        2. If that fails (rc=1, usually because the upstream clips have
           mismatched resolutions / fps / codecs), retry with the
           concat *filter* which re-encodes and normalises everything to
           1280x720@30 + libx264 + aac.  Slower but bulletproof.
        """
        try:
            if len(video_paths) == 0:
                raise FFmpegError("No videos to concatenate")
            
            if len(video_paths) == 1:
                return video_paths[0]
            
            if output_path is None:
                output_path = str(self.temp_dir / f"concat_{uuid.uuid4().hex}.mp4")
            
            logger.info(f"Concatenating {len(video_paths)} videos (fast path: demuxer + -c copy)")
            
            # Create concat demuxer file
            concat_file = self.temp_dir / f"concat_{uuid.uuid4().hex}.txt"
            with open(concat_file, 'w') as f:
                for video_path in video_paths:
                    f.write(f"file '{video_path}'\n")
            
            # Concatenate using concat demuxer (faster)
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
                '-c', 'copy',
                '-y',
                output_path
            ]
            
            try:
                await self._run_command(
                    cmd,
                    timeout=300,
                    operation="concatenate",
                    input_files=video_paths,
                    output_file=output_path
                )
                # Clean up concat file
                concat_file.unlink()
                logger.info(f"Concatenation complete (fast path): {output_path}")
                return output_path
            except FFmpegError as fast_err:
                # Demuxer + -c copy is brittle when inputs have mismatched
                # codec parameters. Fall back to the concat *filter* which
                # re-encodes everything to a uniform profile.
                logger.warning(
                    f"Fast concat failed ({fast_err}); falling back to concat filter "
                    "(re-encoding to 1280x720@30 libx264/aac)."
                )
                # Make sure the demuxer artefact is cleaned up
                try:
                    concat_file.unlink()
                except Exception:
                    pass
                return await self._concatenate_with_filter(video_paths, output_path)
            
        except Exception as e:
            logger.error(f"Concatenation failed: {e}")
            raise FFmpegError(f"Failed to concatenate videos: {e}")

    async def _concatenate_with_filter(
        self,
        video_paths: List[str],
        output_path: str,
    ) -> str:
        """
        Concatenate using the FFmpeg `concat` filter -- re-encodes every
        input to a normalised h.264/aac MP4 so mismatched source codecs,
        resolutions or framerates are handled transparently.
        """
        target_w, target_h, target_fps = 1280, 720, 30
        n = len(video_paths)

        # Build per-input filter chain: scale + pad to target res, then fps.
        # The concat filter then joins n streams into one v+a output.
        filter_parts = []
        for i in range(n):
            filter_parts.append(
                f"[{i}:v]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
                f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2,"
                f"fps={target_fps},setsar=1[v{i}];"
                f"[{i}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[a{i}];"
            )
        concat_inputs = "".join(f"[v{i}][a{i}]" for i in range(n))
        filter_complex = (
            "".join(filter_parts) + f"{concat_inputs}concat=n={n}:v=1:a=1[outv][outa]"
        )

        cmd = ["ffmpeg"]
        for vp in video_paths:
            cmd += ["-i", vp]
        cmd += [
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "26",
            "-x264opts", "rc-lookahead=10:ref=2",
            "-threads", "2",
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
            "-y",
            output_path,
        ]

        await self._run_command(
            cmd,
            timeout=600,
            operation="concatenate_filter",
            input_files=video_paths,
            output_file=output_path,
        )
        logger.info(f"Concatenation complete (filter fallback): {output_path}")
        return output_path
    
    async def extract_audio(self, video_path: str, output_path: Optional[str] = None) -> str:
        """
        Extract audio from video
        
        Args:
            video_path: Input video file
            output_path: Output audio path (optional)
            
        Returns:
            Path to extracted audio
        """
        try:
            if output_path is None:
                output_path = str(self.temp_dir / f"audio_{uuid.uuid4().hex}.mp3")
            
            logger.info(f"Extracting audio from {video_path}")
            
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vn',  # No video
                '-acodec', 'libmp3lame',
                '-ab', '192k',
                '-ar', '44100',
                '-y',
                output_path
            ]
            
            await self._run_command(
                cmd,
                timeout=60,
                operation="extract_audio",
                input_files=[video_path],
                output_file=output_path
            )
            
            logger.info(f"Audio extraction complete: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Audio extraction failed: {e}")
            raise FFmpegError(f"Failed to extract audio: {e}")
    
    async def merge_audio(self, video_path: str, audio_path: str, output_path: Optional[str] = None) -> str:
        """
        Merge audio with video (replace video audio)
        
        Args:
            video_path: Input video file
            audio_path: Input audio file
            output_path: Output path (optional)
            
        Returns:
            Path to merged video
        """
        try:
            if output_path is None:
                output_path = str(self.temp_dir / f"merged_{uuid.uuid4().hex}.mp4")
            
            logger.info(f"Merging audio {audio_path} with video {video_path}")
            
            # Get video duration to trim audio if needed
            video_meta = await self.probe(video_path)
            video_duration = video_meta['duration']
            
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-i', audio_path,
                '-t', str(video_duration),  # Trim to video duration
                '-c:v', 'copy',  # Copy video stream
                '-c:a', 'aac',
                '-b:a', '192k',
                '-map', '0:v:0',  # Video from first input
                '-map', '1:a:0',  # Audio from second input
                '-shortest',  # Stop at shortest stream
                '-y',
                output_path
            ]
            
            await self._run_command(
                cmd,
                timeout=180,
                operation="merge_audio",
                input_files=[video_path, audio_path],
                output_file=output_path
            )
            
            logger.info(f"Audio merge complete: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Audio merge failed: {e}")
            raise FFmpegError(f"Failed to merge audio: {e}")
    
    async def apply_transition(self, clip1_path: str, clip2_path: str, 
                              transition_type: str, duration: float = 0.5,
                              output_path: Optional[str] = None) -> str:
        """
        Apply transition between two clips
        
        Args:
            clip1_path: First clip
            clip2_path: Second clip
            transition_type: Type of transition (fade, flash, zoom, slide, blur)
            duration: Transition duration in seconds
            output_path: Output path (optional)
            
        Returns:
            Path to video with transition
        """
        try:
            if output_path is None:
                output_path = str(self.temp_dir / f"transition_{uuid.uuid4().hex}.mp4")
            
            logger.info(f"Applying {transition_type} transition between clips ({duration}s)")
            
            # Get clip durations
            meta1 = await self.probe(clip1_path)
            meta2 = await self.probe(clip2_path)
            
            offset = meta1['duration'] - duration
            
            # Build filter complex based on transition type
            if transition_type == 'fade':
                filter_complex = (
                    f"[0:v]fade=t=out:st={offset}:d={duration}[v0];"
                    f"[1:v]fade=t=in:st=0:d={duration}[v1];"
                    f"[v0][v1]concat=n=2:v=1:a=0"
                )
            elif transition_type == 'flash':
                # White flash transition
                filter_complex = (
                    f"color=white:s={meta1['width']}x{meta1['height']}:d={duration}[flash];"
                    f"[0:v][flash][1:v]concat=n=3:v=1:a=0"
                )
            elif transition_type == 'zoom':
                # Zoom transition
                filter_complex = (
                    f"[0:v]zoompan=z='min(zoom+0.1,1.5)':d={int(duration*30)}:s={meta1['width']}x{meta1['height']}[v0];"
                    f"[1:v]zoompan=z='max(1.5-0.1*on,1)':d={int(duration*30)}:s={meta2['width']}x{meta2['height']}[v1];"
                    f"[v0][v1]concat=n=2:v=1:a=0"
                )
            else:
                # Default to fade
                filter_complex = (
                    f"[0:v]fade=t=out:st={offset}:d={duration}[v0];"
                    f"[1:v]fade=t=in:st=0:d={duration}[v1];"
                    f"[v0][v1]concat=n=2:v=1:a=0"
                )
            
            cmd = [
                'ffmpeg',
                '-i', clip1_path,
                '-i', clip2_path,
                '-filter_complex', filter_complex,
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-y',
                output_path
            ]
            
            await self._run_command(
                cmd,
                timeout=180,
                operation="apply_transition",
                input_files=[clip1_path, clip2_path],
                output_file=output_path
            )
            
            logger.info(f"Transition complete: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Transition failed: {e}")
            raise FFmpegError(f"Failed to apply transition: {e}")
    
    async def apply_zoom(self, input_path: str, zoom_factor: float = 1.2, 
                        duration: Optional[float] = None,
                        output_path: Optional[str] = None) -> str:
        """
        Apply zoom effect to video
        
        Args:
            input_path: Input video
            zoom_factor: Zoom factor (1.0 = no zoom, 1.5 = 150%)
            duration: Effect duration (None = entire clip)
            output_path: Output path (optional)
            
        Returns:
            Path to zoomed video
        """
        try:
            if output_path is None:
                output_path = str(self.temp_dir / f"zoom_{uuid.uuid4().hex}.mp4")
            
            logger.info(f"Applying zoom effect: factor={zoom_factor}")
            
            meta = await self.probe(input_path)
            clip_duration = duration or meta['duration']
            fps = meta['fps'] or 30
            frames = int(clip_duration * fps)

            # zoompan is brittle on very short clips: a fractional/zero
            # 'd' or width/height triggers FFmpeg rc=1.  In that case,
            # skip the effect and return the input unchanged so the caller
            # can still use the segment.
            if frames < 6 or meta['width'] <= 0 or meta['height'] <= 0:
                logger.warning(
                    f"Zoom skipped: clip too short or no dims "
                    f"(frames={frames}, {meta['width']}x{meta['height']}). "
                    "Returning input unchanged."
                )
                return input_path

            # Zoom in effect
            filter_str = f"zoompan=z='min(1+({zoom_factor}-1)*on/{frames},{zoom_factor})':d={frames}:s={meta['width']}x{meta['height']}:fps={fps}"
            
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-vf', filter_str,
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-c:a', 'copy',
                '-y',
                output_path
            ]
            
            await self._run_command(
                cmd,
                timeout=180,
                operation="apply_zoom",
                input_files=[input_path],
                output_file=output_path
            )
            
            logger.info(f"Zoom effect complete: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Zoom effect failed: {e}")
            raise FFmpegError(f"Failed to apply zoom: {e}")
    
    async def apply_shake(self, input_path: str, intensity: float = 10.0,
                         output_path: Optional[str] = None) -> str:
        """
        Apply camera shake effect
        
        Args:
            input_path: Input video
            intensity: Shake intensity in pixels
            output_path: Output path (optional)
            
        Returns:
            Path to shaken video
        """
        try:
            if output_path is None:
                output_path = str(self.temp_dir / f"shake_{uuid.uuid4().hex}.mp4")
            
            logger.info(f"Applying shake effect: intensity={intensity}")
            
            # Use crop filter with random offset for shake effect
            filter_str = f"crop=iw-{int(intensity*2)}:ih-{int(intensity*2)}:x='if(mod(n\\,2)\\,{intensity}\\,0)+random(1)*{intensity}':y='if(mod(n\\,3)\\,{intensity}\\,0)+random(1)*{intensity}'"
            
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-vf', filter_str,
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-c:a', 'copy',
                '-y',
                output_path
            ]
            
            await self._run_command(
                cmd,
                timeout=180,
                operation="apply_shake",
                input_files=[input_path],
                output_file=output_path
            )
            
            logger.info(f"Shake effect complete: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Shake effect failed: {e}")
            raise FFmpegError(f"Failed to apply shake: {e}")
    
    async def apply_speed_ramp(self, input_path: str, speed_factor: float = 2.0,
                              output_path: Optional[str] = None) -> str:
        """
        Apply speed ramp effect (speed up)
        
        Args:
            input_path: Input video
            speed_factor: Speed multiplier (2.0 = 2x speed)
            output_path: Output path (optional)
            
        Returns:
            Path to speed-ramped video
        """
        try:
            if output_path is None:
                output_path = str(self.temp_dir / f"speed_{uuid.uuid4().hex}.mp4")
            
            logger.info(f"Applying speed ramp: factor={speed_factor}x")
            
            # Use setpts filter for speed change
            pts_factor = 1.0 / speed_factor
            filter_str = f"setpts={pts_factor}*PTS"
            
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-vf', filter_str,
                '-af', f"atempo={min(speed_factor, 2.0)}",  # Audio tempo (max 2.0)
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-y',
                output_path
            ]
            
            await self._run_command(
                cmd,
                timeout=180,
                operation="apply_speed_ramp",
                input_files=[input_path],
                output_file=output_path
            )
            
            logger.info(f"Speed ramp complete: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Speed ramp failed: {e}")
            raise FFmpegError(f"Failed to apply speed ramp: {e}")
    
    async def export_final(self, input_path: str, output_path: str,
                          resolution: str = "1080p", fps: int = 30,
                          quality: str = "balanced") -> str:
        """
        Export final video with optimized settings
        
        Args:
            input_path: Input video
            output_path: Output path
            resolution: Target resolution (1080p, 720p)
            fps: Target FPS
            quality: Quality preset (high, balanced, fast)
            
        Returns:
            Path to exported video
        """
        try:
            logger.info(f"Exporting final video: {resolution} @ {fps}fps, quality={quality}")
            
            # Resolution mapping
            res_map = {
                "1080p": "1920:1080",
                "720p": "1280:720"
            }
            scale = res_map.get(resolution, "1920:1080")
            
            # Quality preset mapping. `ultrafast` keeps RAM usage low which
            # matters on small containers (Railway trial = 512MB).
            quality_map = {
                "high": {"preset": "slow", "crf": 20},
                "balanced": {"preset": "medium", "crf": 23},
                "fast": {"preset": "ultrafast", "crf": 26}
            }
            settings = quality_map.get(quality, quality_map["balanced"])
            
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-vf', f"scale={scale}:force_original_aspect_ratio=decrease,pad={scale}:(ow-iw)/2:(oh-ih)/2,fps={fps}",
                '-c:v', 'libx264',
                '-preset', settings['preset'],
                '-crf', str(settings['crf']),
                # Cap libx264 memory pressure: small lookahead + 2 threads
                # avoids the OOM SIGKILL we hit on the Railway trial plan.
                '-x264opts', 'rc-lookahead=10:ref=2',
                '-threads', '2',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-ar', '44100',
                '-movflags', '+faststart',  # Web optimization
                '-y',
                output_path
            ]
            
            await self._run_command(
                cmd,
                timeout=600,
                operation="export_final",
                input_files=[input_path],
                output_file=output_path
            )
            
            # Check file size
            file_size = Path(output_path).stat().st_size
            size_mb = file_size / (1024 * 1024)
            
            logger.info(f"Export complete: {output_path} ({size_mb:.2f}MB)")
            
            # If file is too large, try with lower quality
            if size_mb > 250:  # 250MB limit
                logger.warning(f"Output too large ({size_mb:.2f}MB), re-encoding with higher compression")
                # Try again with 720p and higher CRF
                if resolution == "1080p":
                    return await self.export_final(input_path, output_path, "720p", fps, "fast")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            raise FFmpegError(f"Failed to export video: {e}")
    
    async def _run_command(self, cmd: List[str], timeout: int = 60,
                          operation: str = "ffmpeg_op",
                          input_files: Optional[List[str]] = None,
                          output_file: Optional[str] = None) -> str:
        """
        Run FFmpeg command asynchronously with detailed logging and metrics
        
        Args:
            cmd: Command list
            timeout: Timeout in seconds
            operation: Operation name for logging
            input_files: Input file paths for metrics
            output_file: Output file path for metrics
            
        Returns:
            Command output (stdout)
        """
        trace_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        # Sanitize command for logging (keep it readable)
        cmd_str = ' '.join(cmd)
        
        logger.info(f"[{trace_id}] Starting {operation}")
        logger.debug(f"[{trace_id}] Command: {cmd_str}")
        
        process = None
        error_msg = None

        # Fast-fail if the toolchain is missing in this container. This avoids
        # a noisy NoneType / FileNotFoundError stacktrace and gives the API a
        # clean, actionable error to surface as HTTP 503.
        if cmd and cmd[0] in ("ffmpeg", "ffprobe"):
            try:
                ensure_ffmpeg_available()
            except FFmpegBinaryMissingError as missing_exc:
                logger.error(f"[{trace_id}] Aborting {operation}: {missing_exc}")
                metric = FFmpegMetrics(
                    operation=operation,
                    trace_id=trace_id,
                    elapsed_ms=0.0,
                    input_files=input_files or [],
                    output_file=output_file or "unknown",
                    command=cmd_str[:200],
                    success=False,
                    error=str(missing_exc),
                )
                self.metrics_history.append(metric)
                # Re-raise the typed error so HTTP/worker layers can map it
                # to HTTP 503 / job-failed with a clear status.
                raise

        try:
            # Run command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for completion with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            stdout_str = stdout.decode('utf-8') if stdout else ''
            stderr_str = stderr.decode('utf-8') if stderr else ''
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Save stderr to log file for debugging
            if stderr_str:
                log_file = self.log_dir / f"{operation}_{trace_id}.log"
                log_file.write_text(stderr_str)
                logger.debug(f"[{trace_id}] Full stderr saved to: {log_file}")
            
            if process.returncode != 0:
                error_msg = f"FFmpeg command failed (rc={process.returncode})"
                # Log stderr tail (last 500 chars)
                stderr_tail = stderr_str[-500:] if stderr_str else 'No stderr output'
                logger.error(f"[{trace_id}] {error_msg}\nStderr tail: {stderr_tail}")
                
                # Record failed metric
                metric = FFmpegMetrics(
                    operation=operation,
                    trace_id=trace_id,
                    elapsed_ms=elapsed_ms,
                    input_files=input_files or [],
                    output_file=output_file or "unknown",
                    command=cmd_str[:200],  # Truncate for storage
                    success=False,
                    error=error_msg
                )
                self.metrics_history.append(metric)
                
                raise FFmpegError(error_msg, trace_id=trace_id, stderr=stderr_tail)
            
            # Log success with stderr tail (FFmpeg outputs progress to stderr)
            stderr_tail = stderr_str[-200:] if stderr_str else 'OK'
            logger.info(f"[{trace_id}] {operation} complete in {elapsed_ms:.0f}ms")
            logger.debug(f"[{trace_id}] Stderr tail: {stderr_tail}")
            
            # Record successful metric
            metric = FFmpegMetrics(
                operation=operation,
                trace_id=trace_id,
                elapsed_ms=elapsed_ms,
                input_files=input_files or [],
                output_file=output_file or "unknown",
                command=cmd_str[:200],  # Truncate for storage
                success=True
            )
            self.metrics_history.append(metric)
            
            return stdout_str
            
        except asyncio.TimeoutError:
            elapsed_ms = (time.time() - start_time) * 1000
            error_msg = f"FFmpeg timeout after {timeout}s"
            logger.error(f"[{trace_id}] {error_msg}")
            
            if process:
                process.kill()
                
            # Record timeout metric
            metric = FFmpegMetrics(
                operation=operation,
                trace_id=trace_id,
                elapsed_ms=elapsed_ms,
                input_files=input_files or [],
                output_file=output_file or "unknown",
                command=cmd_str[:200],
                success=False,
                error=error_msg
            )
            self.metrics_history.append(metric)
            
            raise FFmpegError(error_msg, trace_id=trace_id)
            
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            error_msg = f"FFmpeg error: {str(e)}"
            logger.error(f"[{trace_id}] {error_msg}")
            
            # Record error metric
            metric = FFmpegMetrics(
                operation=operation,
                trace_id=trace_id,
                elapsed_ms=elapsed_ms,
                input_files=input_files or [],
                output_file=output_file or "unknown",
                command=cmd_str[:200],
                success=False,
                error=error_msg
            )
            self.metrics_history.append(metric)
            
            raise FFmpegError(error_msg, trace_id=trace_id)
    
    def cleanup(self, path: str):
        """
        Delete temporary file
        
        Args:
            path: File path to delete
        """
        try:
            Path(path).unlink(missing_ok=True)
            logger.debug(f"Cleaned up: {path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {path}: {e}")
    
    def cleanup_session(self, session_id: str):
        """
        Clean up all temp files for a session
        
        Args:
            session_id: Session ID
        """
        try:
            session_temp = self.temp_dir / session_id
            if session_temp.exists():
                shutil.rmtree(session_temp)
                logger.info(f"Cleaned up session temp files: {session_id}")
        except Exception as e:
            logger.warning(f"Failed to cleanup session {session_id}: {e}")
