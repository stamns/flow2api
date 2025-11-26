from abc import ABC, abstractmethod
from typing import Optional, List, Any, Dict
from ..models import (
    Token, TokenStats, Task, RequestLog, 
    AdminConfig, ProxyConfig, GenerationConfig, 
    CacheConfig, DebugConfig, Project
)

class DatabaseAdapter(ABC):
    """Abstract base class for database adapters"""

    @abstractmethod
    async def is_initialized(self) -> bool:
        """Check if database is initialized (tables exist)"""
        pass

    @abstractmethod
    async def init_db(self):
        """Initialize database tables"""
        pass

    @abstractmethod
    async def check_and_migrate_db(self, config_dict: dict = None):
        """Check database integrity and perform migrations if needed"""
        pass
    
    @abstractmethod
    async def init_config_from_toml(self, config_dict: dict, is_first_startup: bool = True):
        """Initialize database configuration from setting.toml"""
        pass

    @abstractmethod
    async def reload_config_to_memory(self):
        """Reload all configuration from database to in-memory Config instance"""
        pass

    # Token operations
    @abstractmethod
    async def add_token(self, token: Token) -> int:
        pass

    @abstractmethod
    async def get_token(self, token_id: int) -> Optional[Token]:
        pass

    @abstractmethod
    async def get_token_by_st(self, st: str) -> Optional[Token]:
        pass

    @abstractmethod
    async def get_all_tokens(self) -> List[Token]:
        pass

    @abstractmethod
    async def get_active_tokens(self) -> List[Token]:
        pass

    @abstractmethod
    async def update_token(self, token_id: int, **kwargs):
        pass

    @abstractmethod
    async def delete_token(self, token_id: int):
        pass

    # Project operations
    @abstractmethod
    async def add_project(self, project: Project) -> int:
        pass

    @abstractmethod
    async def get_project_by_id(self, project_id: str) -> Optional[Project]:
        pass

    @abstractmethod
    async def get_projects_by_token(self, token_id: int) -> List[Project]:
        pass

    @abstractmethod
    async def delete_project(self, project_id: str):
        pass

    # Task operations
    @abstractmethod
    async def create_task(self, task: Task) -> int:
        pass

    @abstractmethod
    async def get_task(self, task_id: str) -> Optional[Task]:
        pass

    @abstractmethod
    async def update_task(self, task_id: str, **kwargs):
        pass

    # Token stats operations
    @abstractmethod
    async def increment_token_stats(self, token_id: int, stat_type: str):
        pass

    @abstractmethod
    async def get_token_stats(self, token_id: int) -> Optional[TokenStats]:
        pass
    
    @abstractmethod
    async def increment_image_count(self, token_id: int):
        pass

    @abstractmethod
    async def increment_video_count(self, token_id: int):
        pass

    @abstractmethod
    async def increment_error_count(self, token_id: int):
        pass

    @abstractmethod
    async def reset_error_count(self, token_id: int):
        pass

    # Config operations
    @abstractmethod
    async def get_admin_config(self) -> Optional[AdminConfig]:
        pass

    @abstractmethod
    async def update_admin_config(self, **kwargs):
        pass

    @abstractmethod
    async def get_proxy_config(self) -> Optional[ProxyConfig]:
        pass

    @abstractmethod
    async def update_proxy_config(self, enabled: bool, proxy_url: Optional[str] = None):
        pass

    @abstractmethod
    async def get_generation_config(self) -> Optional[GenerationConfig]:
        pass

    @abstractmethod
    async def update_generation_config(self, image_timeout: int, video_timeout: int):
        pass

    @abstractmethod
    async def get_cache_config(self) -> CacheConfig:
        pass

    @abstractmethod
    async def update_cache_config(self, enabled: bool = None, timeout: int = None, base_url: Optional[str] = None):
        pass

    @abstractmethod
    async def get_debug_config(self) -> Optional[DebugConfig]:
        pass

    @abstractmethod
    async def update_debug_config(self, **kwargs):
        pass

    # Request log operations
    @abstractmethod
    async def add_request_log(self, log: RequestLog):
        pass

    @abstractmethod
    async def get_logs(self, limit: int = 100, token_id: Optional[int] = None):
        pass
