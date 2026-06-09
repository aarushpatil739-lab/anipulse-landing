from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import sys
import json
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
from fastapi import UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from services.upload_session_service import UploadSessionService
from models.upload_session import UploadSession



ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Environment configuration
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'anipulse')
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
PORT = int(os.environ.get('PORT', 8000))

# MongoDB connection
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Create the main app without a prefix
app = FastAPI(
    title="AniPulse API",
    description="AI-powered anime video editing API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

# Add your routes to the router instead of directly to app

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj



# ========== UPLOAD ENDPOINTS ==========

# Initialize upload service
upload_service = UploadSessionService(db)

@api_router.post("/upload/sessions")
async def create_upload_session():
    """Create a new upload session"""
    try:
        session = await upload_service.create_session()
        return {
            "success": True,
            "session": {
                "session_id": session.session_id,
                "status": session.status.value,
                "created_at": session.created_at.isoformat(),
                "videos": [],
                "audio": None,
                "total_bytes": 0
            }
        }
    except Exception as e:
        logging.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/upload/sessions/{session_id}")
async def get_upload_session(session_id: str):
    """Get upload session details"""
    session = await upload_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "success": True,
        "session": {
            "session_id": session.session_id,
            "status": session.status.value,
            "videos": [v.model_dump() for v in session.videos],
            "audio": session.audio.model_dump() if session.audio else None,
            "total_bytes": session.total_bytes,
            "is_ready": session.is_ready_to_process(),
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat()
        }
    }

@api_router.post("/upload/sessions/{session_id}/videos")
async def upload_video(session_id: str, file: UploadFile = File(...)):
    """Upload a video file to a session"""
    try:
        result = await upload_service.upload_video(session_id, file)
        
        if not result.get("success"):
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": result.get("error")}
            )
        
        return {
            "success": True,
            "file": result["file"]
        }
    except Exception as e:
        logging.error(f"Error uploading video: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/upload/sessions/{session_id}/audio")
async def upload_audio(session_id: str, file: UploadFile = File(...)):
    """Upload an audio file to a session"""
    try:
        result = await upload_service.upload_audio(session_id, file)
        
        if not result.get("success"):
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": result.get("error")}
            )
        
        return {
            "success": True,
            "file": result["file"]
        }
    except Exception as e:
        logging.error(f"Error uploading audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/upload/sessions/{session_id}/files/{file_id}")
async def remove_file(session_id: str, file_id: str):
    """Remove a file from a session"""
    try:
        result = await upload_service.remove_file(session_id, file_id)
        
        if not result.get("success"):
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": result.get("error")}
            )
        
        return {"success": True, "file_id": file_id}
    except Exception as e:
        logging.error(f"Error removing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/upload/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete an entire upload session"""
    try:
        success = await upload_service.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"success": True, "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/upload/sessions/{session_id}/process")
