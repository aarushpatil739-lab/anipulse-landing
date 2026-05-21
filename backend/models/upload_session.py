from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from enum import Enum


class SessionStatus(str, Enum):
    """Upload session status"""
    DRAFT = "draft"  # Session created, files being uploaded
    UPLOADED = "uploaded"  # All files uploaded successfully
    PROCESSING = "processing"  # AI processing in progress
    COMPLETED = "completed"  # Processing complete
    FAILED = "failed"  # Processing failed


class FileType(str, Enum):
    """Uploaded file types"""
    VIDEO = "video"
    AUDIO = "audio"


class UploadedFile(BaseModel):
    """Model for an uploaded file"""
    file_id: str
    file_type: FileType
    original_name: str
    mime_type: str
    size_bytes: int
    storage_key: str  # Path or S3 key
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    thumbnail_url: Optional[str] = None  # For video thumbnails (future)


class UploadSession(BaseModel):
    """Model for an upload session"""
    session_id: str
    status: SessionStatus = SessionStatus.DRAFT
    videos: List[UploadedFile] = []
    audio: Optional[UploadedFile] = None
    total_bytes: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Future fields for AI processing
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    output_video_url: Optional[str] = None
    error_message: Optional[str] = None

    def add_video(self, file: UploadedFile):
        """Add a video file to the session"""
        self.videos.append(file)
        self.total_bytes += file.size_bytes
        self.updated_at = datetime.utcnow()

    def set_audio(self, file: UploadedFile):
        """Set the audio file for the session"""
        if self.audio:
            # Remove old audio size from total
            self.total_bytes -= self.audio.size_bytes
        self.audio = file
        self.total_bytes += file.size_bytes
        self.updated_at = datetime.utcnow()

    def remove_file(self, file_id: str) -> Optional[UploadedFile]:
        """Remove a file from the session"""
        # Check if it's a video
        for i, video in enumerate(self.videos):
            if video.file_id == file_id:
                removed = self.videos.pop(i)
                self.total_bytes -= removed.size_bytes
                self.updated_at = datetime.utcnow()
                return removed
        
        # Check if it's audio
        if self.audio and self.audio.file_id == file_id:
            removed = self.audio
            self.audio = None
            self.total_bytes -= removed.size_bytes
            self.updated_at = datetime.utcnow()
            return removed
        
        return None

    def is_ready_to_process(self) -> bool:
        """Check if session is ready for processing"""
        return len(self.videos) >= 1 and self.audio is not None

    def to_dict(self) -> Dict:
        """Convert to dictionary for MongoDB storage"""
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "videos": [v.model_dump() for v in self.videos],
            "audio": self.audio.model_dump() if self.audio else None,
            "total_bytes": self.total_bytes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "processing_started_at": self.processing_started_at,
            "processing_completed_at": self.processing_completed_at,
            "output_video_url": self.output_video_url,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'UploadSession':
        """Create from dictionary (MongoDB)"""
        videos = [UploadedFile(**v) for v in data.get("videos", [])]
        audio = UploadedFile(**data["audio"]) if data.get("audio") else None
        
        return cls(
            session_id=data["session_id"],
            status=SessionStatus(data.get("status", SessionStatus.DRAFT)),
            videos=videos,
            audio=audio,
            total_bytes=data.get("total_bytes", 0),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            processing_started_at=data.get("processing_started_at"),
            processing_completed_at=data.get("processing_completed_at"),
            output_video_url=data.get("output_video_url"),
            error_message=data.get("error_message"),
        )
