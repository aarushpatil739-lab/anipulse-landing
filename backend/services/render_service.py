"""
Render Service

Executes generated timeline JSON using FFmpegUtils to produce final AMV.

Modular pipeline:
1. Prepare workspace
2. Process segments (trim, transition, effect)
3. Concatenate all segments
4. Merge final audio
5. Export optimized MP4
6. Validate output
7. Cleanup intermediates
"""

import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import uuid
import time

from services.ffmpeg_utils import FFmpegUtils, FFmpegError
from models.generation_job import GeneratedTimeline, TimelineSegment, ExportResult

logger = logging.getLogger(__name__)


class RenderService:
    """
    Render Service
    
    Executes timeline JSON to produce final AMV using FFmpegUtils.
    """
    
    def __init__(self, job_id: str, work_dir: Optional[str] = None):
        """
        Initialize render service
        
        Args:
            job_id: Generation job ID
            work_dir: Working directory for intermediate files
        """
        self.job_id = job_id
        self.work_dir = Path(work_dir or f"/app/backend/temp/jobs/{job_id}")
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        self.export_dir = Path(f"/app/backend/exports/jobs/{job_id}")
        self.export_dir.mkdir(parents=True, exist_ok=True)
        
        self.ffmpeg = FFmpegUtils()
        self.intermediate_files: List[str] = []
        
        logger.info(f"RenderService initialized for job {job_id}")
        logger.info(f"Work dir: {self.work_dir}")
        logger.info(f"Export dir: {self.export_dir}")
    
    async def render(
        self,
        timeline: GeneratedTimeline,
        audio_path: str,
        resolution: str = "1080p",
        fps: int = 30,
        quality: str = "balanced"
    ) -> ExportResult:
        """
        Render complete AMV from timeline
        
        Args:
            timeline: Generated timeline with segments
            audio_path: Path to music file
            resolution: Target resolution (1080p, 720p)
            fps: Target FPS
            quality: Quality preset (high, balanced, fast)
            
        Returns:
            ExportResult with final video metadata
        """
        logger.info(f"Starting render: {len(timeline.segments)} segments, {timeline.total_duration:.2f}s")
        start_time = time.time()
        
        try:
            # Step 1: Process all segments (trim + effects)
            processed_segments = await self._process_all_segments(timeline.segments)
            
            # Step 2: Apply transitions and concatenate
            merged_video = await self._apply_transitions_and_merge(
                processed_segments,
                timeline.segments
            )
            
            # Step 3: Merge audio with video
            with_audio = await self._merge_audio(merged_video, audio_path)
            
            # Step 4: Export final optimized MP4
            final_path = str(self.export_dir / "final.mp4")
            final_output = await self.ffmpeg.export_final(
                with_audio,
                final_path,
                resolution=resolution,
                fps=fps,
                quality=quality
            )
            
            # Step 5: Validate output
            integrity = await self.ffmpeg.validate_output(
                final_output,
                require_video=True,
                require_audio=True,
                min_duration=1.0
            )
            
            if not integrity.valid:
                raise FFmpegError(f"Final output validation failed: {integrity.errors}")
            
            # Step 6: Cleanup intermediates
            await self._cleanup_intermediates()
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Create export result
            export = ExportResult(
                path=final_output,
                size_bytes=integrity.file_size_bytes,
                duration=integrity.duration,
                resolution=resolution,
                fps=fps,
                codec_video=integrity.codec_video or "h264",
                codec_audio=integrity.codec_audio or "aac"
            )
            
            logger.info(
                f"Render complete: {final_output}, "
                f"size={integrity.file_size_bytes / (1024*1024):.2f}MB, "
                f"duration={integrity.duration:.2f}s, "
                f"elapsed={elapsed_ms/1000:.1f}s"
            )
            
            return export
            
        except Exception as e:
            logger.error(f"Render failed: {e}", exc_info=True)
            await self._cleanup_intermediates()
            raise
    
    async def _process_all_segments(
        self,
        segments: List[TimelineSegment]
    ) -> List[str]:
        """
        Process all segments (trim and apply effects)
        
        Args:
            segments: List of timeline segments
            
        Returns:
            List of processed video file paths
        """
        logger.info(f"Processing {len(segments)} segments...")
        processed = []
        
        for i, segment in enumerate(segments):
            logger.debug(
                f"Processing segment {i+1}/{len(segments)}: "
                f"clip={segment.clip_index}, "
                f"source={segment.start_time:.2f}-{segment.end_time:.2f}s, "
                f"effect={segment.effect}"
            )
            
            # Step 1: Trim source clip
            trimmed = await self._trim_segment(segment, i)
            self.intermediate_files.append(trimmed)
            
            # Step 2: Apply effect if specified
            if segment.effect and segment.effect != "none":
                effected = await self._apply_effect(trimmed, segment.effect, i)
                self.intermediate_files.append(effected)
                processed.append(effected)
            else:
                processed.append(trimmed)
        
        logger.info(f"Segment processing complete: {len(processed)} files")
        return processed
    
    async def _trim_segment(
        self,
        segment: TimelineSegment,
        index: int
    ) -> str:
        """Trim video segment from source clip"""
        output_path = str(self.work_dir / f"seg_{index:04d}_trim.mp4")
        
        trimmed = await self.ffmpeg.trim(
            segment.clip_path,
            segment.start_time,
            segment.end_time,
            output_path
        )
        
        return trimmed
    
    async def _apply_effect(
        self,
        input_path: str,
        effect_type: str,
        index: int
    ) -> str:
        """Apply effect to video segment"""
        output_path = str(self.work_dir / f"seg_{index:04d}_{effect_type}.mp4")
        
        if effect_type == "zoom":
            return await self.ffmpeg.apply_zoom(
                input_path,
                zoom_factor=1.3,
                output_path=output_path
            )
        
        elif effect_type == "shake":
            return await self.ffmpeg.apply_shake(
                input_path,
                intensity=12.0,
                output_path=output_path
            )
        
        elif effect_type == "speed_ramp":
            return await self.ffmpeg.apply_speed_ramp(
                input_path,
                speed_factor=1.5,
                output_path=output_path
            )
        
        else:
            logger.warning(f"Unknown effect type: {effect_type}, skipping")
            return input_path
    
    async def _apply_transitions_and_merge(
        self,
        processed_segments: List[str],
        timeline_segments: List[TimelineSegment]
    ) -> str:
        """
        Apply transitions between segments and concatenate
        
        Args:
            processed_segments: List of processed segment file paths
            timeline_segments: Original timeline segments (for transition info)
            
        Returns:
            Path to merged video
        """
        logger.info(f"Applying transitions and merging {len(processed_segments)} segments...")
        
        if len(processed_segments) == 0:
            raise ValueError("No segments to merge")
        
        if len(processed_segments) == 1:
            # Single segment, no transitions needed
            return processed_segments[0]
        
        # Apply transitions between consecutive segments
        transitioned_segments = []
        
        for i in range(len(processed_segments)):
            if i == 0:
                # First segment: no transition, just add it
                transitioned_segments.append(processed_segments[i])
            else:
                # Apply transition between previous and current segment
                prev_seg = processed_segments[i - 1]
                curr_seg = processed_segments[i]
                transition_type = timeline_segments[i].transition
                
                if transition_type and transition_type != "none":
                    # Apply transition
                    logger.debug(f"Applying {transition_type} transition between segment {i-1} and {i}")
                    transitioned = await self._apply_transition(
                        prev_seg,
                        curr_seg,
                        transition_type,
                        i
                    )
                    self.intermediate_files.append(transitioned)
                    
                    # Replace the last segment in list with transitioned version
                    if transitioned_segments:
                        transitioned_segments.pop()
                    transitioned_segments.append(transitioned)
                else:
                    # No transition, just add current segment
                    transitioned_segments.append(curr_seg)
        
        # Concatenate all segments
        logger.info(f"Concatenating {len(transitioned_segments)} segments...")
        output_path = str(self.work_dir / "merged_video.mp4")
        
        merged = await self.ffmpeg.concatenate(
            transitioned_segments,
            output_path
        )
        self.intermediate_files.append(merged)
        
        logger.info(f"Merge complete: {merged}")
        return merged
    
    async def _apply_transition(
        self,
        clip1_path: str,
        clip2_path: str,
        transition_type: str,
        index: int
    ) -> str:
        """Apply transition between two clips"""
        output_path = str(self.work_dir / f"trans_{index:04d}_{transition_type}.mp4")
        
        # Map transition types
        valid_transitions = ["fade", "flash", "zoom"]
        if transition_type not in valid_transitions:
            logger.warning(f"Unknown transition type: {transition_type}, using fade")
            transition_type = "fade"
        
        return await self.ffmpeg.apply_transition(
            clip1_path,
            clip2_path,
            transition_type,
            duration=0.5,
            output_path=output_path
        )
    
    async def _merge_audio(
        self,
        video_path: str,
        audio_path: str
    ) -> str:
        """Merge audio track with video"""
        logger.info(f"Merging audio: {audio_path}")
        output_path = str(self.work_dir / "with_audio.mp4")
        
        merged = await self.ffmpeg.merge_audio(
            video_path,
            audio_path,
            output_path
        )
        self.intermediate_files.append(merged)
        
        return merged
    
    async def _cleanup_intermediates(self):
        """Cleanup intermediate files"""
        logger.info(f"Cleaning up {len(self.intermediate_files)} intermediate files...")
        
        cleaned = 0
        for path in self.intermediate_files:
            try:
                Path(path).unlink(missing_ok=True)
                cleaned += 1
            except Exception as e:
                logger.warning(f"Failed to cleanup {path}: {e}")
        
        logger.info(f"Cleanup complete: {cleaned}/{len(self.intermediate_files)} files removed")
        self.intermediate_files.clear()
    
    def get_render_stats(self) -> Dict:
        """Get render statistics"""
        return {
            "job_id": self.job_id,
            "work_dir": str(self.work_dir),
            "export_dir": str(self.export_dir),
            "intermediate_files_count": len(self.intermediate_files),
            "ffmpeg_metrics": self.ffmpeg.get_metrics()
        }
