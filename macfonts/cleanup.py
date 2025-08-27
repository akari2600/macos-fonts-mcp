import os
import time
import asyncio
import glob
from typing import List, Optional
from .config import DEFAULT_OUT_DIR, DEFAULT_CACHE_DIR
from .logging_config import logger

class FileCleanupManager:
    """Manages cleanup of generated files and cache."""
    
    def __init__(self, max_age_hours: int = 24, max_files: int = 1000):
        self.max_age_seconds = max_age_hours * 3600
        self.max_files = max_files
    
    async def cleanup_old_files(self, directory: str = DEFAULT_OUT_DIR) -> int:
        """Remove files older than max_age_hours."""
        if not os.path.exists(directory):
            return 0
        
        current_time = time.time()
        removed_count = 0
        
        try:
            files = glob.glob(os.path.join(directory, "*"))
            for file_path in files:
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > self.max_age_seconds:
                        try:
                            os.remove(file_path)
                            removed_count += 1
                            logger.debug(f"Removed old file: {file_path}")
                        except OSError as e:
                            logger.warning(f"Failed to remove file {file_path}: {e}")
            
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} old files from {directory}")
            
            return removed_count
            
        except Exception as e:
            logger.error(f"Error during file cleanup: {e}")
            return 0
    
    async def cleanup_excess_files(self, directory: str = DEFAULT_OUT_DIR) -> int:
        """Remove excess files if count exceeds max_files."""
        if not os.path.exists(directory):
            return 0
        
        try:
            files = []
            for file_path in glob.glob(os.path.join(directory, "*")):
                if os.path.isfile(file_path):
                    files.append((file_path, os.path.getmtime(file_path)))
            
            if len(files) <= self.max_files:
                return 0
            
            # Sort by modification time (oldest first)
            files.sort(key=lambda x: x[1])
            
            # Remove oldest files
            excess_count = len(files) - self.max_files
            removed_count = 0
            
            for file_path, _ in files[:excess_count]:
                try:
                    os.remove(file_path)
                    removed_count += 1
                    logger.debug(f"Removed excess file: {file_path}")
                except OSError as e:
                    logger.warning(f"Failed to remove file {file_path}: {e}")
            
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} excess files from {directory}")
            
            return removed_count
            
        except Exception as e:
            logger.error(f"Error during excess file cleanup: {e}")
            return 0
    
    async def get_directory_size(self, directory: str = DEFAULT_OUT_DIR) -> int:
        """Get total size of directory in bytes."""
        if not os.path.exists(directory):
            return 0
        
        total_size = 0
        try:
            for file_path in glob.glob(os.path.join(directory, "*")):
                if os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"Error calculating directory size: {e}")
        
        return total_size
    
    async def cleanup_by_size(self, directory: str = DEFAULT_OUT_DIR, max_size_mb: int = 500) -> int:
        """Remove oldest files if directory exceeds max_size_mb."""
        if not os.path.exists(directory):
            return 0
        
        max_size_bytes = max_size_mb * 1024 * 1024
        current_size = await self.get_directory_size(directory)
        
        if current_size <= max_size_bytes:
            return 0
        
        try:
            files = []
            for file_path in glob.glob(os.path.join(directory, "*")):
                if os.path.isfile(file_path):
                    files.append((file_path, os.path.getmtime(file_path), os.path.getsize(file_path)))
            
            # Sort by modification time (oldest first)
            files.sort(key=lambda x: x[1])
            
            removed_count = 0
            freed_size = 0
            
            for file_path, _, file_size in files:
                if current_size - freed_size <= max_size_bytes:
                    break
                
                try:
                    os.remove(file_path)
                    removed_count += 1
                    freed_size += file_size
                    logger.debug(f"Removed file to free space: {file_path}")
                except OSError as e:
                    logger.warning(f"Failed to remove file {file_path}: {e}")
            
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} files, freed {freed_size / (1024*1024):.1f} MB")
            
            return removed_count
            
        except Exception as e:
            logger.error(f"Error during size-based cleanup: {e}")
            return 0
    
    async def full_cleanup(self) -> dict:
        """Perform all cleanup operations."""
        results = {
            "old_files_removed": 0,
            "excess_files_removed": 0,
            "size_cleanup_removed": 0,
            "total_removed": 0
        }
        
        try:
            results["old_files_removed"] = await self.cleanup_old_files()
            results["excess_files_removed"] = await self.cleanup_excess_files()
            results["size_cleanup_removed"] = await self.cleanup_by_size()
            results["total_removed"] = (
                results["old_files_removed"] + 
                results["excess_files_removed"] + 
                results["size_cleanup_removed"]
            )
            
            if results["total_removed"] > 0:
                logger.info(f"Full cleanup completed: {results}")
            
        except Exception as e:
            logger.error(f"Error during full cleanup: {e}")
        
        return results

# Global cleanup manager
cleanup_manager = FileCleanupManager()

async def start_cleanup_task():
    """Start background task for periodic cleanup."""
    async def cleanup_loop():
        while True:
            try:
                await cleanup_manager.full_cleanup()
                # Run cleanup every 30 minutes
                await asyncio.sleep(1800)
            except Exception as e:
                logger.error(f"Cleanup task error: {e}")
                await asyncio.sleep(1800)
    
    asyncio.create_task(cleanup_loop())
    logger.info("File cleanup task started")

async def cleanup_on_exit():
    """Cleanup function to call on server shutdown."""
    logger.info("Performing final cleanup...")
    results = await cleanup_manager.full_cleanup()
    logger.info(f"Final cleanup completed: {results}")