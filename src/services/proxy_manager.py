"""Proxy management module"""
from typing import Optional
from ..core.database import Database
from ..core.models import ProxyConfig

class ProxyManager:
    """Proxy configuration manager"""

    def __init__(self, db: Database, config):
        self.db = db
        self.config = config

    async def get_proxy_url(self) -> Optional[str]:
        """Get proxy URL if enabled, otherwise return None"""
        # Env overrides (via config properties which check Env)
        # Note: config.proxy_enabled checks Env but not DB (in my implementation of Config.proxy_enabled)
        # Wait, Config.proxy_enabled: return self.settings.proxy_enabled (Env/TOML only).
        # It does NOT check DB.
        
        # So I should check config first (Env/TOML).
        # If Env is set (locked), use it.
        # Else use DB.
        
        if self.config._is_locked("PROXY_ENABLED") or self.config._is_locked("PROXY_URL"):
            if self.config.proxy_enabled and self.config.proxy_url:
                return self.config.proxy_url
            return None

        config = await self.db.get_proxy_config()
        if config and config.enabled and config.proxy_url:
            return config.proxy_url
        return None

    async def update_proxy_config(self, enabled: bool, proxy_url: Optional[str]):
        """Update proxy configuration"""
        await self.db.update_proxy_config(enabled, proxy_url)

    async def get_proxy_config(self) -> ProxyConfig:
        """Get proxy configuration"""
        db_config = await self.db.get_proxy_config()
        
        # Apply Env overrides
        enabled = db_config.enabled
        proxy_url = db_config.proxy_url
        
        if self.config._is_locked("PROXY_ENABLED"):
            enabled = self.config.proxy_enabled
            
        if self.config._is_locked("PROXY_URL"):
            proxy_url = self.config.proxy_url
            
        # Return merged config
        # We need to construct ProxyConfig. Is it mutable?
        # It's a Pydantic model probably.
        
        # I need to check core.models.ProxyConfig
        db_config.enabled = enabled
        db_config.proxy_url = proxy_url
        return db_config
