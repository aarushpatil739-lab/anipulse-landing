"""
Generation Job Model

Represents an AMV generation job with state tracking, progress, and output information.
"""

from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field
import uuid


class JobStatus(str, Enum):
    """Job processing status"""
    QUEUED = "queued"
    ANALYZING_AUDIO = "analyzing_audio"
    GENERATING_TIMELINE = "generating_timeline"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


class AudioAnalysisResult(BaseModel):
    """Stored audio analysis results"""
    bpm: float
    beats: List[float]
    drops: List[float]
    energy_curve: List[Dict[str, float]]
    sections: List[Dict[str, Any]]
    beat_intervals: List[Dict[str, float]]
    duration: float


class TimelineSegment(BaseModel):
    """Single segment in the edit timeline"""
    clip_path: str
    clip_index: int  # Index in original clips list
    start_time: float  # Start time in source clip
    end_time: float  # End time in source clip
    timeline_start: float  # Start time in final output
    timeline_end: float  # End time in final output
    transition: Optional[str] = None  # fade, flash, zoom, none
    effect: Optional[str] = None  # zoom, shake, speed_ramp, none
    energy_level: str  # low, medium, high
    beat_aligned: bool = True


class GeneratedTimeline(BaseModel):
    """Complete generated edit timeline"""
    segments: List[TimelineSegment]
    total_duration: float
    transition_count: int
    effect_count: int
    avg_cut_duration: float
    style: str = "amv_default"


class ExportResult(BaseModel):
    """Final export information"""
    path: str
    size_bytes: int
    duration: float
    resolution: str
    fps: int
    codec_video: str
    codec_audio: str


class TimingMetrics(BaseModel):
    """Performance timing for each stage"""
    analyzing_audio_ms: float = 0.0
    generating_timeline_ms: float = 0.0
    rendering_ms: float = 0.0
    total_ms: float = 0.0


class GenerationJob(BaseModel):
    """
    Generation Job Model
    
    Tracks the complete lifecycle of an AMV generation job from queued to completed/failed.
    """
    # Core identification
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(..., description="Upload session ID")
    
    # Status tracking
    status: JobStatus = JobStatus.QUEUED
    progress_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    current_stage: str = "Queued"
    
    # Input metadata
    input_clips: List[Dict[str, Any]] = Field(default_factory=list)  # {path, duration, resolution}
    input_audio: Optional[Dict[str, Any]] = None  # {path, duration}
    style: str = "amv_default"
    
    # Processing results
    audio_analysis: Optional[AudioAnalysisResult] = None
    timeline: Optional[GeneratedTimeline] = None
    export: Optional[ExportResult] = None
    
    # Performance metrics
    timings: TimingMetrics = Field(default_factory=TimingMetrics)
    
    # Logging and debugging
    ffmpeg_logs: List[str] = Field(default_factory=list)  # Trace IDs
    timeline_log: Optional[str] = None  # Path to detailed timeline generation log
    
    # Error handling
    error_message: Optional[str] = None
    error_trace_id: Optional[str] = None
    error_stage: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def update_progress(self, status: JobStatus, progress: float, stage: str):
        """Update job status and progress"""
        self.status = status
        self.progress_pct = progress
        self.current_stage = stage
        self.updated_at = datetime.now(timezone.utc)
        
        if status == JobStatus.ANALYZING_AUDIO and not self.started_at:
            self.started_at = datetime.now(timezone.utc)
        
        if status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            self.completed_at = datetime.now(timezone.utc)
    
    def mark_failed(self, error: str, trace_id: Optional[str] = None, stage: Optional[str] = None):
        """Mark job as failed with error details"""
        self.status = JobStatus.FAILED
        self.progress_pct = 0.0
        self.error_message = error
        self.error_trace_id = trace_id
        self.error_stage = stage or self.current_stage
        self.completed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for MongoDB storage"""
        data = self.model_dump()
        # Convert datetime objects to ISO strings for MongoDB
        for key in ['created_at', 'updated_at', 'started_at', 'completed_at']:
            if data.get(key):
                data[key] = data[key].isoformat() if isinstance(data[key], datetime) else data[key]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'GenerationJob':
        """Create from MongoDB dictionary"""
        # Convert ISO strings back to datetime objects
        for key in ['created_at', 'updated_at', 'started_at', 'completed_at']:
            if data.get(key) and isinstance(data.get(key), str):
                try:
                    data[key] = datetime.fromisoformat(data[key])
                except:
                    pass
        return cls(**data)
    
    def get_public_status(self) -> Dict:
        """Get public-facing status information"""
        return {
            "job_id": self.job_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "progress_pct": self.progress_pct,
            "current_stage": self.current_stage,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "has_timeline": self.timeline is not None,
            "has_export": self.export is not None
        }


class GenerationJobService:
    """Service for managing generation jobs in MongoDB"""
    
    def __init__(self, db):
        self.db = db
        self.collection = db.generation_jobs
    
    async def create_job(self, session_id: str, clips: List[Dict], audio: Dict, style: str = "amv_default") -> GenerationJob:
        """Create a new generation job"""
        job = GenerationJob(
            session_id=session_id,
            input_clips=clips,
            input_audio=audio,
            style=style
        )
        
        # Store in MongoDB
        await self.collection.insert_one(job.to_dict())
        
        return job
    
    async def get_job(self, job_id: str) -> Optional[GenerationJob]:
        """Get job by ID"""
        doc = await self.collection.find_one({"job_id": job_id}, {"_id": 0})
        if doc:
            return GenerationJob.from_dict(doc)
        return None
    
    async def update_job(self, job: GenerationJob):
        """Update existing job"""
        job.updated_at = datetime.now(timezone.utc)
        await self.collection.update_one(
            {"job_id": job.job_id},
            {"$set": job.to_dict()}
        )
    
    async def delete_job(self, job_id: str) -> bool:
        """Delete a job"""
        result = await self.collection.delete_one({"job_id": job_id})
        return result.deleted_count > 0
    
    async def get_jobs_by_session(self, session_id: str) -> List[GenerationJob]:
        """Get all jobs for a session"""
        docs = await self.collection.find({"session_id": session_id}, {"_id": 0}).to_list(100)
        return [GenerationJob.from_dict(doc) for doc in docs]
    
    async def get_queued_jobs(self) -> List[GenerationJob]:
        """Get all queued jobs"""
        docs = await self.collection.find({"status": JobStatus.QUEUED.value}, {"_id": 0}).to_list(100)
        return [GenerationJob.from_dict(doc) for doc in docs]
