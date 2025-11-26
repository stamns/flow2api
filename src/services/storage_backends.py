from abc import ABC, abstractmethod
import os
import time
import asyncio
from pathlib import Path
from typing import Optional, List
import shutil
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError
from ..core.logger import debug_logger

class StorageBackend(ABC):
    """Abstract base class for storage backends"""

    @abstractmethod
    async def exists(self, filename: str) -> bool:
        """Check if file exists"""
        pass

    @abstractmethod
    async def save(self, filename: str, content: bytes, media_type: str) -> str:
        """Save content and return public/signed URL"""
        pass

    @abstractmethod
    async def get_url(self, filename: str) -> str:
        """Get public/signed URL for existing file"""
        pass

    @abstractmethod
    async def delete(self, filename: str) -> bool:
        """Delete file"""
        pass

    @abstractmethod
    async def purge_expired(self, ttl: int) -> int:
        """Purge expired files based on TTL"""
        pass

class LocalStorageBackend(StorageBackend):
    """Local file system storage backend"""

    def __init__(self, cache_dir: str, base_url: str):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = base_url.rstrip("/")

    async def exists(self, filename: str) -> bool:
        return (self.cache_dir / filename).exists()

    async def save(self, filename: str, content: bytes, media_type: str) -> str:
        file_path = self.cache_dir / filename
        # Write file in a thread to avoid blocking event loop
        await asyncio.to_thread(self._write_file, file_path, content)
        return await self.get_url(filename)

    def _write_file(self, path: Path, content: bytes):
        with open(path, "wb") as f:
            f.write(content)

    async def get_url(self, filename: str) -> str:
        # Assuming base_url points to the server root where /tmp is mounted or served
        # If base_url is "http://localhost:8000", result is "http://localhost:8000/tmp/filename"
        # If base_url includes /tmp, we should handle that.
        # The current implementation in GenerationHandler constructs: f"{self._get_base_url()}/tmp/{cached_filename}"
        # So we should probably return just the filename or the full URL?
        # The interface says "return public/signed URL".
        # So we should return the full URL.
        # But we need to know the mount point.
        # Let's assume the base_url passed to __init__ is the root URL.
        
        # However, we are removing the /tmp mount in main.py.
        # "Remove the /tmp StaticFiles mount in src/main.py; instead, surface cached asset URLs via the configured CDN/base URL"
        # So if we use LocalStorageBackend, we actually DO need to serve the files somehow.
        # Maybe the instruction implies "Remove the /tmp mount" ONLY if using remote backend?
        # "Implement a remote object-storage backend... Remove the /tmp StaticFiles mount... Add configuration... and a 'local filesystem' fallback for developers."
        # If fallback is used, we probably still need the mount.
        # Or maybe I should implement a simple endpoint to serve files if LocalStorage is used?
        # Or keep the mount but make it conditional?
        
        # For now, I will assume base_url + "/tmp/" + filename
        return f"{self.base_url}/tmp/{filename}"

    async def delete(self, filename: str) -> bool:
        file_path = self.cache_dir / filename
        try:
            if file_path.exists():
                await asyncio.to_thread(os.remove, file_path)
                return True
        except Exception as e:
            debug_logger.log_error(f"Failed to delete local file {filename}: {str(e)}")
        return False

    async def purge_expired(self, ttl: int) -> int:
        removed_count = 0
        current_time = time.time()
        
        # Use asyncio.to_thread for directory iteration if there are many files
        files = await asyncio.to_thread(lambda: list(self.cache_dir.iterdir()))
        
        for file_path in files:
            if file_path.is_file():
                try:
                    stat = await asyncio.to_thread(os.stat, file_path)
                    file_age = current_time - stat.st_mtime
                    if file_age > ttl:
                        await asyncio.to_thread(os.remove, file_path)
                        removed_count += 1
                except Exception:
                    pass
        return removed_count

