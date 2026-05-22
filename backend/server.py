from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List
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



# ========== FFMPEG TEST ENDPOINTS ==========

from services.ffmpeg_utils import FFmpegUtils, FFmpegError
from fastapi import BackgroundTasks
from typing import Optional, Dict, Any
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
    """Health check endpoint for Railway"""
    try:
        # Test MongoDB connection
        await db.command("ping")
        return {
            "status": "healthy",
            "database": "connected",
            "service": "anipulse-backend"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }

@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info("Starting AniPulse Backend API")
    logger.info(f"MongoDB: {MONGO_URL}")
    logger.info(f"Database: {DB_NAME}")
    logger.info(f"CORS Origins: {CORS_ORIGINS}")
    logger.info(f"Port: {PORT}")
    
    # Test MongoDB connection
    try:
        await db.command("ping")
        logger.info("MongoDB connection successful")
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    """Shutdown event handler"""
    logger.info("Shutting down AniPulse Backend API")
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