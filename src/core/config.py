"""Configuration management for Flow2API"""
import os
import tomli
from pathlib import Path
from typing import Dict, Any, Optional, Type, Tuple
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

class TomlConfigSettingsSource(PydanticBaseSettingsSource):
    """
    A settings source that loads configuration from setting.toml
    and maps nested sections to flat fields.
    """
    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        return None, field_name, False

    def __call__(self) -> Dict[str, Any]:
        config_path = Path(__file__).parent.parent.parent / "config" / "setting.toml"
        if not config_path.exists():
            return {}
            
        with open(config_path, "rb") as f:
            try:
                toml_data = tomli.load(f)
            except Exception:
                return {}

        flat_data = {}
        
        # Global section
        for k, v in toml_data.get("global", {}).items():
            flat_data[k] = v
            
        # Sections with prefix
        sections = {
            "flow": "flow_",
            "server": "server_",
            "debug": "debug_",
            "generation": "generation_",
            "admin": "admin_",
            "cache": "cache_"
        }
        
        for section, prefix in sections.items():
            for k, v in toml_data.get(section, {}).items():
                # Handle timeout key conflict by explicit mapping if needed, 
                # but flow_timeout, cache_timeout etc are unique.
                flat_data[f"{prefix}{k}"] = v
                
        # Proxy section (special handling for keys)
        # proxy.proxy_enabled -> proxy_enabled
        # proxy.proxy_url -> proxy_url
        for k, v in toml_data.get("proxy", {}).items():
             flat_data[k] = v
             
        return flat_data

class Settings(BaseSettings):
    # Global
    api_key: str = Field(validation_alias=AliasChoices("api_key", "API_KEY"), default="han1234")
    admin_username: str = Field(validation_alias=AliasChoices("admin_username", "ADMIN_USERNAME"), default="admin")
    admin_password: str = Field(validation_alias=AliasChoices("admin_password", "ADMIN_PASSWORD"), default="admin")
    
    # Flow
    flow_labs_base_url: str = Field(validation_alias=AliasChoices("flow_labs_base_url", "FLOW_LABS_BASE_URL"), default="https://labs.google/fx/api")
    flow_api_base_url: str = Field(validation_alias=AliasChoices("flow_api_base_url", "FLOW_API_BASE_URL"), default="https://aisandbox-pa.googleapis.com/v1")
    flow_timeout: int = Field(validation_alias=AliasChoices("flow_timeout", "FLOW_TIMEOUT"), default=120)
    flow_poll_interval: float = Field(validation_alias=AliasChoices("flow_poll_interval", "FLOW_POLL_INTERVAL"), default=3.0)
    flow_max_poll_attempts: int = Field(validation_alias=AliasChoices("flow_max_poll_attempts", "FLOW_MAX_POLL_ATTEMPTS"), default=200)
    flow_max_retries: int = Field(default=3) 

    # Server
    server_host: str = Field(validation_alias=AliasChoices("server_host", "SERVER_HOST"), default="0.0.0.0")
    server_port: int = Field(validation_alias=AliasChoices("server_port", "SERVER_PORT"), default=8000)
    
    # Debug
    debug_enabled: bool = Field(validation_alias=AliasChoices("debug_enabled", "DEBUG_ENABLED"), default=False)
    debug_log_requests: bool = Field(validation_alias=AliasChoices("debug_log_requests", "DEBUG_LOG_REQUESTS"), default=True)
    debug_log_responses: bool = Field(validation_alias=AliasChoices("debug_log_responses", "DEBUG_LOG_RESPONSES"), default=True)
    debug_mask_token: bool = Field(validation_alias=AliasChoices("debug_mask_token", "DEBUG_MASK_TOKEN"), default=True)
    
    # Proxy
    proxy_enabled: bool = Field(validation_alias=AliasChoices("proxy_enabled", "PROXY_ENABLED"), default=False)
    proxy_url: Optional[str] = Field(validation_alias=AliasChoices("proxy_url", "PROXY_URL"), default="")
    
    # Generation
    generation_image_timeout: int = Field(validation_alias=AliasChoices("generation_image_timeout", "GENERATION_IMAGE_TIMEOUT"), default=300)
    generation_video_timeout: int = Field(validation_alias=AliasChoices("generation_video_timeout", "GENERATION_VIDEO_TIMEOUT"), default=1500)
    
    # Admin
    admin_error_ban_threshold: int = Field(validation_alias=AliasChoices("admin_error_ban_threshold", "ADMIN_ERROR_BAN_THRESHOLD"), default=3)
    
    # Cache
    cache_enabled: bool = Field(validation_alias=AliasChoices("cache_enabled", "CACHE_ENABLED"), default=False)
    cache_timeout: int = Field(validation_alias=AliasChoices("cache_timeout", "CACHE_TIMEOUT"), default=7200)
    cache_base_url: Optional[str] = Field(validation_alias=AliasChoices("cache_base_url", "CACHE_BASE_URL"), default="")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            TomlConfigSettingsSource(settings_cls),
        )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

