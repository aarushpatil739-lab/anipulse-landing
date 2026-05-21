from typing import Tuple, Optional
from fastapi import UploadFile
import mimetypes


class FileValidationError(Exception):
    """Custom exception for file validation errors"""
    pass


class FileValidator:
    """Service for validating uploaded files"""
    
    # File size limits (in bytes)
    MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500MB
    MAX_AUDIO_SIZE = 50 * 1024 * 1024   # 50MB
    MAX_TOTAL_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
    
    # Upload limits
    MIN_VIDEOS = 1
    MAX_VIDEOS = 20
    
    # Allowed file types
    ALLOWED_VIDEO_TYPES = {
        "video/mp4": [".mp4"],
        "video/quicktime": [".mov"],
        "video/webm": [".webm"],
    }
    
    ALLOWED_AUDIO_TYPES = {
        "audio/mpeg": [".mp3"],
        "audio/wav": [".wav"],
        "audio/x-wav": [".wav"],
    }
    
    @classmethod
    def validate_video_file(cls, file: UploadFile) -> Tuple[bool, Optional[str]]:
        """Validate a video file
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file size
        if hasattr(file, 'size') and file.size:
            if file.size > cls.MAX_VIDEO_SIZE:
                size_mb = cls.MAX_VIDEO_SIZE / (1024 * 1024)
                return False, f"Video file exceeds maximum size of {size_mb}MB"
        
        # Check content type
        content_type = file.content_type
        if content_type not in cls.ALLOWED_VIDEO_TYPES:
            allowed = ", ".join(cls.ALLOWED_VIDEO_TYPES.keys())
            return False, f"Invalid video format. Allowed: {allowed}"
        
        # Check file extension
        filename = file.filename.lower() if file.filename else ""
        valid_extensions = []
        for exts in cls.ALLOWED_VIDEO_TYPES.values():
            valid_extensions.extend(exts)
        
        if not any(filename.endswith(ext) for ext in valid_extensions):
            return False, f"Invalid video file extension. Allowed: {', '.join(valid_extensions)}"
        
        return True, None
    
    @classmethod
    def validate_audio_file(cls, file: UploadFile) -> Tuple[bool, Optional[str]]:
        """Validate an audio file
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file size
        if hasattr(file, 'size') and file.size:
            if file.size > cls.MAX_AUDIO_SIZE:
                size_mb = cls.MAX_AUDIO_SIZE / (1024 * 1024)
                return False, f"Audio file exceeds maximum size of {size_mb}MB"
        
        # Check content type
        content_type = file.content_type
        if content_type not in cls.ALLOWED_AUDIO_TYPES:
            allowed = ", ".join(cls.ALLOWED_AUDIO_TYPES.keys())
            return False, f"Invalid audio format. Allowed: {allowed}"
        
        # Check file extension
        filename = file.filename.lower() if file.filename else ""
        valid_extensions = []
        for exts in cls.ALLOWED_AUDIO_TYPES.values():
            valid_extensions.extend(exts)
        
        if not any(filename.endswith(ext) for ext in valid_extensions):
            return False, f"Invalid audio file extension. Allowed: {', '.join(valid_extensions)}"
        
        return True, None
    
    @classmethod
    def validate_video_count(cls, current_count: int, adding: int = 1) -> Tuple[bool, Optional[str]]:
        """Validate video count limits"""
        new_count = current_count + adding
        
        if new_count > cls.MAX_VIDEOS:
            return False, f"Maximum {cls.MAX_VIDEOS} videos allowed. Current: {current_count}"
        
        return True, None
    
    @classmethod
    def validate_total_size(cls, current_size: int, adding_size: int) -> Tuple[bool, Optional[str]]:
        """Validate total upload size"""
        new_total = current_size + adding_size
        
        if new_total > cls.MAX_TOTAL_SIZE:
            max_gb = cls.MAX_TOTAL_SIZE / (1024 * 1024 * 1024)
            current_gb = current_size / (1024 * 1024 * 1024)
            return False, f"Total upload size exceeds {max_gb}GB limit. Current: {current_gb:.2f}GB"
        
        return True, None
    
    @classmethod
    def get_file_size(cls, file: UploadFile) -> int:
        """Get file size in bytes"""
        # Try to get size from file object
        if hasattr(file, 'size') and file.size:
            return file.size
        
        # Otherwise, read the file to get size
        file.file.seek(0, 2)  # Seek to end
        size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        return size
