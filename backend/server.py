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

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

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
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

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

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()