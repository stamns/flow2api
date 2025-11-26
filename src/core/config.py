"""Configuration management for Flow2API"""
import os
import json
import tomli
from pathlib import Path
from typing import Dict, Any, Optional

class Config:
    """Application configuration"""

    def __init__(self):
        self._config = self._load_config()
        self._apply_env_vars()
        self._admin_username: Optional[str] = None
        self._admin_password: Optional[str] = None

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from setting.toml"""
        config_path = Path(__file__).parent.parent.parent / "config" / "setting.toml"
        with open(config_path, "rb") as f:
            return tomli.load(f)

    def _apply_env_vars(self):
        """Override configuration with environment variables"""
        # Global settings
        if os.getenv("API_KEY"):
            self._config["global"]["api_key"] = os.getenv("API_KEY")
        if os.getenv("ADMIN_USERNAME"):
            self._config["global"]["admin_username"] = os.getenv("ADMIN_USERNAME")
        if os.getenv("ADMIN_PASSWORD"):
            self._config["global"]["admin_password"] = os.getenv("ADMIN_PASSWORD")

        # Flow settings
        if os.getenv("FLOW_LABS_BASE_URL"):
            self._config["flow"]["labs_base_url"] = os.getenv("FLOW_LABS_BASE_URL")
        if os.getenv("FLOW_API_BASE_URL"):
            self._config["flow"]["api_base_url"] = os.getenv("FLOW_API_BASE_URL")
        if os.getenv("FLOW_TIMEOUT"):
            self._config["flow"]["timeout"] = int(os.getenv("FLOW_TIMEOUT"))
        if os.getenv("FLOW_POLL_INTERVAL"):
            self._config["flow"]["poll_interval"] = float(os.getenv("FLOW_POLL_INTERVAL"))
        if os.getenv("FLOW_MAX_POLL_ATTEMPTS"):
            self._config["flow"]["max_poll_attempts"] = int(os.getenv("FLOW_MAX_POLL_ATTEMPTS"))

        # Server settings
        if os.getenv("SERVER_HOST"):
            self._config["server"]["host"] = os.getenv("SERVER_HOST")
        if os.getenv("SERVER_PORT"):
            self._config["server"]["port"] = int(os.getenv("SERVER_PORT"))

        # Debug settings
        if "debug" not in self._config:
            self._config["debug"] = {}
        if os.getenv("DEBUG_ENABLED"):
            self._config["debug"]["enabled"] = os.getenv("DEBUG_ENABLED").lower() == "true"
        if os.getenv("DEBUG_LOG_REQUESTS"):
            self._config["debug"]["log_requests"] = os.getenv("DEBUG_LOG_REQUESTS").lower() == "true"
        if os.getenv("DEBUG_LOG_RESPONSES"):
            self._config["debug"]["log_responses"] = os.getenv("DEBUG_LOG_RESPONSES").lower() == "true"
        if os.getenv("DEBUG_MASK_TOKEN"):
            self._config["debug"]["mask_token"] = os.getenv("DEBUG_MASK_TOKEN").lower() == "true"

        # Proxy settings
        if "proxy" not in self._config:
            self._config["proxy"] = {}
        if os.getenv("PROXY_ENABLED"):
            self._config["proxy"]["proxy_enabled"] = os.getenv("PROXY_ENABLED").lower() == "true"
        if os.getenv("PROXY_URL"):
            self._config["proxy"]["proxy_url"] = os.getenv("PROXY_URL")

        # Generation settings
        if "generation" not in self._config:
            self._config["generation"] = {}
        if os.getenv("GENERATION_IMAGE_TIMEOUT"):
            self._config["generation"]["image_timeout"] = int(os.getenv("GENERATION_IMAGE_TIMEOUT"))
        if os.getenv("GENERATION_VIDEO_TIMEOUT"):
            self._config["generation"]["video_timeout"] = int(os.getenv("GENERATION_VIDEO_TIMEOUT"))

        # Admin settings
        if "admin" not in self._config:
            self._config["admin"] = {}
        if os.getenv("ADMIN_ERROR_BAN_THRESHOLD"):
            self._config["admin"]["error_ban_threshold"] = int(os.getenv("ADMIN_ERROR_BAN_THRESHOLD"))

        # Database settings
        if os.getenv("DATABASE_URL"):
            self._config["database"] = {"url": os.getenv("DATABASE_URL")}

        # Cache settings
        if "cache" not in self._config:
            self._config["cache"] = {}
        if os.getenv("CACHE_ENABLED"):
            self._config["cache"]["enabled"] = os.getenv("CACHE_ENABLED").lower() == "true"
        if os.getenv("CACHE_TIMEOUT"):
            self._config["cache"]["timeout"] = int(os.getenv("CACHE_TIMEOUT"))
        if os.getenv("CACHE_BASE_URL"):
            self._config["cache"]["base_url"] = os.getenv("CACHE_BASE_URL")

    def reload_config(self):
        """Reload configuration from file"""
        self._config = self._load_config()
        self._apply_env_vars()

    def get_raw_config(self) -> Dict[str, Any]:
        """Get raw configuration dictionary"""
        return self._config

    @property
    def admin_username(self) -> str:
        # If admin_username is set from database, use it; otherwise fall back to config file
        if self._admin_username is not None:
            return self._admin_username
        return self._config["global"]["admin_username"]

    @admin_username.setter
    def admin_username(self, value: str):
        self._admin_username = value
        self._config["global"]["admin_username"] = value

    def set_admin_username_from_db(self, username: str):
        """Set admin username from database"""
        self._admin_username = username

    # Flow2API specific properties
    @property
    def flow_labs_base_url(self) -> str:
        """Google Labs base URL for project management"""
        return self._config["flow"]["labs_base_url"]

    @property
    def flow_api_base_url(self) -> str:
        """Google AI Sandbox API base URL for generation"""
        return self._config["flow"]["api_base_url"]

    @property
    def flow_timeout(self) -> int:
        return self._config["flow"]["timeout"]

    @property
    def flow_max_retries(self) -> int:
        return self._config["flow"]["max_retries"]

    @property
    def poll_interval(self) -> float:
        return self._config["flow"]["poll_interval"]

    @property
    def max_poll_attempts(self) -> int:
        return self._config["flow"]["max_poll_attempts"]

    @property
    def server_host(self) -> str:
        return self._config["server"]["host"]

    @property
    def server_port(self) -> int:
        return self._config["server"]["port"]

    @property
    def debug_enabled(self) -> bool:
        return self._config.get("debug", {}).get("enabled", False)

    @property
    def debug_log_requests(self) -> bool:
        return self._config.get("debug", {}).get("log_requests", True)

    @property
    def debug_log_responses(self) -> bool:
        return self._config.get("debug", {}).get("log_responses", True)

    @property
    def debug_mask_token(self) -> bool:
        return self._config.get("debug", {}).get("mask_token", True)

    # Mutable properties for runtime updates
    @property
    def api_key(self) -> str:
        return self._config["global"]["api_key"]

    @api_key.setter
    def api_key(self, value: str):
        self._config["global"]["api_key"] = value

    @property
    def admin_password(self) -> str:
        # If admin_password is set from database, use it; otherwise fall back to config file
        if self._admin_password is not None:
            return self._admin_password
        return self._config["global"]["admin_password"]

    @admin_password.setter
    def admin_password(self, value: str):
        self._admin_password = value
        self._config["global"]["admin_password"] = value

    def set_admin_password_from_db(self, password: str):
        """Set admin password from database"""
        self._admin_password = password

    def set_debug_enabled(self, enabled: bool):
        """Set debug mode enabled/disabled"""
        if "debug" not in self._config:
            self._config["debug"] = {}
        self._config["debug"]["enabled"] = enabled

    @property
    def image_timeout(self) -> int:
        """Get image generation timeout in seconds"""
        return self._config.get("generation", {}).get("image_timeout", 300)

    def set_image_timeout(self, timeout: int):
        """Set image generation timeout in seconds"""
        if "generation" not in self._config:
            self._config["generation"] = {}
        self._config["generation"]["image_timeout"] = timeout

    @property
    def video_timeout(self) -> int:
        """Get video generation timeout in seconds"""
        return self._config.get("generation", {}).get("video_timeout", 1500)

    def set_video_timeout(self, timeout: int):
        """Set video generation timeout in seconds"""
        if "generation" not in self._config:
            self._config["generation"] = {}
        self._config["generation"]["video_timeout"] = timeout

    # Cache configuration
    @property
    def cache_enabled(self) -> bool:
        """Get cache enabled status"""
        return self._config.get("cache", {}).get("enabled", False)

    def set_cache_enabled(self, enabled: bool):
        """Set cache enabled status"""
        if "cache" not in self._config:
            self._config["cache"] = {}
        self._config["cache"]["enabled"] = enabled

    @property
    def cache_timeout(self) -> int:
        """Get cache timeout in seconds"""
        return self._config.get("cache", {}).get("timeout", 7200)

    def set_cache_timeout(self, timeout: int):
        """Set cache timeout in seconds"""
        if "cache" not in self._config:
            self._config["cache"] = {}
        self._config["cache"]["timeout"] = timeout

    @property
    def cache_base_url(self) -> str:
        """Get cache base URL"""
        return self._config.get("cache", {}).get("base_url", "")

    def set_cache_base_url(self, base_url: str):
        """Set cache base URL"""
        if "cache" not in self._config:
            self._config["cache"] = {}
        self._config["cache"]["base_url"] = base_url

    @property
    def database_url(self) -> Optional[str]:
        """Get database URL from environment"""
        return self._config.get("database", {}).get("url")

# Global config instance
config = Config()