async def process_session(session_id: str):
    """Start processing a session (placeholder for AI editing)"""
    try:
        result = await upload_service.start_processing(session_id)
        
        if not result.get("success"):
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": result.get("error")}
            )
        
        return result
    except Exception as e:
        logging.error(f"Error processing session: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# ========== GENERATION ENDPOINTS ==========

from models.generation_job import GenerationJobService, GenerationJob, JobStatus
from services.processing_queue import ProcessingQueue
from fastapi.responses import FileResponse

# Initialize generation services
generation_job_service = GenerationJobService(db)
processing_queue: Optional[ProcessingQueue] = None

class GenerateRequest(BaseModel):
    """Request to generate AMV"""
    session_id: str = Field(..., description="Upload session ID")
    style: str = Field("amv_default", description="Generation style")
    max_duration: float = Field(180.0, description="Maximum output duration in seconds")
    aspect_ratio: str = Field(
        "16:9",
        description="Output aspect ratio. One of: 16:9, 9:16, 1:1",
    )
    vertical_mode: str = Field(
        "blurred",
        description=(
            "How to fit a 16:9 source into 9:16 (or 1:1). "
            "'blurred' (TikTok-style blurred background, recommended) or "
            "'crop' (center-crop, may cut content). "
            "Ignored when aspect_ratio is 16:9."
        ),
    )

@api_router.post("/generate")
async def generate_amv(request: GenerateRequest):
    """
    Start AMV generation for an upload session
    
    Returns job_id for tracking progress
    """
    try:
        # Pre-flight: confirm the rendering toolchain is installed in this
        # runtime. If not, return HTTP 503 immediately with a clear, machine
        # readable error so the frontend can show a banner instead of having
        # the job silently fail seconds later.
        if not ffmpeg_is_available():
            status = ffmpeg_status_dict()
            logger.error(f"/api/generate rejected: ffmpeg toolchain missing -> {status['missing']}")
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "ffmpeg_unavailable",
                    "message": (
                        "Rendering backend is not configured: "
                        f"missing system binaries {status['missing']}. "
                        "Please contact support / redeploy the backend image."
                    ),
                    "missing": status["missing"],
                    "ffmpeg": status["ffmpeg"],
                    "ffprobe": status["ffprobe"],
                },
            )

        # Validate session exists and is ready
        session = await upload_service.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if not session.is_ready_to_process():
            raise HTTPException(
                status_code=400,
                detail="Session not ready: need at least 1 video and 1 audio file"
            )
        
        # Prepare clip metadata
        clips_metadata = []
        for video in session.videos:
            # Convert relative storage_key to absolute path
            video_path = f"/app/backend/uploads/{video.storage_key}"
            clips_metadata.append({
                "path": video_path,
                "duration": 10.0,  # Default duration (will be probed by FFmpeg)
                "width": 1920,
                "height": 1080,
                "fps": 30.0,
                "bitrate": 500000,
                "has_audio": True
            })
        
        # Prepare audio metadata
        audio_path = f"/app/backend/uploads/{session.audio.storage_key}"
        audio_metadata = {
            "path": audio_path,
            "duration": 180.0  # Default duration (will be determined by audio analyzer)
        }
        
        # Create generation job
        job = await generation_job_service.create_job(
            session_id=request.session_id,
            clips=clips_metadata,
            audio=audio_metadata,
            style=request.style
        )

        # Stash render-format options on the job so the worker can read
        # them.  These persist via MongoDB alongside the rest of the job.
        job.input_audio = job.input_audio or {}
        job.input_audio["__render_opts"] = {
            "aspect_ratio": request.aspect_ratio,
            "vertical_mode": request.vertical_mode,
            "max_duration": request.max_duration,
        }
        await generation_job_service.update_job(job)
        
        # Enqueue job
        if processing_queue:
            await processing_queue.enqueue_job(job)
        else:
            raise HTTPException(status_code=503, detail="Processing queue not available")
        
        logger.info(f"Generation job {job.job_id} created and enqueued for session {request.session_id}")
        
        return {
            "success": True,
            "job_id": job.job_id,
            "status": job.status.value,
            "message": "Generation started"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

def _friendly_error_message(raw: Optional[str]) -> Optional[str]:
    """Map noisy FFmpeg / pipeline error strings to user-friendly text.

    Keep the raw text accessible to operators via logs and `raw_error`,
    but never let an end-user see 'rc=-9' or a 200-line stderr blob.
    """
    if not raw:
        return None
    low = raw.lower()
    if "rc=-9" in low or "sigkill" in low or "out of memory" in low:
        return (
            "Render complexity exceeded the available memory. AniPulse "
            "is retrying in lightweight mode -- give it another go."
        )
    if "no available clips" in low or "all clips shorter" in low:
        return (
            "Not enough footage for the requested edit length. Try a "
            "shorter track or upload a few more clips."
        )
    if "timeout" in low:
        return (
            "A render step took longer than expected. AniPulse aborted "
            "it safely -- please try again."
        )
    if "ffmpeg" in low or "rc=" in low:
        return "An internal render step failed. AniPulse is logging the issue and you can safely retry."
    return raw  # already friendly enough


@api_router.get("/generate/{job_id}/status")
async def get_generation_status(job_id: str):
    """
    Get generation job status and progress
    """
    try:
        job = await generation_job_service.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        payload = job.get_public_status()

        # Surface user-friendly error in addition to raw_error so the
        # frontend can show a calm message.
        raw_err = payload.get("error_message")
        if raw_err:
            payload["raw_error"] = raw_err
            payload["error_message"] = _friendly_error_message(raw_err) or raw_err

        # Surface footage + safe-mode diagnostics from the timeline if available.
        if job.timeline:
            payload["safe_mode"] = bool(getattr(job.timeline, "safe_mode", False))
            payload["safe_mode_reason"] = getattr(job.timeline, "safe_mode_reason", None)
            payload["footage_limited"] = bool(getattr(job.timeline, "footage_limited", False))
            payload["footage_warning"] = getattr(job.timeline, "footage_warning", None)
            payload["segment_count"] = len(job.timeline.segments or [])
            payload["timeline_duration"] = float(getattr(job.timeline, "total_duration", 0.0))

        return {
            "success": True,
            **payload,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/generate/{job_id}/timeline")
async def get_generation_timeline(job_id: str):
    """
    Get generated timeline JSON
    """
    try:
        job = await generation_job_service.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if not job.timeline:
            raise HTTPException(status_code=404, detail="Timeline not yet generated")
        
        return {
            "success": True,
            "job_id": job.job_id,
            "timeline": job.timeline.model_dump()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/generate/{job_id}/download")
async def download_generated_video(job_id: str):
    """
    Download generated AMV video
    """
    try:
        job = await generation_job_service.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status != JobStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Job not completed yet (status: {job.status.value})"
            )
        
        if not job.export or not job.export.path:
            raise HTTPException(status_code=404, detail="Export file not found")
        
        export_path = Path(job.export.path)
        if not export_path.exists():
            raise HTTPException(status_code=404, detail="Export file does not exist")
        
        return FileResponse(
            path=str(export_path),
            media_type="video/mp4",
            filename=f"anipulse_{job_id}.mp4"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/generate/queue/stats")
async def get_queue_stats():
    """Get processing queue statistics"""
    try:
        if processing_queue:
            stats = processing_queue.get_queue_stats()
            return {
                "success": True,
                **stats
            }
        else:
            return {
                "success": False,
                "error": "Processing queue not initialized"
            }
    except Exception as e:
        logger.error(f"Error getting queue stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# ========== AUDIO & VIDEO ANALYSIS ENDPOINTS ==========

from services.audio_analyzer import AudioAnalyzer
from services.scene_analyzer import SceneAnalyzer, is_available as scene_pyav_available

# Reusable analyzer instances (cheap to construct, no shared state issues)
_audio_analyzer = AudioAnalyzer()
_scene_analyzer = SceneAnalyzer(analysis_fps=6)


class AudioBeatsRequest(BaseModel):
    """Run beat / BPM / drop analysis on an already-uploaded audio file."""

    session_id: Optional[str] = Field(
        None,
        description="Upload session ID. Resolves the session's audio file.",
    )
    audio_path: Optional[str] = Field(
        None,
        description=(
            "Direct path to an audio file already on the backend filesystem "
            "(advanced: for internal debugging only)."
        ),
    )


def _audio_summary(analysis: Dict, beat_count_in_payload: int = 256) -> Dict:
    """Trim the full analysis result down to a frontend-friendly payload.

    The raw `energy_curve` can be thousands of points -- we down-sample
    to keep the response under ~50 KB so it's snappy in the UI.
    """
    beats: List[float] = analysis.get("beats", []) or []
    drops: List[float] = analysis.get("drops", []) or []
    sections = analysis.get("sections", []) or []
    energy_curve = analysis.get("energy_curve", []) or []

    # Down-sample energy curve to at most ~600 points for the timeline UI.
    if len(energy_curve) > 600:
        step = max(1, len(energy_curve) // 600)
        energy_curve = energy_curve[::step]

    bpm = float(analysis.get("bpm", 0.0))
    duration = float(analysis.get("duration", 0.0))

    # Build a uniform "beat grid" so the frontend can render bar lines
    # even on tracks where librosa's onset detection drops beats around
    # silence.  Grid spans 0..duration at the detected BPM.
    beat_period = 60.0 / bpm if bpm > 1 else 0.5
    grid: List[float] = []
    t = beats[0] if beats else 0.0
    while t <= duration and len(grid) < 8192:
        grid.append(round(t, 4))
        t += beat_period

    return {
        "bpm": bpm,
        "duration_seconds": duration,
        "beat_count": len(beats),
        "drop_count": len(drops),
        "beats": [round(b, 4) for b in beats[:beat_count_in_payload]],
        "drops": [round(d, 4) for d in drops],
        "beat_grid": grid,
        "energy_curve": energy_curve,
        "sections": sections,
        "beat_period_seconds": beat_period,
    }


@api_router.post("/audio/beats")
async def detect_audio_beats(req: AudioBeatsRequest):
    """
    Beat / BPM / drop detection for an uploaded audio track.

    Returns BPM, raw beat timestamps, a uniform beat-grid (useful for
    rendering bar lines in a timeline UI), drop timestamps, the energy
    curve and detected high/low energy sections.
    """
    if not req.session_id and not req.audio_path:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'session_id' or 'audio_path'.",
        )

    audio_path: Optional[str] = req.audio_path
    if req.session_id:
        sess = await upload_service.get_session(req.session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")
        if not sess.audio:
            raise HTTPException(
                status_code=400,
                detail="Session has no audio file uploaded yet.",
            )
        audio_path = f"/app/backend/uploads/{sess.audio.storage_key}"

    if not audio_path or not Path(audio_path).exists():
        raise HTTPException(status_code=404, detail=f"Audio file not found: {audio_path}")

    try:
        analysis = await _audio_analyzer.analyze(audio_path)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Beat detection failed")
        raise HTTPException(status_code=500, detail=f"Beat detection failed: {exc}")

    return {
        "success": True,
        "audio_path": audio_path,
        **_audio_summary(analysis),
    }


class VideoAnalyzeRequest(BaseModel):
    """Run scene / motion / intensity analysis on uploaded video clips."""

    session_id: Optional[str] = Field(
        None,
        description="Upload session ID. Analyzes all video clips in the session.",
    )
    video_paths: Optional[List[str]] = Field(
        None,
        description="Direct list of video file paths to analyze (advanced).",
    )


@api_router.post("/video/analyze")
async def analyze_video_clips(req: VideoAnalyzeRequest):
    """
    Scene / motion / intensity analysis for each uploaded video clip.

    Returns per-clip motion_score, intensity_score, score_1_to_10,
    scene-cut timestamps and action/calm sub-segments.  Used by the
    smart clip selector during generation, and exposed here so the
    frontend can show "intensity bars" beneath each clip thumbnail.
    """
    if not scene_pyav_available():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "pyav_unavailable",
                "message": (
                    "PyAV is not installed in this runtime; scene analysis is "
                    "unavailable. Add 'av' to backend/requirements.txt."
                ),
            },
        )

    paths: List[str] = []
    if req.video_paths:
        paths.extend(req.video_paths)
    if req.session_id:
        sess = await upload_service.get_session(req.session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")
        for v in sess.videos:
            paths.append(f"/app/backend/uploads/{v.storage_key}")

    if not paths:
        raise HTTPException(
            status_code=400,
            detail="Provide 'session_id' (recommended) or 'video_paths'.",
        )

    results = _scene_analyzer.analyze_many(paths)
    return {
        "success": True,
        "clip_count": len(results),
        "clips": [r.to_dict() for r in results],
    }


# ========== FFMPEG TEST ENDPOINTS ==========

from services.ffmpeg_utils import FFmpegUtils, FFmpegError
from services.ffmpeg_availability import (
    FFmpegBinaryMissingError,
    ensure_available as ensure_ffmpeg_available,
    is_available as ffmpeg_is_available,
    status_dict as ffmpeg_status_dict,
)
from fastapi import BackgroundTasks
import tempfile
import shutil
import subprocess

# Initialize FFmpeg utilities
ffmpeg_utils = FFmpegUtils()

class FFmpegTestRequest(BaseModel):
    """Base model for FFmpeg test requests"""
    session_id: Optional[str] = None
    
class TrimRequest(FFmpegTestRequest):
    """Request model for trim test"""
    video_index: int = 0  # Which video from the session to use
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")

class ConcatenateRequest(FFmpegTestRequest):
    """Request model for concatenate test"""
    video_indices: List[int] = Field(..., description="Indices of videos to concatenate")

class TransitionRequest(FFmpegTestRequest):
    """Request model for transition test"""
    video1_index: int = 0
    video2_index: int = 1
    transition_type: str = Field("fade", description="fade, flash, or zoom")
    duration: float = Field(0.5, description="Transition duration in seconds")

async def generate_test_video(name: str = "test", duration: float = 3.0, 
                              color: str = "blue") -> str:
    """Generate a synthetic test video for testing"""
    # Refuse early if the toolchain is missing in this runtime.
    if not ffmpeg_is_available():
        status = ffmpeg_status_dict()
        raise HTTPException(
            status_code=503,
            detail={
                "error": "ffmpeg_unavailable",
                "message": (
                    "Cannot generate test video: ffmpeg toolchain missing "
                    f"({status['missing']})."
                ),
                "missing": status["missing"],
            },
        )

    output_path = f"/app/backend/temp/{name}_{uuid.uuid4().hex}.mp4"
    
    cmd = [
        'ffmpeg',
        '-f', 'lavfi',
        '-i', f'color=c={color}:s=1280x720:d={duration}:r=30',
        '-f', 'lavfi',
        '-i', f'sine=frequency=440:duration={duration}',
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-crf', '23',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-y',
        output_path
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    await process.communicate()
    
    if process.returncode != 0:
        raise HTTPException(status_code=500, detail="Failed to generate test video")
    
    return output_path

@api_router.get("/health/ffmpeg")
async def health_ffmpeg():
    """
    Diagnostic endpoint that reports whether ffmpeg/ffprobe are installed
    in the runtime image. Used as the Railway healthcheck target.

    Always returns HTTP 200 (so Railway does not endlessly restart on a
    missing binary) but flags `available=false` in the body when broken.
    The /api/generate endpoint refuses to start jobs when this is false.
    """
    status = ffmpeg_status_dict()

    deps_file = Path("/app/backend/logs/deps_status.json")
    deps_snapshot = None
    if deps_file.exists():
        try:
            deps_snapshot = json.loads(deps_file.read_text())
        except Exception as exc:  # noqa: BLE001
            deps_snapshot = {"error": f"could not parse deps_status.json: {exc}"}

    return {
        "service": "anipulse-backend",
        "available": status["available"],
        "missing": status["missing"],
        "ffmpeg": status["ffmpeg"],
        "ffprobe": status["ffprobe"],
        "startup_check": deps_snapshot,
    }


@api_router.post("/test/ffmpeg/probe")
async def test_probe(request: FFmpegTestRequest):
    """Test FFmpeg probe functionality"""
    try:
        # Generate a test video
        test_video = await generate_test_video("probe_test", duration=2.0, color="blue")
        
        # Probe it
        metadata = await ffmpeg_utils.probe(test_video)
        
        # Validate output
        integrity = await ffmpeg_utils.validate_output(test_video, require_video=True)
        
        # Get metrics
        metrics = ffmpeg_utils.get_last_metric()
        
        # Cleanup
        Path(test_video).unlink(missing_ok=True)
        
        return {
            "success": True,
            "operation": "probe",
            "metadata": metadata,
            "integrity": {
                "valid": integrity.valid,
                "has_video": integrity.has_video_stream,
                "has_audio": integrity.has_audio_stream,
                "duration": integrity.duration,
                "file_size_bytes": integrity.file_size_bytes
            },
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"Probe test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/test/ffmpeg/trim")
async def test_trim(request: TrimRequest):
    """Test FFmpeg trim functionality"""
    try:
        # Generate a test video
        test_video = await generate_test_video("trim_test", duration=5.0, color="green")
        
        # Trim it
        output = await ffmpeg_utils.trim(test_video, request.start, request.end)
        
        # Validate output
        integrity = await ffmpeg_utils.validate_output(output, require_video=True, min_duration=0.5)
        
        # Get metrics
        metrics = ffmpeg_utils.get_last_metric()
        
        # Cleanup
        Path(test_video).unlink(missing_ok=True)
        Path(output).unlink(missing_ok=True)
        
        return {
            "success": True,
            "operation": "trim",
            "input_duration": 5.0,
            "trim_start": request.start,
            "trim_end": request.end,
            "expected_duration": request.end - request.start,
            "actual_duration": integrity.duration,
            "integrity": {
                "valid": integrity.valid,
                "errors": integrity.errors
            },
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"Trim test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/test/ffmpeg/concatenate")
async def test_concatenate():
    """Test FFmpeg concatenate functionality"""
    try:
        # Generate multiple test videos
        video1 = await generate_test_video("concat1", duration=2.0, color="red")
        video2 = await generate_test_video("concat2", duration=2.5, color="blue")
        video3 = await generate_test_video("concat3", duration=1.5, color="green")
        
        videos = [video1, video2, video3]
        expected_duration = 2.0 + 2.5 + 1.5
        
        # Concatenate them
        output = await ffmpeg_utils.concatenate(videos)
        
        # Validate output
        integrity = await ffmpeg_utils.validate_output(output, require_video=True, min_duration=5.0)
        
        # Get metrics
        metrics = ffmpeg_utils.get_last_metric()
        
        # Cleanup
        for v in videos:
            Path(v).unlink(missing_ok=True)
        Path(output).unlink(missing_ok=True)
        
        return {
            "success": True,
            "operation": "concatenate",
            "input_count": len(videos),
            "expected_duration": expected_duration,
            "actual_duration": integrity.duration,
            "integrity": {
                "valid": integrity.valid,
                "errors": integrity.errors
            },
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"Concatenate test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/test/ffmpeg/transition")
async def test_transition(request: TransitionRequest):
    """Test FFmpeg transition functionality"""
    try:
        # Generate two test videos
        video1 = await generate_test_video("trans1", duration=3.0, color="purple")
        video2 = await generate_test_video("trans2", duration=3.0, color="orange")
        
        # Apply transition
        output = await ffmpeg_utils.apply_transition(
            video1,
            video2,
            request.transition_type,
            request.duration
        )
        
        # Validate output
        integrity = await ffmpeg_utils.validate_output(output, require_video=True, min_duration=4.0)
        
        # Get metrics
        metrics = ffmpeg_utils.get_last_metric()
        
        # Cleanup
        Path(video1).unlink(missing_ok=True)
        Path(video2).unlink(missing_ok=True)
        Path(output).unlink(missing_ok=True)
        
        return {
            "success": True,
            "operation": f"transition_{request.transition_type}",
            "transition_type": request.transition_type,
            "transition_duration": request.duration,
            "output_duration": integrity.duration,
            "integrity": {
                "valid": integrity.valid,
                "errors": integrity.errors
            },
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"Transition test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/test/ffmpeg/metrics")
async def get_ffmpeg_metrics():
    """Get all recorded FFmpeg performance metrics"""
    try:
        metrics = ffmpeg_utils.get_metrics()
        
        # Calculate summary statistics
        if metrics:
            total_ops = len(metrics)
            successful = sum(1 for m in metrics if m['success'])
            failed = total_ops - successful
            avg_time = sum(m['elapsed_ms'] for m in metrics) / total_ops if total_ops > 0 else 0
            
            summary = {
                "total_operations": total_ops,
                "successful": successful,
                "failed": failed,
                "success_rate": (successful / total_ops * 100) if total_ops > 0 else 0,
                "avg_elapsed_ms": avg_time
            }
        else:
            summary = {
                "total_operations": 0,
                "successful": 0,
                "failed": 0,
                "success_rate": 0,
                "avg_elapsed_ms": 0
            }
        
        return {
            "success": True,
            "summary": summary,
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

import asyncio


@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks


# Configure CORS with environment-based origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include the API router
app.include_router(api_router)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Lightweight health check endpoint used by Railway.

    Returns HTTP 200 as soon as the FastAPI process is up, even if the
    background queue or MongoDB ping is still warming up. This prevents
    healthcheck timeouts on cold start when librosa/scipy/numba imports
    eat 30-60s of CPU time.
    """
    # MongoDB ping is best-effort and bounded so a slow/down Mongo never
    # turns the healthcheck red.
    db_state = "unknown"
    try:
        await asyncio.wait_for(db.command("ping"), timeout=2.0)
        db_state = "connected"
    except asyncio.TimeoutError:
        db_state = "timeout"
    except Exception as exc:  # noqa: BLE001
        db_state = f"error: {exc}"

    return {
        "status": "healthy",
        "service": "anipulse-backend",
        "version": "1.0.0",
        "database": db_state,
        "ffmpeg_available": ffmpeg_is_available(),
        "ffmpeg_missing": ffmpeg_status_dict()["missing"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    global processing_queue
    
    logger.info("=" * 60)
    logger.info("AniPulse Backend API - starting up")
    logger.info("=" * 60)
    logger.info(f"Python:      {sys.version.split()[0]}")
    logger.info(f"Working dir: {os.getcwd()}")
    logger.info(f"MongoDB URL: {MONGO_URL}")
    logger.info(f"Database:    {DB_NAME}")
    logger.info(f"CORS origins:{CORS_ORIGINS}")
    logger.info(f"PORT env:    {os.environ.get('PORT', '(not set)')}, bind PORT={PORT}")
    logger.info(f"FFmpeg available: {ffmpeg_is_available()} | status={ffmpeg_status_dict()['missing']}")

    # Test MongoDB connection (best-effort, bounded so it never blocks startup)
    try:
        await asyncio.wait_for(db.command("ping"), timeout=5.0)
        logger.info("MongoDB connection: OK")
    except asyncio.TimeoutError:
        logger.error("MongoDB ping timed out after 5s - continuing startup anyway")
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e} - continuing startup anyway")

    # Initialize and start processing queue (best-effort)
    try:
        processing_queue = ProcessingQueue(db)
        await processing_queue.start()
        logger.info("Processing queue: started")
    except Exception as e:
        logger.error(f"Failed to start processing queue: {e}")

    logger.info("=" * 60)
    logger.info("AniPulse Backend API - startup complete; ready to serve")
    logger.info("=" * 60)

@app.on_event("shutdown")
async def shutdown_db_client():
    """Shutdown event handler"""
    global processing_queue
    
    logger.info("Shutting down AniPulse Backend API")
    
    # Stop processing queue
    if processing_queue:
        try:
            await processing_queue.stop()
            logger.info("Processing queue stopped")
        except Exception as e:
            logger.error(f"Error stopping processing queue: {e}")
    
    client.close()

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AniPulse Backend API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=PORT,
        reload=False,  # Set to False in production
        log_level="info"
    )