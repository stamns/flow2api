from typing import Any, Dict, Tuple, Type, Optional
from pathlib import Path
import tomli
from pydantic.fields import FieldInfo
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

class TomlConfigSettingsSource(PydanticBaseSettingsSource):
    """
    A settings source class that loads variables from a TOML file
    at the project's root (config/setting.toml).
    """
    def __call__(self) -> Dict[str, Any]:
        config_path = Path(__file__).parent.parent.parent / "config" / "setting.toml"
        
        if not config_path.exists():
             return {}
             
        try:
            with open(config_path, "rb") as f:
                file_content = tomli.load(f)
        except Exception:
            return {}
            
        return self._flatten_toml(file_content)

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
    API_KEY: str = Field(validation_alias=AliasChoices("api_key", "API_KEY"), default="han1234")
    ADMIN_USERNAME: str = Field(validation_alias=AliasChoices("admin_username", "ADMIN_USERNAME"), default="admin")
    ADMIN_PASSWORD: str = Field(validation_alias=AliasChoices("admin_password", "ADMIN_PASSWORD"), default="admin")
    DATABASE_URL: Optional[str] = None 

    # Flow
    FLOW_LABS_BASE_URL: str = Field(validation_alias=AliasChoices("flow_labs_base_url", "FLOW_LABS_BASE_URL"), default="https://labs.google/fx/api")
    FLOW_API_BASE_URL: str = Field(validation_alias=AliasChoices("flow_api_base_url", "FLOW_API_BASE_URL"), default="https://aisandbox-pa.googleapis.com/v1")
    FLOW_TIMEOUT: int = Field(validation_alias=AliasChoices("flow_timeout", "FLOW_TIMEOUT"), default=120)
    FLOW_POLL_INTERVAL: float = Field(validation_alias=AliasChoices("flow_poll_interval", "FLOW_POLL_INTERVAL"), default=3.0)
    FLOW_MAX_POLL_ATTEMPTS: int = Field(validation_alias=AliasChoices("flow_max_poll_attempts", "FLOW_MAX_POLL_ATTEMPTS"), default=200)
    FLOW_MAX_RETRIES: int = Field(default=3) 

    # Server
    SERVER_HOST: str = Field(validation_alias=AliasChoices("server_host", "SERVER_HOST"), default="0.0.0.0")
    SERVER_PORT: int = Field(validation_alias=AliasChoices("server_port", "SERVER_PORT"), default=8000)
    
    # Debug
    DEBUG_ENABLED: bool = Field(validation_alias=AliasChoices("debug_enabled", "DEBUG_ENABLED"), default=False)
    DEBUG_LOG_REQUESTS: bool = Field(validation_alias=AliasChoices("debug_log_requests", "DEBUG_LOG_REQUESTS"), default=True)
    DEBUG_LOG_RESPONSES: bool = Field(validation_alias=AliasChoices("debug_log_responses", "DEBUG_LOG_RESPONSES"), default=True)
    DEBUG_MASK_TOKEN: bool = Field(validation_alias=AliasChoices("debug_mask_token", "DEBUG_MASK_TOKEN"), default=True)
    
    # Proxy
    PROXY_ENABLED: bool = Field(validation_alias=AliasChoices("proxy_enabled", "PROXY_ENABLED"), default=False)
    PROXY_URL: Optional[str] = Field(validation_alias=AliasChoices("proxy_url", "PROXY_URL"), default="")
    
    # Generation
    GENERATION_IMAGE_TIMEOUT: int = Field(validation_alias=AliasChoices("generation_image_timeout", "GENERATION_IMAGE_TIMEOUT"), default=300)
    GENERATION_VIDEO_TIMEOUT: int = Field(validation_alias=AliasChoices("generation_video_timeout", "GENERATION_VIDEO_TIMEOUT"), default=1500)
    
    # Admin
    ADMIN_ERROR_BAN_THRESHOLD: int = Field(validation_alias=AliasChoices("admin_error_ban_threshold", "ADMIN_ERROR_BAN_THRESHOLD"), default=3)
    
    # Cache
    CACHE_ENABLED: bool = Field(validation_alias=AliasChoices("cache_enabled", "CACHE_ENABLED"), default=False)
    CACHE_TIMEOUT: int = Field(validation_alias=AliasChoices("cache_timeout", "CACHE_TIMEOUT"), default=7200)
    CACHE_BASE_URL: Optional[str] = Field(validation_alias=AliasChoices("cache_base_url", "CACHE_BASE_URL"), default="")

    # Storage
    STORAGE_BACKEND: str = Field(validation_alias=AliasChoices("storage_backend", "STORAGE_BACKEND"), default="local")
    S3_BUCKET_NAME: Optional[str] = Field(validation_alias=AliasChoices("s3_bucket_name", "S3_BUCKET_NAME"), default=None)
    S3_REGION_NAME: Optional[str] = Field(validation_alias=AliasChoices("s3_region_name", "S3_REGION_NAME"), default=None)
    S3_ENDPOINT_URL: Optional[str] = Field(validation_alias=AliasChoices("s3_endpoint_url", "S3_ENDPOINT_URL"), default=None)
    S3_ACCESS_KEY: Optional[str] = Field(validation_alias=AliasChoices("s3_access_key", "S3_ACCESS_KEY"), default=None)
    S3_SECRET_KEY: Optional[str] = Field(validation_alias=AliasChoices("s3_secret_key", "S3_SECRET_KEY"), default=None)
    S3_PUBLIC_DOMAIN: Optional[str] = Field(validation_alias=AliasChoices("s3_public_domain", "S3_PUBLIC_DOMAIN"), default=None)

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
            "storage": {
                "backend": self.STORAGE_BACKEND,
                "s3_bucket_name": self.S3_BUCKET_NAME,
                "s3_region_name": self.S3_REGION_NAME,
                "s3_endpoint_url": self.S3_ENDPOINT_URL,
                "s3_access_key": self.S3_ACCESS_KEY,
                "s3_secret_key": self.S3_SECRET_KEY,
                "s3_public_domain": self.S3_PUBLIC_DOMAIN,
            }
        }

settings = Settings()
