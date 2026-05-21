from abc import ABC, abstractmethod
from typing import BinaryIO, Optional
import os
import shutil
from pathlib import Path
import uuid


class StorageProvider(ABC):
    """Abstract storage provider interface for future cloud migration"""
    
    @abstractmethod
    async def save_file(self, file: BinaryIO, session_id: str, file_type: str, filename: str) -> str:
        """Save a file and return storage key"""
        pass
    
    @abstractmethod
    async def delete_file(self, storage_key: str) -> bool:
        """Delete a file"""
        pass
    
    @abstractmethod
    async def get_file_path(self, storage_key: str) -> str:
        """Get file path for serving"""
        pass
    
    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete all files for a session"""
        pass


class LocalStorageProvider(StorageProvider):
    """Local file storage implementation"""
    
    def __init__(self, base_path: str = "/app/backend/uploads"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_session_path(self, session_id: str) -> Path:
        """Get the directory path for a session"""
        return self.base_path / "sessions" / session_id
    
    def _get_file_path(self, session_id: str, file_type: str, filename: str) -> Path:
        """Get the full path for a file"""
        session_path = self._get_session_path(session_id)
        type_path = session_path / file_type
        type_path.mkdir(parents=True, exist_ok=True)
        return type_path / filename
    
    async def save_file(self, file: BinaryIO, session_id: str, file_type: str, filename: str) -> str:
        """Save file locally and return storage key"""
        # Generate unique filename to avoid conflicts
        ext = Path(filename).suffix
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        file_path = self._get_file_path(session_id, file_type, unique_filename)
        
        # Save file
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file, f)
        
        # Return storage key (relative path for future S3 compatibility)
        storage_key = f"sessions/{session_id}/{file_type}/{unique_filename}"
        return storage_key
    
    async def delete_file(self, storage_key: str) -> bool:
        """Delete a file by storage key"""
        try:
            file_path = self.base_path / storage_key
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            print(f"Error deleting file {storage_key}: {e}")
            return False
    
    async def get_file_path(self, storage_key: str) -> str:
        """Get absolute file path"""
        return str(self.base_path / storage_key)
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete entire session directory"""
        try:
            session_path = self._get_session_path(session_id)
            if session_path.exists():
                shutil.rmtree(session_path)
                return True
            return False
        except Exception as e:
            print(f"Error deleting session {session_id}: {e}")
            return False


class S3StorageProvider(StorageProvider):
    """AWS S3 storage implementation (future)"""
    
    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        self.bucket_name = bucket_name
        self.region = region
        # TODO: Initialize boto3 client
        raise NotImplementedError("S3 storage not yet implemented")
    
    async def save_file(self, file: BinaryIO, session_id: str, file_type: str, filename: str) -> str:
        # TODO: Upload to S3
        raise NotImplementedError()
    
    async def delete_file(self, storage_key: str) -> bool:
        # TODO: Delete from S3
        raise NotImplementedError()
    
    async def get_file_path(self, storage_key: str) -> str:
        # TODO: Return S3 URL
        raise NotImplementedError()
    
    async def delete_session(self, session_id: str) -> bool:
        # TODO: Delete S3 objects by prefix
        raise NotImplementedError()


class R2StorageProvider(StorageProvider):
    """Cloudflare R2 storage implementation (future)"""
    
    def __init__(self, bucket_name: str, account_id: str):
        self.bucket_name = bucket_name
        self.account_id = account_id
        # TODO: Initialize R2 client (S3-compatible)
        raise NotImplementedError("R2 storage not yet implemented")
    
    async def save_file(self, file: BinaryIO, session_id: str, file_type: str, filename: str) -> str:
        raise NotImplementedError()
    
    async def delete_file(self, storage_key: str) -> bool:
        raise NotImplementedError()
    
    async def get_file_path(self, storage_key: str) -> str:
        raise NotImplementedError()
    
    async def delete_session(self, session_id: str) -> bool:
        raise NotImplementedError()


# Factory function to get storage provider
def get_storage_provider(provider_type: str = "local") -> StorageProvider:
    """Get storage provider instance"""
    if provider_type == "local":
        return LocalStorageProvider()
    elif provider_type == "s3":
        # TODO: Get from env vars
        raise NotImplementedError("S3 not configured")
    elif provider_type == "r2":
        # TODO: Get from env vars
        raise NotImplementedError("R2 not configured")
    else:
        raise ValueError(f"Unknown storage provider: {provider_type}")
