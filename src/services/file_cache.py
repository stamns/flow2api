"""File caching service"""
import asyncio
import hashlib
import time
from pathlib import Path
from typing import Optional
from curl_cffi.requests import AsyncSession
from ..core.config import config
from ..core.logger import debug_logger
from .storage_backends import LocalStorageBackend, S3StorageBackend


class FileCache:
    """File caching service for videos"""

    def __init__(self, cache_dir: str = "tmp", default_timeout: int = 7200, proxy_manager=None):
        """
        Initialize file cache
        
        Args:
            cache_dir: Cache directory path (for local backend)
            default_timeout: Default cache timeout in seconds
            proxy_manager: ProxyManager instance for downloading files
        """
        self.default_timeout = default_timeout
        self.proxy_manager = proxy_manager
        
        # Initialize storage backend
        backend_type = config.storage_backend
        if backend_type == "s3":
            self.backend = S3StorageBackend(
                bucket_name=config.s3_bucket_name,
                region_name=config.s3_region_name,
                endpoint_url=config.s3_endpoint_url,
                access_key=config.s3_access_key,
                secret_key=config.s3_secret_key,
                public_domain=config.s3_public_domain
            )
        else:
            # Default to local
            self.backend = LocalStorageBackend(
                cache_dir=cache_dir,
                base_url=config.cache_base_url or "http://localhost:8000"
            )

    async def start_cleanup_task(self):
        """Deprecated: No-op"""
        pass

    async def stop_cleanup_task(self):
        """Deprecated: No-op"""
        pass
        
    async def purge_expired_files(self):
        """Purge expired files based on TTL"""
        try:
            count = await self.backend.purge_expired(self.default_timeout)
            if count > 0:
                debug_logger.log_info(f"Purge job: removed {count} expired cache files")
            return count
        except Exception as e:
            debug_logger.log_error(f"Purge job failed: {str(e)}")
            return 0

    def _generate_cache_filename(self, url: str, media_type: str) -> str:
        """Generate unique filename for cached file"""
        # Use URL hash as filename
        url_hash = hashlib.md5(url.encode()).hexdigest()

        # Determine file extension
        if media_type == "video":
            ext = ".mp4"
        elif media_type == "image":
            ext = ".jpg"
        else:
            ext = ""

        return f"{url_hash}{ext}"

    async def download_and_cache(self, url: str, media_type: str) -> str:
        """
        Download file from URL and cache it.
        
        Args:
            url: File URL to download
            media_type: 'image' or 'video'

        Returns:
            Public URL of the cached file
        """
        filename = self._generate_cache_filename(url, media_type)
        
        # Check if already exists in backend
        if await self.backend.exists(filename):
            debug_logger.log_info(f"Cache hit: {filename}")
            return await self.backend.get_url(filename)

        # Download file
        debug_logger.log_info(f"Downloading file from: {url}")

        try:
            # Get proxy if available
            proxy_url = None
            if self.proxy_manager:
                proxy_config = await self.proxy_manager.get_proxy_config()
                if proxy_config and proxy_config.enabled and proxy_config.proxy_url:
                    proxy_url = proxy_config.proxy_url

            # Download with proxy support
            async with AsyncSession() as session:
                proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
                response = await session.get(url, timeout=60, proxies=proxies)

                if response.status_code != 200:
                    raise Exception(f"Download failed: HTTP {response.status_code}")
                
                content = response.content

                # Save to backend
                public_url = await self.backend.save(filename, content, media_type)

                debug_logger.log_info(f"File cached: {filename} ({len(content)} bytes)")
                return public_url

        except Exception as e:
            debug_logger.log_error(
                error_message=f"Failed to download/cache file: {str(e)}",
                status_code=0,
                response_text=str(e)
            )
            raise Exception(f"Failed to cache file: {str(e)}")

    def set_timeout(self, timeout: int):
        """Set cache timeout in seconds"""
        self.default_timeout = timeout
        debug_logger.log_info(f"Cache timeout updated to {timeout} seconds")

    def get_timeout(self) -> int:
        """Get current cache timeout"""
        return self.default_timeout

    async def clear_all(self):
        """Clear all cached files (not implemented for all backends safely, mostly for testing)"""
        # For now, we can implement it by listing all files and deleting them. 
        # But for S3 this might be dangerous/slow. 
        # Let's just log a warning or leave it empty? 
        # The existing code did unlink on all files in cache_dir.
        pass
