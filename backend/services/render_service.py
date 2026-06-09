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
        quality: str = "balanced",
        aspect_ratio: str = "16:9",
        vertical_mode: str = "blurred",
        safe_mode: bool = False,
    ) -> ExportResult:
        """
        Render complete AMV from timeline

        Safe mode (true when the orchestrator detected memory pressure
        or insufficient footage) strips effects + complex transitions
        and forces ultrafast x264 settings to keep the render reliable
        on small containers.
        """
        if safe_mode:
            # Mutate a shallow copy of the timeline: drop every effect
            # and reduce all transitions to None (clean hard cuts).
            # We don't deep-copy segments because each one is a Pydantic
            # model -- assigning fields is fine.
            for seg in timeline.segments:
                seg.effect = None
                seg.transition = None
            logger.warning(
                "Render in SAFE MODE: %d segments, effects=stripped, "
                "transitions=hard-cut only (%s)",
                len(timeline.segments),
                timeline.safe_mode_reason or "memory budget",
            )

        logger.info(
            f"Starting render: {len(timeline.segments)} segments, "
            f"{timeline.total_duration:.2f}s, aspect={aspect_ratio} ({vertical_mode})"
            f"{' [SAFE MODE]' if safe_mode else ''}"
        )
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
                quality=quality,
                aspect_ratio=aspect_ratio,
                vertical_mode=vertical_mode,
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
            # Always clean intermediates on success so disk doesn't fill
            # over time on long-running Railway containers.
            try:
                await self._cleanup_intermediates()
            except Exception as cleanup_exc:
                logger.warning(f"Post-success cleanup error (non-fatal): {cleanup_exc}")

            return export
            
        except Exception as e:
            logger.error(f"Render failed: {e}", exc_info=True)
            # Always attempt cleanup on failure so we don't leak temp
            # files; never let cleanup mask the original exception.
            try:
                await self._cleanup_intermediates()
            except Exception as cleanup_exc:
                logger.warning(f"Post-failure cleanup error (suppressed): {cleanup_exc}")
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
            
            # Step 2: Apply effect if specified.  If the effect fails (e.g.
            # zoompan rejecting a tiny clip, or shake on a 0.3s segment),
            # fall back to the trimmed clip without the effect rather than
            # aborting the whole render -- the AMV will still be produced.
            if segment.effect and segment.effect != "none":
                try:
                    effected = await self._apply_effect(trimmed, segment.effect, i)
                    self.intermediate_files.append(effected)
                    processed.append(effected)
                except Exception as effect_exc:
                    logger.warning(
                        f"Segment {i}: effect '{segment.effect}' failed -- "
                        f"falling back to trimmed clip. Error: {effect_exc}"
                    )
                    processed.append(trimmed)
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
        
        # SAFETY: Validate segment durations before attempting transitions
        # Minimum segment duration to safely apply transitions.  AMV
        # pacing on a fast BPM often yields 0.5s segments; trying to xfade
        # those is both slow (xfade is O(overlap*resolution)) and creates
        # visual mush.  Raising the threshold to 0.8s means very short
        # segments use hard cuts -- which is the actual AMV aesthetic on
        # high-energy passages anyway.
        MIN_DURATION_FOR_TRANSITION = 0.8
        
        # Apply transitions between consecutive segments with safety checks
        transitioned_segments = []
        
        for i in range(len(processed_segments)):
            if i == 0:
                # First segment: no transition, just add it
                transitioned_segments.append(processed_segments[i])
            else:
                # Check if both segments are long enough for transition
                prev_seg = processed_segments[i - 1]
                curr_seg = processed_segments[i]
                transition_type = timeline_segments[i].transition
                
                # SAFETY: Validate segment durations
                try:
                    prev_meta = await self.ffmpeg.probe(prev_seg)
                    curr_meta = await self.ffmpeg.probe(curr_seg)
                    
                    prev_duration = prev_meta['duration']
                    curr_duration = curr_meta['duration']
                    
                    can_apply_transition = (
                        prev_duration >= MIN_DURATION_FOR_TRANSITION and
                        curr_duration >= MIN_DURATION_FOR_TRANSITION
                    )
                    
                    if not can_apply_transition:
                        logger.warning(
                            f"Segments too short for transition (prev={prev_duration:.2f}s, curr={curr_duration:.2f}s), "
                            f"skipping transition and using direct concat"
                        )
                        transition_type = None
                    
                except Exception as e:
                    logger.warning(f"Failed to probe segment durations: {e}, skipping transition")
                    transition_type = None
                
                if transition_type and transition_type != "none":
                    # Attempt to apply transition with fallback
                    try:
                        logger.debug(f"Applying {transition_type} transition between segment {i-1} and {i}")
                        transitioned = await self._apply_transition_safe(
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
                    except Exception as e:
                        logger.error(f"Transition failed: {e}, falling back to direct concatenation")
                        # Fallback: just add current segment without transition
                        transitioned_segments.append(curr_seg)
                else:
                    # No transition, just add current segment
                    transitioned_segments.append(curr_seg)
        
        # Concatenate all segments.
        # Defensive: drop any segment that has no decodable video (a
        # 0-duration trim or a corrupt intermediate file would cause the
        # concat filter to fail with 'matches no streams').
        valid_segments: List[str] = []
        for seg in transitioned_segments:
            try:
                meta = await self.ffmpeg.probe(seg)
                if meta.get("duration", 0.0) >= 0.05 and meta.get("width", 0) > 0:
                    valid_segments.append(seg)
                else:
                    logger.warning(
                        f"Dropping unusable segment before concat: {seg} "
                        f"(duration={meta.get('duration')}, "
                        f"{meta.get('width')}x{meta.get('height')})"
                    )
            except Exception as exc:
                logger.warning(f"Dropping unprobeable segment {seg}: {exc}")

        if not valid_segments:
            raise FFmpegError(
                "All segments were invalid -- nothing to concatenate. "
                "This usually means the timeline produced 0-duration trims."
            )

        logger.info(
            f"Concatenating {len(valid_segments)} valid segments "
            f"(dropped {len(transitioned_segments) - len(valid_segments)})..."
        )
        output_path = str(self.work_dir / "merged_video.mp4")
        
        merged = await self.ffmpeg.concatenate(
            valid_segments,
            output_path
        )
        self.intermediate_files.append(merged)
        
        logger.info(f"Merge complete: {merged}")
        return merged
    
    async def _apply_transition_safe(
        self,
        clip1_path: str,
        clip2_path: str,
        transition_type: str,
        index: int
    ) -> str:
        """
        Apply transition between two clips with error recovery
        
        Fallback order:
        1. Try requested transition type
        2. If fails, try simple fade
        3. If still fails, return concatenated clips without transition
        """
        output_path = str(self.work_dir / f"trans_{index:04d}_{transition_type}.mp4")
        
        # Map transition types
        valid_transitions = ["fade", "flash", "zoom"]
        if transition_type not in valid_transitions:
            logger.warning(f"Unknown transition type: {transition_type}, using fade")
            transition_type = "fade"
        
        # Try primary transition
        try:
            return await self.ffmpeg.apply_transition(
                clip1_path,
                clip2_path,
                transition_type,
                duration=0.5,
                output_path=output_path
            )
        except Exception as e:
            logger.warning(f"Primary transition '{transition_type}' failed: {e}")
            
            # Fallback 1: Try simple fade if not already using it
            if transition_type != "fade":
                try:
                    logger.info("Attempting fallback to fade transition...")
                    return await self.ffmpeg.apply_transition(
                        clip1_path,
                        clip2_path,
                        "fade",
                        duration=0.3,  # Shorter duration for stability
                        output_path=output_path
                    )
                except Exception as e2:
                    logger.warning(f"Fade fallback also failed: {e2}")
            
            # Fallback 2: Simple concatenation without transition
            logger.info("All transitions failed, using direct concatenation")
            concat_path = str(self.work_dir / f"concat_{index:04d}.mp4")
            return await self.ffmpeg.concatenate(
                [clip1_path, clip2_path],
                concat_path
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
