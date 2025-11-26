"""Configuration management for Flow2API"""
import os
from typing import Dict, Any, Optional
from .settings import settings

class Config:
    """Application configuration wrapper around Settings with mutable overrides"""

    def __init__(self):
        # We rely on the global settings instance which has loaded from Env > TOML > Defaults
        self._settings = settings
        
        # Runtime overrides (from DB)
        self._db_admin_username: Optional[str] = None
        self._db_admin_password: Optional[str] = None
        self._db_api_key: Optional[str] = None
        self._db_debug_enabled: Optional[bool] = None
        self._db_debug_log_requests: Optional[bool] = None
        self._db_debug_log_responses: Optional[bool] = None
        self._db_debug_mask_token: Optional[bool] = None
        self._db_proxy_enabled: Optional[bool] = None
        self._db_proxy_url: Optional[str] = None
        self._db_image_timeout: Optional[int] = None
        self._db_video_timeout: Optional[int] = None
        self._db_error_ban_threshold: Optional[int] = None
        self._db_cache_enabled: Optional[bool] = None
        self._db_cache_timeout: Optional[int] = None
        self._db_cache_base_url: Optional[str] = None

    def get_raw_config(self) -> Dict[str, Any]:
        """Get raw configuration dictionary (matching legacy structure)"""
        return self._settings.to_legacy_dict()

    # Helpers
    def _get_effective_value(self, env_key: str, db_value: Any, settings_value: Any) -> Any:
        """
        Determine effective value:
        1. Env Var (Locked) - checked via os.environ to distinguish from default
        2. DB Override
        3. Settings Value (which includes TOML/Default)
        """
        # If env var is explicitly set, use it (ignoring DB)
        # Note: settings_value already contains the env var value if set,
        # but we check os.environ to decide priority against DB.
        if os.getenv(env_key) is not None:
             return settings_value
        
        if db_value is not None:
            return db_value
            
        return settings_value

    @property
    def admin_username(self) -> str:
        return self._get_effective_value("ADMIN_USERNAME", self._db_admin_username, self._settings.ADMIN_USERNAME)

    @admin_username.setter
    def admin_username(self, value: str):
        self._db_admin_username = value

    def set_admin_username_from_db(self, username: str):
        self._db_admin_username = username

    @property
    def admin_password(self) -> str:
        return self._get_effective_value("ADMIN_PASSWORD", self._db_admin_password, self._settings.ADMIN_PASSWORD)

    @admin_password.setter
    def admin_password(self, value: str):
        self._db_admin_password = value
    
    def set_admin_password_from_db(self, password: str):
        self._db_admin_password = password

    @property
    def api_key(self) -> str:
        return self._get_effective_value("API_KEY", self._db_api_key, self._settings.API_KEY)
        
    @api_key.setter
    def api_key(self, value: str):
        self._db_api_key = value

    # Flow properties
    @property
    def flow_labs_base_url(self) -> str:
        return self._settings.FLOW_LABS_BASE_URL
        
    @property
    def flow_api_base_url(self) -> str:
        return self._settings.FLOW_API_BASE_URL
        
    @property
    def flow_timeout(self) -> int:
        return self._settings.FLOW_TIMEOUT
        
    @property
    def flow_max_retries(self) -> int:
        return self._settings.FLOW_MAX_RETRIES

    @property
    def poll_interval(self) -> float:
        return self._settings.FLOW_POLL_INTERVAL

    @property
    def max_poll_attempts(self) -> int:
        return self._settings.FLOW_MAX_POLL_ATTEMPTS

    # Server
    @property
    def server_host(self) -> str:
        return self._settings.SERVER_HOST

    @property
    def server_port(self) -> int:
        return self._settings.SERVER_PORT

    # Debug
    @property
    def debug_enabled(self) -> bool:
        return self._get_effective_value("DEBUG_ENABLED", self._db_debug_enabled, self._settings.DEBUG_ENABLED)

    def set_debug_enabled(self, enabled: bool):
        self._db_debug_enabled = enabled

    @property
    def debug_log_requests(self) -> bool:
        return self._get_effective_value("DEBUG_LOG_REQUESTS", self._db_debug_log_requests, self._settings.DEBUG_LOG_REQUESTS)
        
    def set_debug_log_requests(self, enabled: bool):
        self._db_debug_log_requests = enabled

    @property
    def debug_log_responses(self) -> bool:
        return self._get_effective_value("DEBUG_LOG_RESPONSES", self._db_debug_log_responses, self._settings.DEBUG_LOG_RESPONSES)

    def set_debug_log_responses(self, enabled: bool):
        self._db_debug_log_responses = enabled

    @property
    def debug_mask_token(self) -> bool:
        return self._get_effective_value("DEBUG_MASK_TOKEN", self._db_debug_mask_token, self._settings.DEBUG_MASK_TOKEN)

    def set_debug_mask_token(self, enabled: bool):
        self._db_debug_mask_token = enabled

    # Proxy
    @property
    def proxy_enabled(self) -> bool:
        return self._get_effective_value("PROXY_ENABLED", self._db_proxy_enabled, self._settings.PROXY_ENABLED)

    def set_proxy_enabled(self, enabled: bool):
        self._db_proxy_enabled = enabled

    @property
    def proxy_url(self) -> str:
        return self._get_effective_value("PROXY_URL", self._db_proxy_url, self._settings.PROXY_URL)

    def set_proxy_url(self, url: str):
        self._db_proxy_url = url

    # Generation
    @property
    def image_timeout(self) -> int:
        return self._get_effective_value("GENERATION_IMAGE_TIMEOUT", self._db_image_timeout, self._settings.GENERATION_IMAGE_TIMEOUT)

    def set_image_timeout(self, timeout: int):
        self._db_image_timeout = timeout

    @property
    def video_timeout(self) -> int:
        return self._get_effective_value("GENERATION_VIDEO_TIMEOUT", self._db_video_timeout, self._settings.GENERATION_VIDEO_TIMEOUT)

    def set_video_timeout(self, timeout: int):
        self._db_video_timeout = timeout

    # Admin
    @property
    def error_ban_threshold(self) -> int:
        return self._get_effective_value("ADMIN_ERROR_BAN_THRESHOLD", self._db_error_ban_threshold, self._settings.ADMIN_ERROR_BAN_THRESHOLD)

    def set_error_ban_threshold(self, threshold: int):
        self._db_error_ban_threshold = threshold

    # Cache
    @property
    def cache_enabled(self) -> bool:
        return self._get_effective_value("CACHE_ENABLED", self._db_cache_enabled, self._settings.CACHE_ENABLED)

    def set_cache_enabled(self, enabled: bool):
        self._db_cache_enabled = enabled

    @property
    def cache_timeout(self) -> int:
        return self._get_effective_value("CACHE_TIMEOUT", self._db_cache_timeout, self._settings.CACHE_TIMEOUT)

    def set_cache_timeout(self, timeout: int):
        self._db_cache_timeout = timeout

    @property
    def cache_base_url(self) -> str:
        return self._get_effective_value("CACHE_BASE_URL", self._db_cache_base_url, self._settings.CACHE_BASE_URL)

    def set_cache_base_url(self, url: str):
        self._db_cache_base_url = url

    # Storage
    @property
    def storage_backend(self) -> str:
        return self._settings.STORAGE_BACKEND
        
    @property
    def s3_bucket_name(self) -> Optional[str]:
        return self._settings.S3_BUCKET_NAME
        
    @property
    def s3_region_name(self) -> Optional[str]:
        return self._settings.S3_REGION_NAME
        
    @property
    def s3_endpoint_url(self) -> Optional[str]:
        return self._settings.S3_ENDPOINT_URL
        
    @property
    def s3_access_key(self) -> Optional[str]:
        return self._settings.S3_ACCESS_KEY
        
    @property
    def s3_secret_key(self) -> Optional[str]:
        return self._settings.S3_SECRET_KEY
        
    @property
    def s3_public_domain(self) -> Optional[str]:
        return self._settings.S3_PUBLIC_DOMAIN

    @property
    def database_url(self) -> Optional[str]:
        return self._settings.DATABASE_URL
        
    def get_locked_status(self) -> Dict[str, bool]:
        """Get status of which settings are locked by environment variables"""
        locked = {}
        for field_name, field_info in self._settings.model_fields.items():
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

config = Config()
