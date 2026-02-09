import os
import shutil
from pathlib import Path
from typing import List, Tuple
from fastapi import UploadFile
import logging

logger = logging.getLogger(__name__)

class FileManager:
    """
    Handles file upload and storage.
    For now, stores files locally. Can be upgraded to MinIO/S3 later.
    """
    
    def __init__(self, storage_path: str = "./storage/uploads"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    async def save_upload(
        self, 
        file: UploadFile, 
        batch_id: str, 
        document_type: str
    ) -> Tuple[str, int]:
        """
        Save uploaded file to local storage.
        
        Returns:
            (file_path, file_size)
        """
        # Create batch directory
        batch_dir = self.storage_path / batch_id / document_type
        batch_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = batch_dir / file.filename
        
        with open(file_path, 'wb') as f:
            content = await file.read()
            f.write(content)
            file_size = len(content)
        
        logger.info(f"Saved file: {file_path} ({file_size} bytes)")
        return str(file_path), file_size
    
    def get_batch_files(self, batch_id: str) -> List[str]:
        """Get all files for a batch"""
        batch_dir = self.storage_path / batch_id
        if not batch_dir.exists():
            return []
        
        files = []
        for file_path in batch_dir.rglob('*'):
            if file_path.is_file():
                files.append(str(file_path))
        
        return files
    
    def delete_batch_files(self, batch_id: str):
        """Delete all files for a batch"""
        batch_dir = self.storage_path / batch_id
        if batch_dir.exists():
            shutil.rmtree(batch_dir)
            logger.info(f"Deleted batch files: {batch_id}")