class S3StorageBackend(StorageBackend):
    """S3-compatible object storage backend"""

    def __init__(self, bucket_name: str, 
                 region_name: Optional[str] = None, 
                 endpoint_url: Optional[str] = None, 
                 access_key: Optional[str] = None, 
                 secret_key: Optional[str] = None,
                 public_domain: Optional[str] = None):
        
        self.bucket_name = bucket_name
        self.client = boto3.client(
            's3',
            region_name=region_name,
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        self.public_domain = public_domain

    async def exists(self, filename: str) -> bool:
        try:
            await asyncio.to_thread(
                self.client.head_object,
                Bucket=self.bucket_name,
                Key=filename
            )
            return True
        except ClientError:
            return False

    async def save(self, filename: str, content: bytes, media_type: str) -> str:
        content_type = "video/mp4" if media_type == "video" else "image/jpeg"
        
        # Store timestamp in metadata for TTL
        metadata = {
            "created_at": str(int(time.time()))
        }

        await asyncio.to_thread(
            self.client.put_object,
            Bucket=self.bucket_name,
            Key=filename,
            Body=content,
            ContentType=content_type,
            Metadata=metadata
        )
        
        return await self.get_url(filename)

    async def get_url(self, filename: str) -> str:
        if self.public_domain:
            return f"{self.public_domain.rstrip('/')}/{filename}"
        
        # Generate presigned URL
        # Ticket says "returns signed HTTPS URLs the API can stream back to clients even after the serverless function exits"
        # So we need a reasonably long expiration, maybe matching the cache TTL or a default like 1 hour.
        # But if we want them to remain accessible "across cold starts", presigned URL is good.
        
        url = await asyncio.to_thread(
            self.client.generate_presigned_url,
            'get_object',
            Params={'Bucket': self.bucket_name, 'Key': filename},
            ExpiresIn=3600 * 24  # 24 hours, or configurable
        )
        return url

    async def delete(self, filename: str) -> bool:
        try:
            await asyncio.to_thread(
                self.client.delete_object,
                Bucket=self.bucket_name,
                Key=filename
            )
            return True
        except Exception as e:
            debug_logger.log_error(f"Failed to delete S3 object {filename}: {str(e)}")
            return False

    async def purge_expired(self, ttl: int) -> int:
        removed_count = 0
        current_time = int(time.time())
        
        # List objects
        # Note: This might be slow for large buckets. 
        # But the requirement is an explicit purge job.
        
        paginator = self.client.get_paginator('list_objects_v2')
        
        # We need to run this in a thread because boto3 is blocking
        def _purge():
            count = 0
            for page in paginator.paginate(Bucket=self.bucket_name):
                if 'Contents' not in page:
                    continue
                
                for obj in page['Contents']:
                    key = obj['Key']
                    
                    # We need to get head_object to get custom metadata
                    # list_objects_v2 does NOT return custom metadata
                    try:
                        head = self.client.head_object(Bucket=self.bucket_name, Key=key)
                        metadata = head.get('Metadata', {})
                        created_at_str = metadata.get('created_at')
                        
                        if created_at_str:
                            created_at = int(created_at_str)
                            age = current_time - created_at
                            if age > ttl:
                                self.client.delete_object(Bucket=self.bucket_name, Key=key)
                                count += 1
                        else:
                            # Fallback to LastModified if metadata is missing?
                            # Maybe safer not to delete if we are unsure.
                            # But if we just uploaded it, it should have metadata.
                            # Let's use LastModified as fallback if metadata missing.
                            last_modified = obj['LastModified'].replace(tzinfo=timezone.utc).timestamp()
                            age = current_time - last_modified
                            if age > ttl:
                                self.client.delete_object(Bucket=self.bucket_name, Key=key)
                                count += 1
                                
                    except Exception as e:
                        debug_logger.log_error(f"Error checking/deleting {key}: {str(e)}")
            return count

        removed_count = await asyncio.to_thread(_purge)
        return removed_count
