from typing import Any, Dict, Tuple, Type, Optional
from pathlib import Path
import tomli
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

class TomlConfigSettingsSource(PydanticBaseSettingsSource):
    """
    A settings source class that loads variables from a TOML file
    at the project's root (config/setting.toml).
    """
    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> Tuple[Any, str, bool]:
        config_path = Path(__file__).parent.parent.parent / "config" / "setting.toml"
        
        if not config_path.exists():
             return None, field_name, False
             
        try:
            with open(config_path, "rb") as f:
                file_content = tomli.load(f)
        except Exception:
            # If TOML file is invalid or cannot be read, ignore it
            return None, field_name, False
            
        # Flatten the TOML structure to match Settings fields
        flat_config = self._flatten_toml(file_content)
        
        val = flat_config.get(field_name)
        return val, field_name, False

    def _flatten_toml(self, config: Dict[str, Any]) -> Dict[str, Any]:
        flat = {}
        
        # Global
        g = config.get("global", {})
        if "api_key" in g: flat["API_KEY"] = g["api_key"]
        if "admin_username" in g: flat["ADMIN_USERNAME"] = g["admin_username"]
        if "admin_password" in g: flat["ADMIN_PASSWORD"] = g["admin_password"]
        
        # Flow
        f = config.get("flow", {})
        if "labs_base_url" in f: flat["FLOW_LABS_BASE_URL"] = f["labs_base_url"]
        if "api_base_url" in f: flat["FLOW_API_BASE_URL"] = f["api_base_url"]
        if "timeout" in f: flat["FLOW_TIMEOUT"] = f["timeout"]
        if "poll_interval" in f: flat["FLOW_POLL_INTERVAL"] = f["poll_interval"]
        if "max_poll_attempts" in f: flat["FLOW_MAX_POLL_ATTEMPTS"] = f["max_poll_attempts"]
        
        # Server
        s = config.get("server", {})
        if "host" in s: flat["SERVER_HOST"] = s["host"]
        if "port" in s: flat["SERVER_PORT"] = s["port"]
        
        # Debug
        d = config.get("debug", {})
        if "enabled" in d: flat["DEBUG_ENABLED"] = d["enabled"]
        if "log_requests" in d: flat["DEBUG_LOG_REQUESTS"] = d["log_requests"]
        if "log_responses" in d: flat["DEBUG_LOG_RESPONSES"] = d["log_responses"]
        if "mask_token" in d: flat["DEBUG_MASK_TOKEN"] = d["mask_token"]
        
        # Proxy
        p = config.get("proxy", {})
        if "proxy_enabled" in p: flat["PROXY_ENABLED"] = p["proxy_enabled"]
        if "proxy_url" in p: flat["PROXY_URL"] = p["proxy_url"]
        
        # Generation
        gen = config.get("generation", {})
        if "image_timeout" in gen: flat["GENERATION_IMAGE_TIMEOUT"] = gen["image_timeout"]
        if "video_timeout" in gen: flat["GENERATION_VIDEO_TIMEOUT"] = gen["video_timeout"]
        
        # Admin
        a = config.get("admin", {})
        if "error_ban_threshold" in a: flat["ADMIN_ERROR_BAN_THRESHOLD"] = a["error_ban_threshold"]
        
        # Cache
        c = config.get("cache", {})
        if "enabled" in c: flat["CACHE_ENABLED"] = c["enabled"]
        if "timeout" in c: flat["CACHE_TIMEOUT"] = c["timeout"]
        if "base_url" in c: flat["CACHE_BASE_URL"] = c["base_url"]
        
        return flat

    def prepare_field_value(
        self, field: FieldInfo, field_name: str, value: Any, value_is_complex: bool
    ) -> Any:
        return value

class Settings(BaseSettings):
    # Global / Auth
    API_KEY: str = "han1234"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"
    DATABASE_URL: Optional[str] = None 

    # Flow
    FLOW_LABS_BASE_URL: str = "https://labs.google/fx/api"
    FLOW_API_BASE_URL: str = "https://aisandbox-pa.googleapis.com/v1"
    FLOW_TIMEOUT: int = 120
    FLOW_POLL_INTERVAL: float = 3.0
    FLOW_MAX_POLL_ATTEMPTS: int = 200
    FLOW_MAX_RETRIES: int = 3

    # Server
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

    # Debug
    DEBUG_ENABLED: bool = False
    DEBUG_LOG_REQUESTS: bool = True
    DEBUG_LOG_RESPONSES: bool = True
    DEBUG_MASK_TOKEN: bool = True

    # Proxy
    PROXY_ENABLED: bool = False
    PROXY_URL: Optional[str] = None

    # Generation
    GENERATION_IMAGE_TIMEOUT: int = 300
    GENERATION_VIDEO_TIMEOUT: int = 1500

    # Admin
    ADMIN_ERROR_BAN_THRESHOLD: int = 3

    # Cache
    CACHE_ENABLED: bool = False
    CACHE_TIMEOUT: int = 7200
    CACHE_BASE_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True
    )

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
            file_secret_settings,
        )

    def to_legacy_dict(self) -> Dict[str, Any]:
        """Return a dictionary matching the legacy TOML structure."""
        return {
            "global": {
                "api_key": self.API_KEY,
                "admin_username": self.ADMIN_USERNAME,
                "admin_password": self.ADMIN_PASSWORD,
            },
            "flow": {
                "labs_base_url": self.FLOW_LABS_BASE_URL,
                "api_base_url": self.FLOW_API_BASE_URL,
                "timeout": self.FLOW_TIMEOUT,
                "poll_interval": self.FLOW_POLL_INTERVAL,
                "max_poll_attempts": self.FLOW_MAX_POLL_ATTEMPTS,
                "max_retries": self.FLOW_MAX_RETRIES,
            },
            "server": {
                "host": self.SERVER_HOST,
                "port": self.SERVER_PORT,
            },
            "debug": {
                "enabled": self.DEBUG_ENABLED,
                "log_requests": self.DEBUG_LOG_REQUESTS,
                "log_responses": self.DEBUG_LOG_RESPONSES,
                "mask_token": self.DEBUG_MASK_TOKEN,
            },
            "proxy": {
                "proxy_enabled": self.PROXY_ENABLED,
                "proxy_url": self.PROXY_URL or "",
            },
            "generation": {
                "image_timeout": self.GENERATION_IMAGE_TIMEOUT,
                "video_timeout": self.GENERATION_VIDEO_TIMEOUT,
            },
            "admin": {
                "error_ban_threshold": self.ADMIN_ERROR_BAN_THRESHOLD,
            },
            "cache": {
                "enabled": self.CACHE_ENABLED,
                "timeout": self.CACHE_TIMEOUT,
                "base_url": self.CACHE_BASE_URL or "",
            },
        }

settings = Settings()