class Config:
    """Application configuration wrapper"""

    def __init__(self):
        self.settings = Settings()
        self._db_overrides: Dict[str, Any] = {}

    def reload_config(self):
        """Reload configuration from file"""
        self.settings = Settings()
        # Note: We do NOT clear _db_overrides here, preserving DB state.

    def get_raw_config(self) -> Dict[str, Any]:
        """Get raw configuration dictionary (nested structure)"""
        s = self.settings
        return {
            "global": {
                "api_key": s.api_key,
                "admin_username": s.admin_username,
                "admin_password": s.admin_password,
            },
            "flow": {
                "labs_base_url": s.flow_labs_base_url,
                "api_base_url": s.flow_api_base_url,
                "timeout": s.flow_timeout,
                "poll_interval": s.flow_poll_interval,
                "max_poll_attempts": s.flow_max_poll_attempts,
                "max_retries": s.flow_max_retries
            },
            "server": {
                "host": s.server_host,
                "port": s.server_port,
            },
            "debug": {
                "enabled": s.debug_enabled,
                "log_requests": s.debug_log_requests,
                "log_responses": s.debug_log_responses,
                "mask_token": s.debug_mask_token,
            },
            "proxy": {
                "proxy_enabled": s.proxy_enabled,
                "proxy_url": s.proxy_url,
            },
            "generation": {
                "image_timeout": s.generation_image_timeout,
                "video_timeout": s.generation_video_timeout,
            },
            "admin": {
                "error_ban_threshold": s.admin_error_ban_threshold,
            },
            "cache": {
                "enabled": s.cache_enabled,
                "timeout": s.cache_timeout,
                "base_url": s.cache_base_url,
            }
        }

    def get_locked_status(self) -> Dict[str, bool]:
        """Get status of which settings are locked by environment variables"""
        locked = {}
        for field_name, field_info in self.settings.model_fields.items():
            alias = field_info.validation_alias
            env_var = None
            if isinstance(alias, AliasChoices):
                # We assume the second choice is the env var as per our definition
                if len(alias.choices) > 1:
                    env_var = alias.choices[1]
            elif isinstance(alias, str):
                env_var = alias
            
            if env_var:
                locked[env_var] = self._is_locked(env_var)
        return locked
        
    def _is_locked(self, env_var: str) -> bool:
        return env_var in os.environ

    # Properties
    
    @property
    def admin_username(self) -> str:
        if self._is_locked("ADMIN_USERNAME"):
            return self.settings.admin_username
        return self._db_overrides.get("admin_username", self.settings.admin_username)

    @admin_username.setter
    def admin_username(self, value: str):
        self._db_overrides["admin_username"] = value

    def set_admin_username_from_db(self, username: str):
        self._db_overrides["admin_username"] = username

    @property
    def admin_password(self) -> str:
        if self._is_locked("ADMIN_PASSWORD"):
            return self.settings.admin_password
        return self._db_overrides.get("admin_password", self.settings.admin_password)

    @admin_password.setter
    def admin_password(self, value: str):
        self._db_overrides["admin_password"] = value

    def set_admin_password_from_db(self, password: str):
        self._db_overrides["admin_password"] = password

    @property
    def api_key(self) -> str:
        if self._is_locked("API_KEY"):
            return self.settings.api_key
        return self._db_overrides.get("api_key", self.settings.api_key)

    @api_key.setter
    def api_key(self, value: str):
        self._db_overrides["api_key"] = value

    # Flow
    @property
    def flow_labs_base_url(self) -> str:
        # Assuming no DB override for these yet
        if self._is_locked("FLOW_LABS_BASE_URL"):
            return self.settings.flow_labs_base_url
        return self.settings.flow_labs_base_url

    @property
    def flow_api_base_url(self) -> str:
        return self.settings.flow_api_base_url

    @property
    def flow_timeout(self) -> int:
        return self.settings.flow_timeout

    @property
    def flow_max_retries(self) -> int:
        return self.settings.flow_max_retries

    @property
    def poll_interval(self) -> float:
        return self.settings.flow_poll_interval

    @property
    def max_poll_attempts(self) -> int:
        return self.settings.flow_max_poll_attempts

    # Server
    @property
    def server_host(self) -> str:
        return self.settings.server_host

    @property
    def server_port(self) -> int:
        return self.settings.server_port

    # Debug
    @property
    def debug_enabled(self) -> bool:
        if self._is_locked("DEBUG_ENABLED"):
            return self.settings.debug_enabled
        return self._db_overrides.get("debug_enabled", self.settings.debug_enabled)

    def set_debug_enabled(self, enabled: bool):
        self._db_overrides["debug_enabled"] = enabled

    @property
    def debug_log_requests(self) -> bool:
        return self.settings.debug_log_requests

    @property
    def debug_log_responses(self) -> bool:
        return self.settings.debug_log_responses

    @property
    def debug_mask_token(self) -> bool:
        return self.settings.debug_mask_token

    # Generation
    @property
    def image_timeout(self) -> int:
        if self._is_locked("GENERATION_IMAGE_TIMEOUT"):
            return self.settings.generation_image_timeout
        return self._db_overrides.get("image_timeout", self.settings.generation_image_timeout)

    def set_image_timeout(self, timeout: int):
        self._db_overrides["image_timeout"] = timeout

    @property
    def video_timeout(self) -> int:
        if self._is_locked("GENERATION_VIDEO_TIMEOUT"):
            return self.settings.generation_video_timeout
        return self._db_overrides.get("video_timeout", self.settings.generation_video_timeout)

    def set_video_timeout(self, timeout: int):
        self._db_overrides["video_timeout"] = timeout

    # Cache
    @property
    def cache_enabled(self) -> bool:
        if self._is_locked("CACHE_ENABLED"):
            return self.settings.cache_enabled
        return self._db_overrides.get("cache_enabled", self.settings.cache_enabled)

    def set_cache_enabled(self, enabled: bool):
        self._db_overrides["cache_enabled"] = enabled

    @property
    def cache_timeout(self) -> int:
        if self._is_locked("CACHE_TIMEOUT"):
            return self.settings.cache_timeout
        return self._db_overrides.get("cache_timeout", self.settings.cache_timeout)

    def set_cache_timeout(self, timeout: int):
        self._db_overrides["cache_timeout"] = timeout

    @property
    def cache_base_url(self) -> str:
        if self._is_locked("CACHE_BASE_URL"):
            return self.settings.cache_base_url
        return self._db_overrides.get("cache_base_url", self.settings.cache_base_url)

    def set_cache_base_url(self, base_url: str):
        self._db_overrides["cache_base_url"] = base_url
    
    # Proxy - Note: DB overrides existed in old config implicitly via get? 
    # Old config: `if "proxy" not in self._config...`. No, ProxyManager uses DB.
    # But Config class had proxy props? No, only in `_apply_env_vars` it set them.
    # `Config` didn't have proxy properties exposed!
    # Let's check `src/core/config.py` again (memory).
    # It has `proxy` dict in `_config`.
    # But no `@property def proxy_enabled(self)`.
    # Downstream usage? `services.flow_client`? `services.proxy_manager`?
    # `services/proxy_manager.py` likely reads from DB directly or config.
    # `services/flow_client.py`?
    
    # Let's add proxy properties anyway as we have them in Settings.
    @property
    def proxy_enabled(self) -> bool:
         # Env > DB (from where?) > TOML.
         # ProxyManager seems to handle DB logic.
         # But if we want to support Env locking for Proxy:
         return self.settings.proxy_enabled

    @property
    def proxy_url(self) -> Optional[str]:
        return self.settings.proxy_url


# Global config instance
config = Config()
