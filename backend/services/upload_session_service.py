from typing import Optional, Dict, List
from datetime import datetime
import uuid
from models.upload_session import UploadSession, UploadedFile, SessionStatus, FileType
from services.storage_provider import get_storage_provider, StorageProvider
from services.file_validator import FileValidator
from fastapi import UploadFile
import os


class UploadSessionService:
    """Service for managing upload sessions"""
    
    def __init__(self, db, storage_provider: Optional[StorageProvider] = None):
        self.db = db
        self.storage = storage_provider or get_storage_provider("local")
        self.validator = FileValidator
    
    async def create_session(self) -> UploadSession:
        """Create a new upload session"""
        session_id = str(uuid.uuid4())
        session = UploadSession(session_id=session_id)
        
        # Save to database
        await self.db.upload_sessions.insert_one(session.to_dict())
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[UploadSession]:
        """Get an upload session by ID"""
        doc = await self.db.upload_sessions.find_one({"session_id": session_id})
        if not doc:
            return None
        return UploadSession.from_dict(doc)
    
    async def update_session(self, session: UploadSession) -> bool:
        """Update a session in the database"""
        result = await self.db.upload_sessions.update_one(
            {"session_id": session.session_id},
            {"$set": session.to_dict()}
        )
        return result.modified_count > 0
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its files"""
        # Get session
        session = await self.get_session(session_id)
        if not session:
            return False
        
        # Delete files from storage
        await self.storage.delete_session(session_id)
        
        # Delete from database
        result = await self.db.upload_sessions.delete_one({"session_id": session_id})
        return result.deleted_count > 0
    
    async def upload_video(self, session_id: str, file: UploadFile) -> Dict:
        """Upload a video file to a session
        
        Returns:
            Dict with file info or error
        """
        # Get session
        session = await self.get_session(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        # Validate file
        is_valid, error = self.validator.validate_video_file(file)
        if not is_valid:
            return {"success": False, "error": error}
        
        # Check video count
        is_valid, error = self.validator.validate_video_count(len(session.videos))
        if not is_valid:
            return {"success": False, "error": error}
        
        # Get file size
        file_size = self.validator.get_file_size(file)
        
        # Check total size
        is_valid, error = self.validator.validate_total_size(session.total_bytes, file_size)
        if not is_valid:
            return {"success": False, "error": error}
        
        # Save file
        storage_key = await self.storage.save_file(
            file.file, session_id, "videos", file.filename
        )
        
        # Create file record
        uploaded_file = UploadedFile(
            file_id=str(uuid.uuid4()),
            file_type=FileType.VIDEO,
            original_name=file.filename,
            mime_type=file.content_type,
            size_bytes=file_size,
            storage_key=storage_key
        )
        
        # Add to session
        session.add_video(uploaded_file)
        await self.update_session(session)
        
        return {
            "success": True,
            "file": uploaded_file.model_dump()
        }
    
    async def upload_audio(self, session_id: str, file: UploadFile) -> Dict:
        """Upload an audio file to a session
        
        Returns:
            Dict with file info or error
        """
        # Get session
        session = await self.get_session(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        # Validate file
        is_valid, error = self.validator.validate_audio_file(file)
        if not is_valid:
            return {"success": False, "error": error}
        
        # Get file size
        file_size = self.validator.get_file_size(file)
        
        # Check total size
        is_valid, error = self.validator.validate_total_size(session.total_bytes, file_size)
        if not is_valid:
            return {"success": False, "error": error}
        
        # Save file
        storage_key = await self.storage.save_file(
            file.file, session_id, "audio", file.filename
        )
        
        # Create file record
        uploaded_file = UploadedFile(
            file_id=str(uuid.uuid4()),
            file_type=FileType.AUDIO,
            original_name=file.filename,
            mime_type=file.content_type,
            size_bytes=file_size,
            storage_key=storage_key
        )
        
        # Set audio (replaces existing if any)
        old_audio = session.audio
        session.set_audio(uploaded_file)
        await self.update_session(session)
        
        # Delete old audio file if exists
        if old_audio:
            await self.storage.delete_file(old_audio.storage_key)
        
        return {
            "success": True,
            "file": uploaded_file.model_dump()
        }
    
    async def remove_file(self, session_id: str, file_id: str) -> Dict:
        """Remove a file from a session
        
        Returns:
            Dict with success status
        """
        # Get session
        session = await self.get_session(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        # Remove file
        removed_file = session.remove_file(file_id)
        if not removed_file:
            return {"success": False, "error": "File not found"}
        
        # Delete from storage
        await self.storage.delete_file(removed_file.storage_key)
        
        # Update session
        await self.update_session(session)
        
        return {"success": True, "file_id": file_id}
    
    async def mark_as_uploaded(self, session_id: str) -> bool:
        """Mark session as uploaded (ready to process)"""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        if not session.is_ready_to_process():
            return False
        
        session.status = SessionStatus.UPLOADED
        session.updated_at = datetime.utcnow()
        return await self.update_session(session)
    
    async def start_processing(self, session_id: str) -> Dict:
        """Start processing a session (placeholder for future AI)
        
        Returns:
            Dict with status
        """
        session = await self.get_session(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        if not session.is_ready_to_process():
            return {
                "success": False,
                "error": "Session not ready. Need at least 1 video and 1 audio file."
            }
        
        # Update status
        session.status = SessionStatus.PROCESSING
        session.processing_started_at = datetime.utcnow()
        await self.update_session(session)
        
        # TODO: Trigger AI processing pipeline
        # For now, return a placeholder response
        return {
            "success": True,
            "message": "Processing started! AI editing will be implemented in the next phase.",
            "session_id": session_id,
            "status": "processing"
        }
