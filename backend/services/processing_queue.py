"""
Processing Queue

Async background processing queue for AMV generation jobs.

Features:
- Async job queue with worker loop
- State management (queued → analyzing → generating → rendering → completed/failed)
- Progress tracking with MongoDB persistence
- Graceful error handling and recovery
- Detailed structured logging
- Cancellation support
"""

import asyncio
import logging
from typing import Optional
from pathlib import Path
import time

from models.generation_job import GenerationJob, JobStatus, GenerationJobService, AudioAnalysisResult, ExportResult
from services.audio_analyzer import AudioAnalyzer
from services.timeline_generator import TimelineGenerator
from services.render_service import RenderService
from services.upload_session_service import UploadSessionService

logger = logging.getLogger(__name__)


class ProcessingQueue:
    """
    Async processing queue for AMV generation
    
    Single-worker queue for MVP (scalable to distributed workers later)
    """
    
    def __init__(self, db):
        """
        Initialize processing queue
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.job_service = GenerationJobService(db)
        self.upload_service = UploadSessionService(db)
        self.audio_analyzer = AudioAnalyzer()
        
        self.queue: asyncio.Queue = asyncio.Queue()
        self.worker_task: Optional[asyncio.Task] = None
        self.running = False
        
        logger.info("ProcessingQueue initialized")
    
    async def start(self):
        """Start background worker"""
        if self.running:
            logger.warning("ProcessingQueue already running")
            return
        
        self.running = True
        self.worker_task = asyncio.create_task(self._worker_loop())
        logger.info("ProcessingQueue worker started")
    
    async def stop(self):
        """Stop background worker"""
        if not self.running:
            return
        
        self.running = False
        
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        
        logger.info("ProcessingQueue worker stopped")
    
    async def enqueue_job(self, job: GenerationJob):
        """
        Add job to queue
        
        Args:
            job: Generation job to process
        """
        await self.queue.put(job.job_id)
        logger.info(f"Job {job.job_id} enqueued (queue size: {self.queue.qsize()})")
    
    async def _worker_loop(self):
        """Background worker loop"""
        logger.info("Worker loop started")
        
        while self.running:
            try:
                # Get next job from queue (with timeout to allow clean shutdown)
                try:
                    job_id = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                # Process job
                await self._process_job(job_id)
                
            except asyncio.CancelledError:
                logger.info("Worker loop cancelled")
                break
            except Exception as e:
                logger.error(f"Worker loop error: {e}", exc_info=True)
                await asyncio.sleep(1)  # Brief pause before continuing
        
        logger.info("Worker loop stopped")
    
    async def _process_job(self, job_id: str):
        """
        Process a single job through the complete pipeline
        
        Args:
            job_id: Job ID to process
        """
        logger.info(f"=== Processing job {job_id} ===")
        start_time = time.time()
        
        job = await self.job_service.get_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        
        try:
            # Stage 1: Analyzing Audio (5-25%)
            await self._stage_analyze_audio(job)
            
            # Stage 2: Generating Timeline (25-45%)
            await self._stage_generate_timeline(job)
            
            # Stage 3: Rendering (45-95%)
            await self._stage_render(job)
            
            # Stage 4: Completed (100%)
            job.update_progress(JobStatus.COMPLETED, 100.0, "Completed")
            
            elapsed_ms = (time.time() - start_time) * 1000
            job.timings.total_ms = elapsed_ms
            
            await self.job_service.update_job(job)
            
            logger.info(
                f"Job {job_id} completed successfully in {elapsed_ms/1000:.1f}s"
            )
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            
            # Mark job as failed
            error_msg = str(e)
            trace_id = getattr(e, 'trace_id', None)
            job.mark_failed(error_msg, trace_id=trace_id)
            
            await self.job_service.update_job(job)
    
    async def _stage_analyze_audio(self, job: GenerationJob):
        """Stage 1: Analyze audio"""
        logger.info(f"[{job.job_id}] Stage 1: Analyzing audio...")
        stage_start = time.time()
        
        job.update_progress(JobStatus.ANALYZING_AUDIO, 5.0, "Analyzing audio")
        await self.job_service.update_job(job)
        
        # Get audio file path
        if not job.input_audio or 'path' not in job.input_audio:
            raise ValueError("No audio file in job")
        
        audio_path = job.input_audio['path']
        
        # Analyze audio
        analysis_result = await self.audio_analyzer.analyze(audio_path)
        
        # Store analysis in job
        job.audio_analysis = AudioAnalysisResult(**analysis_result)
        
        # Update progress
        job.update_progress(JobStatus.ANALYZING_AUDIO, 25.0, "Audio analysis complete")
        job.timings.analyzing_audio_ms = (time.time() - stage_start) * 1000
        await self.job_service.update_job(job)
        
        logger.info(
            f"[{job.job_id}] Audio analysis complete: "
            f"BPM={analysis_result['bpm']:.1f}, "
            f"beats={len(analysis_result['beats'])}, "
            f"drops={len(analysis_result['drops'])}"
        )
    
    async def _stage_generate_timeline(self, job: GenerationJob):
        """Stage 2: Generate timeline"""
        logger.info(f"[{job.job_id}] Stage 2: Generating timeline...")
        stage_start = time.time()
        
        job.update_progress(JobStatus.GENERATING_TIMELINE, 30.0, "Generating timeline")
        await self.job_service.update_job(job)
        
        if not job.audio_analysis:
            raise ValueError("Audio analysis not available")
        
        # Convert audio analysis to dict
        audio_dict = job.audio_analysis.model_dump()
        
        # Generate timeline
        generator = TimelineGenerator(
            audio_analysis=audio_dict,
            clips_metadata=job.input_clips,
            max_duration=180.0,  # 3 minute cap
            style=job.style
        )
        
        timeline = generator.generate()
        
        # Store timeline in job
        job.timeline = timeline
        
        # Save generation log
        log_path = Path(f"/app/backend/logs/timeline_{job.job_id}.log")
        log_path.write_text(generator.get_generation_log())
        job.timeline_log = str(log_path)
        
        # Update progress
        job.update_progress(JobStatus.GENERATING_TIMELINE, 45.0, "Timeline generation complete")
        job.timings.generating_timeline_ms = (time.time() - stage_start) * 1000
        await self.job_service.update_job(job)
        
        logger.info(
            f"[{job.job_id}] Timeline generated: "
            f"{len(timeline.segments)} segments, "
            f"{timeline.total_duration:.2f}s, "
            f"{timeline.transition_count} transitions, "
            f"{timeline.effect_count} effects"
        )
    
    async def _stage_render(self, job: GenerationJob):
        """Stage 3: Render final video"""
        logger.info(f"[{job.job_id}] Stage 3: Rendering final video...")
        stage_start = time.time()
        
        job.update_progress(JobStatus.RENDERING, 50.0, "Rendering video")
        await self.job_service.update_job(job)
        
        if not job.timeline:
            raise ValueError("Timeline not available")
        
        if not job.input_audio or 'path' not in job.input_audio:
            raise ValueError("Audio file not available")
        
        # Initialize render service
        render_service = RenderService(job.job_id)
        
        # Render video
        export = await render_service.render(
            timeline=job.timeline,
            audio_path=job.input_audio['path'],
            resolution="1080p",
            fps=30,
            quality="balanced"
        )
        
        # Store export info in job
        job.export = export
        
        # Collect FFmpeg logs (trace IDs)
        ffmpeg_metrics = render_service.ffmpeg.get_metrics()
        job.ffmpeg_logs = [m['trace_id'] for m in ffmpeg_metrics]
        
        # Update progress
        job.update_progress(JobStatus.RENDERING, 95.0, "Rendering complete")
        job.timings.rendering_ms = (time.time() - stage_start) * 1000
        await self.job_service.update_job(job)
        
        logger.info(
            f"[{job.job_id}] Render complete: "
            f"path={export.path}, "
            f"size={export.size_bytes / (1024*1024):.2f}MB, "
            f"duration={export.duration:.2f}s"
        )
    
    def get_queue_stats(self) -> dict:
        """Get queue statistics"""
        return {
            "running": self.running,
            "queue_size": self.queue.qsize(),
            "worker_active": self.worker_task is not None and not self.worker_task.done()
        }
