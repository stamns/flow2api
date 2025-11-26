"""Proxy management module"""
from typing import Optional
from ..core.database import Database
from ..core.models import ProxyConfig
from ..core.config import Config

class ProxyManager:
    """Proxy configuration manager"""

    def __init__(self, db: Database, config: Config):
        self.db = db
        self.config = config

    async def get_proxy_url(self) -> Optional[str]:
        """Get proxy URL if enabled, otherwise return None"""
        # Use config for effective value (Env > DB > Default)
        if self.config.proxy_enabled and self.config.proxy_url:
            return self.config.proxy_url
        return None

    async def update_proxy_config(self, enabled: bool, proxy_url: Optional[str]):
        """Update proxy configuration"""
        # Update DB
        await self.db.update_proxy_config(enabled, proxy_url)
        # Update Config in-memory
        self.config.set_proxy_enabled(enabled)
        self.config.set_proxy_url(proxy_url)

    async def get_proxy_config(self) -> ProxyConfig:
        """Get proxy configuration"""
        # Return effective configuration
        return ProxyConfig(
            id=1,
            enabled=self.config.proxy_enabled,
            proxy_url=self.config.proxy_url
        )
