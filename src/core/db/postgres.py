import json
from datetime import datetime, date
from typing import Optional, List, Any
import asyncio

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from sqlalchemy.engine import Result

from ..models import (
    Token, TokenStats, Task, RequestLog, 
    AdminConfig, ProxyConfig, GenerationConfig, 
    CacheConfig, Project, DebugConfig
)
from .base import DatabaseAdapter

class PostgresAdapter(DatabaseAdapter):
    """Postgres database manager using SQLAlchemy"""

    def __init__(self, db_url: str):
        self.engine = create_async_engine(db_url)
    
    async def is_initialized(self) -> bool:
        """Check if database is initialized (tables exist)"""
        async with self.engine.connect() as conn:
            return await self._table_exists(conn, "tokens")

    async def init_db(self):
        """Initialize database tables"""
        async with self.engine.begin() as conn:
            # Tokens table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS tokens (
                    id SERIAL PRIMARY KEY,
                    st TEXT UNIQUE NOT NULL,
                    at TEXT,
                    at_expires TIMESTAMP,
                    email TEXT NOT NULL,
                    name TEXT,
                    remark TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TIMESTAMP,
                    use_count INTEGER DEFAULT 0,
                    credits INTEGER DEFAULT 0,
                    user_paygate_tier TEXT,
                    current_project_id TEXT,
                    current_project_name TEXT,
                    image_enabled BOOLEAN DEFAULT TRUE,
                    video_enabled BOOLEAN DEFAULT TRUE,
                    image_concurrency INTEGER DEFAULT -1,
                    video_concurrency INTEGER DEFAULT -1
                )
            """))

            # Projects table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS projects (
                    id SERIAL PRIMARY KEY,
                    project_id TEXT UNIQUE NOT NULL,
                    token_id INTEGER NOT NULL REFERENCES tokens(id),
                    project_name TEXT NOT NULL,
                    tool_name TEXT DEFAULT 'PINHOLE',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Token stats table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS token_stats (
                    id SERIAL PRIMARY KEY,
                    token_id INTEGER NOT NULL REFERENCES tokens(id),
                    image_count INTEGER DEFAULT 0,
                    video_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    last_success_at TIMESTAMP,
                    last_error_at TIMESTAMP,
                    today_image_count INTEGER DEFAULT 0,
                    today_video_count INTEGER DEFAULT 0,
                    today_error_count INTEGER DEFAULT 0,
                    today_date DATE,
                    consecutive_error_count INTEGER DEFAULT 0
                )
            """))

            # Tasks table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    task_id TEXT UNIQUE NOT NULL,
                    token_id INTEGER NOT NULL REFERENCES tokens(id),
                    model TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'processing',
                    progress INTEGER DEFAULT 0,
                    result_urls TEXT,
                    error_message TEXT,
                    scene_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """))

            # Request logs table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS request_logs (
                    id SERIAL PRIMARY KEY,
                    token_id INTEGER REFERENCES tokens(id),
                    operation TEXT NOT NULL,
                    request_body TEXT,
                    response_body TEXT,
                    status_code INTEGER NOT NULL,
                    duration FLOAT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Admin config table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS admin_config (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    username TEXT DEFAULT 'admin',
                    password TEXT DEFAULT 'admin',
                    api_key TEXT DEFAULT 'han1234',
                    error_ban_threshold INTEGER DEFAULT 3,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Proxy config table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS proxy_config (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    enabled BOOLEAN DEFAULT FALSE,
                    proxy_url TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Generation config table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS generation_config (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    image_timeout INTEGER DEFAULT 300,
                    video_timeout INTEGER DEFAULT 1500,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Cache config table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS cache_config (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    cache_enabled BOOLEAN DEFAULT FALSE,
                    cache_timeout INTEGER DEFAULT 7200,
                    cache_base_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Debug config table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS debug_config (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    enabled BOOLEAN DEFAULT FALSE,
                    log_requests BOOLEAN DEFAULT TRUE,
                    log_responses BOOLEAN DEFAULT TRUE,
                    mask_token BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Create indexes
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_task_id ON tasks(task_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_token_st ON tokens(st)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_project_id ON projects(project_id)"))

    async def _table_exists(self, conn, table_name: str) -> bool:
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :table_name)"
        ), {"table_name": table_name})
        return result.scalar()

    async def _column_exists(self, conn, table_name: str, column_name: str) -> bool:
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = :table_name AND column_name = :column_name)"
        ), {"table_name": table_name, "column_name": column_name})
        return result.scalar()

    async def _ensure_config_rows(self, conn, config_dict: dict = None):
        """Ensure all config tables have their default rows"""
        
        # Admin config
        result = await conn.execute(text("SELECT COUNT(*) FROM admin_config"))
        if result.scalar() == 0:
            admin_username = "admin"
            admin_password = "admin"
            api_key = "han1234"
            error_ban_threshold = 3

            if config_dict:
                global_config = config_dict.get("global", {})
                admin_username = global_config.get("admin_username", "admin")
                admin_password = global_config.get("admin_password", "admin")
                api_key = global_config.get("api_key", "han1234")

                admin_config = config_dict.get("admin", {})
                error_ban_threshold = admin_config.get("error_ban_threshold", 3)

            await conn.execute(text("""
                INSERT INTO admin_config (id, username, password, api_key, error_ban_threshold)
                VALUES (1, :u, :p, :k, :e)
            """), {"u": admin_username, "p": admin_password, "k": api_key, "e": error_ban_threshold})

        # Proxy config
        result = await conn.execute(text("SELECT COUNT(*) FROM proxy_config"))
        if result.scalar() == 0:
            proxy_enabled = False
            proxy_url = None

            if config_dict:
                proxy_config = config_dict.get("proxy", {})
                proxy_enabled = proxy_config.get("proxy_enabled", False)
                proxy_url = proxy_config.get("proxy_url", "") or None

            await conn.execute(text("""
                INSERT INTO proxy_config (id, enabled, proxy_url)
                VALUES (1, :e, :u)
            """), {"e": proxy_enabled, "u": proxy_url})

        # Generation config
        result = await conn.execute(text("SELECT COUNT(*) FROM generation_config"))
        if result.scalar() == 0:
            image_timeout = 300
            video_timeout = 1500

            if config_dict:
                generation_config = config_dict.get("generation", {})
                image_timeout = generation_config.get("image_timeout", 300)
                video_timeout = generation_config.get("video_timeout", 1500)

            await conn.execute(text("""
                INSERT INTO generation_config (id, image_timeout, video_timeout)
                VALUES (1, :i, :v)
            """), {"i": image_timeout, "v": video_timeout})

        # Cache config
        result = await conn.execute(text("SELECT COUNT(*) FROM cache_config"))
        if result.scalar() == 0:
            cache_enabled = False
            cache_timeout = 7200
            cache_base_url = None

            if config_dict:
                cache_config = config_dict.get("cache", {})
                cache_enabled = cache_config.get("enabled", False)
                cache_timeout = cache_config.get("timeout", 7200)
                cache_base_url = cache_config.get("base_url", "") or None

            await conn.execute(text("""
                INSERT INTO cache_config (id, cache_enabled, cache_timeout, cache_base_url)
                VALUES (1, :e, :t, :u)
            """), {"e": cache_enabled, "t": cache_timeout, "u": cache_base_url})

        # Debug config
        result = await conn.execute(text("SELECT COUNT(*) FROM debug_config"))
        if result.scalar() == 0:
            debug_enabled = False
            log_requests = True
            log_responses = True
            mask_token = True

            if config_dict:
                debug_config = config_dict.get("debug", {})
                debug_enabled = debug_config.get("enabled", False)
                log_requests = debug_config.get("log_requests", True)
                log_responses = debug_config.get("log_responses", True)
                mask_token = debug_config.get("mask_token", True)

            await conn.execute(text("""
                INSERT INTO debug_config (id, enabled, log_requests, log_responses, mask_token)
                VALUES (1, :e, :lr, :lrs, :m)
            """), {"e": debug_enabled, "lr": log_requests, "lrs": log_responses, "m": mask_token})

    async def check_and_migrate_db(self, config_dict: dict = None):
        """Check database integrity and perform migrations if needed"""
        async with self.engine.begin() as conn:
            print("Checking database integrity and performing migrations (Postgres)...")

            # Create missing tables
            if not await self._table_exists(conn, "cache_config"):
                print("  ✓ Creating missing table: cache_config")
                await conn.execute(text("""
                    CREATE TABLE cache_config (
                        id INTEGER PRIMARY KEY DEFAULT 1,
                        cache_enabled BOOLEAN DEFAULT FALSE,
                        cache_timeout INTEGER DEFAULT 7200,
                        cache_base_url TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            
            # Check and add missing columns to tokens table
            if await self._table_exists(conn, "tokens"):
                columns_to_add = [
                    ("at", "TEXT"),
                    ("at_expires", "TIMESTAMP"),
                    ("credits", "INTEGER DEFAULT 0"),
                    ("user_paygate_tier", "TEXT"),
                    ("current_project_id", "TEXT"),
                    ("current_project_name", "TEXT"),
                    ("image_enabled", "BOOLEAN DEFAULT TRUE"),
                    ("video_enabled", "BOOLEAN DEFAULT TRUE"),
                    ("image_concurrency", "INTEGER DEFAULT -1"),
                    ("video_concurrency", "INTEGER DEFAULT -1"),
                ]

                for col_name, col_type in columns_to_add:
                    if not await self._column_exists(conn, "tokens", col_name):
                        try:
                            await conn.execute(text(f"ALTER TABLE tokens ADD COLUMN {col_name} {col_type}"))
                            print(f"  ✓ Added column '{col_name}' to tokens table")
                        except Exception as e:
                            print(f"  ✗ Failed to add column '{col_name}': {e}")

            # Check and add missing columns to admin_config table
            if await self._table_exists(conn, "admin_config"):
                if not await self._column_exists(conn, "admin_config", "error_ban_threshold"):
                    try:
                        await conn.execute(text("ALTER TABLE admin_config ADD COLUMN error_ban_threshold INTEGER DEFAULT 3"))
                        print("  ✓ Added column 'error_ban_threshold' to admin_config table")
                    except Exception as e:
                        print(f"  ✗ Failed to add column 'error_ban_threshold': {e}")
            
            # Check and add missing columns to token_stats table
            if await self._table_exists(conn, "token_stats"):
                stats_columns_to_add = [
                    ("today_image_count", "INTEGER DEFAULT 0"),
                    ("today_video_count", "INTEGER DEFAULT 0"),
                    ("today_error_count", "INTEGER DEFAULT 0"),
                    ("today_date", "DATE"),
                    ("consecutive_error_count", "INTEGER DEFAULT 0"),
                ]

                for col_name, col_type in stats_columns_to_add:
                    if not await self._column_exists(conn, "token_stats", col_name):
                        try:
                            await conn.execute(text(f"ALTER TABLE token_stats ADD COLUMN {col_name} {col_type}"))
                            print(f"  ✓ Added column '{col_name}' to token_stats table")
                        except Exception as e:
                            print(f"  ✗ Failed to add column '{col_name}': {e}")

            # Ensure config rows
            await self._ensure_config_rows(conn, config_dict=None)
            print("Database migration check completed.")

    async def init_config_from_toml(self, config_dict: dict, is_first_startup: bool = True):
        async with self.engine.begin() as conn:
            if is_first_startup:
                await self._ensure_config_rows(conn, config_dict)
            else:
                await self._ensure_config_rows(conn, config_dict=None)

    async def reload_config_to_memory(self):
        from ..config import config

        admin_config = await self.get_admin_config()
        if admin_config:
            config.set_admin_username_from_db(admin_config.username)
            config.set_admin_password_from_db(admin_config.password)
            config.api_key = admin_config.api_key

        cache_config = await self.get_cache_config()
        if cache_config:
            config.set_cache_enabled(cache_config.cache_enabled)
            config.set_cache_timeout(cache_config.cache_timeout)
            config.set_cache_base_url(cache_config.cache_base_url or "")

        generation_config = await self.get_generation_config()
        if generation_config:
            config.set_image_timeout(generation_config.image_timeout)
            config.set_video_timeout(generation_config.video_timeout)

        debug_config = await self.get_debug_config()
        if debug_config:
            config.set_debug_enabled(debug_config.enabled)

    @property
    def async_session(self):
        from sqlalchemy.ext.asyncio import async_sessionmaker
        return async_sessionmaker(self.engine, expire_on_commit=False)

    # Token operations
    async def add_token(self, token: Token) -> int:
        """Add a new token"""
        async with self.async_session() as session:
            async with session.begin():
                # Using model_dump to get dictionary, but need to ensure keys match
                params = token.model_dump()
                result = await session.execute(text("""
                    INSERT INTO tokens (st, at, at_expires, email, name, remark, is_active,
                                       credits, user_paygate_tier, current_project_id, current_project_name,
                                       image_enabled, video_enabled, image_concurrency, video_concurrency)
                    VALUES (:st, :at, :at_expires, :email, :name, :remark, :is_active,
                            :credits, :user_paygate_tier, :current_project_id, :current_project_name,
                            :image_enabled, :video_enabled, :image_concurrency, :video_concurrency)
                    RETURNING id
                """), params)
                token_id = result.scalar()

                await session.execute(text("""
                    INSERT INTO token_stats (token_id) VALUES (:token_id)
                """), {"token_id": token_id})
                
                return token_id

    async def get_token(self, token_id: int) -> Optional[Token]:
        """Get token by ID"""
        async with self.engine.connect() as conn:
            result = await conn.execute(text("SELECT * FROM tokens WHERE id = :id"), {"id": token_id})
            row = result.mappings().fetchone()
            if row:
                return Token(**dict(row))
            return None

    async def get_token_by_st(self, st: str) -> Optional[Token]:
        """Get token by ST"""
        async with self.engine.connect() as conn:
            result = await conn.execute(text("SELECT * FROM tokens WHERE st = :st"), {"st": st})
            row = result.mappings().fetchone()
            if row:
                return Token(**dict(row))
            return None

    async def get_all_tokens(self) -> List[Token]:
        """Get all tokens"""
        async with self.engine.connect() as conn:
            result = await conn.execute(text("SELECT * FROM tokens ORDER BY created_at DESC"))
            rows = result.mappings().fetchall()
            return [Token(**dict(row)) for row in rows]

    async def get_active_tokens(self) -> List[Token]:
        """Get all active tokens"""
        async with self.engine.connect() as conn:
            result = await conn.execute(text("SELECT * FROM tokens WHERE is_active = TRUE ORDER BY last_used_at ASC"))
            rows = result.mappings().fetchall()
            return [Token(**dict(row)) for row in rows]

    async def update_token(self, token_id: int, **kwargs):
        """Update token fields"""
        async with self.async_session() as session:
            async with session.begin():
                updates = []
                params = {"token_id": token_id}

                for key, value in kwargs.items():
                    if value is not None:
                        updates.append(f"{key} = :{key}")
                        params[key] = value

                if updates:
                    query = f"UPDATE tokens SET {', '.join(updates)} WHERE id = :token_id"
                    await session.execute(text(query), params)

    async def delete_token(self, token_id: int):
        """Delete token and related data"""
        async with self.async_session() as session:
            async with session.begin():
                await session.execute(text("DELETE FROM token_stats WHERE token_id = :id"), {"id": token_id})
                await session.execute(text("DELETE FROM projects WHERE token_id = :id"), {"id": token_id})
                await session.execute(text("DELETE FROM tokens WHERE id = :id"), {"id": token_id})

    # Project operations
    async def add_project(self, project: Project) -> int:
        """Add a new project"""
        async with self.async_session() as session:
            async with session.begin():
                params = project.model_dump()
                result = await session.execute(text("""
                    INSERT INTO projects (project_id, token_id, project_name, tool_name, is_active)
                    VALUES (:project_id, :token_id, :project_name, :tool_name, :is_active)
                    RETURNING id
                """), params)
                return result.scalar()

    async def get_project_by_id(self, project_id: str) -> Optional[Project]:
        """Get project by UUID"""
        async with self.engine.connect() as conn:
            result = await conn.execute(text("SELECT * FROM projects WHERE project_id = :pid"), {"pid": project_id})
            row = result.mappings().fetchone()
            if row:
                return Project(**dict(row))
            return None

    async def get_projects_by_token(self, token_id: int) -> List[Project]:
        """Get all projects for a token"""
        async with self.engine.connect() as conn:
            result = await conn.execute(text(
                "SELECT * FROM projects WHERE token_id = :tid ORDER BY created_at DESC"
            ), {"tid": token_id})
            rows = result.mappings().fetchall()
            return [Project(**dict(row)) for row in rows]

    async def delete_project(self, project_id: str):
        """Delete project"""
        async with self.async_session() as session:
            async with session.begin():
                await session.execute(text("DELETE FROM projects WHERE project_id = :pid"), {"pid": project_id})

    # Task operations
    async def create_task(self, task: Task) -> int:
        """Create a new task"""
        async with self.async_session() as session:
            async with session.begin():
                params = task.model_dump()
                # result_urls is usually None at creation or handled by Task model dump
                if isinstance(params.get("result_urls"), list):
                    params["result_urls"] = json.dumps(params["result_urls"])
                
                result = await session.execute(text("""
                    INSERT INTO tasks (task_id, token_id, model, prompt, status, progress, scene_id, result_urls, error_message)
                    VALUES (:task_id, :token_id, :model, :prompt, :status, :progress, :scene_id, :result_urls, :error_message)
                    RETURNING id
                """), params)
                return result.scalar()

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        async with self.engine.connect() as conn:
            result = await conn.execute(text("SELECT * FROM tasks WHERE task_id = :tid"), {"tid": task_id})
            row = result.mappings().fetchone()
            if row:
                task_dict = dict(row)
                if task_dict.get("result_urls"):
                    try:
                        task_dict["result_urls"] = json.loads(task_dict["result_urls"])
                    except:
                        pass # Keep as string if not valid JSON
                return Task(**task_dict)
            return None

    async def update_task(self, task_id: str, **kwargs):
        """Update task"""
        async with self.async_session() as session:
            async with session.begin():
                updates = []
                params = {"task_id": task_id}

                for key, value in kwargs.items():
                    if value is not None:
                        if key == "result_urls" and isinstance(value, list):
                            value = json.dumps(value)
                        
                        updates.append(f"{key} = :{key}")
                        params[key] = value

                if updates:
                    query = f"UPDATE tasks SET {', '.join(updates)} WHERE task_id = :task_id"
                    await session.execute(text(query), params)

    # Token stats operations
    async def increment_token_stats(self, token_id: int, stat_type: str):
        """Increment token statistics"""
        if stat_type == "image":
            await self.increment_image_count(token_id)
        elif stat_type == "video":
            await self.increment_video_count(token_id)
        elif stat_type == "error":
            await self.increment_error_count(token_id)

    async def get_token_stats(self, token_id: int) -> Optional[TokenStats]:
        """Get token statistics"""
        async with self.engine.connect() as conn:
            result = await conn.execute(text("SELECT * FROM token_stats WHERE token_id = :tid"), {"tid": token_id})
            row = result.mappings().fetchone()
            if row:
                return TokenStats(**dict(row))
            return None
    
    async def increment_image_count(self, token_id: int):
        """Increment image generation count with daily reset"""
        today = date.today()
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(text(
                    "SELECT today_date FROM token_stats WHERE token_id = :tid FOR UPDATE"
                ), {"tid": token_id})
                row = result.fetchone()

                if row and row[0] != today:
                    await session.execute(text("""
                        UPDATE token_stats
                        SET image_count = image_count + 1,
                            today_image_count = 1,
                            today_date = :today
                        WHERE token_id = :tid
                    """), {"today": today, "tid": token_id})
                else:
                    await session.execute(text("""
                        UPDATE token_stats
                        SET image_count = image_count + 1,
                            today_image_count = today_image_count + 1,
                            today_date = :today
                        WHERE token_id = :tid
                    """), {"today": today, "tid": token_id})

    async def increment_video_count(self, token_id: int):
        """Increment video generation count with daily reset"""
        today = date.today()
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(text(
                    "SELECT today_date FROM token_stats WHERE token_id = :tid FOR UPDATE"
                ), {"tid": token_id})
                row = result.fetchone()

                if row and row[0] != today:
                    await session.execute(text("""
                        UPDATE token_stats
                        SET video_count = video_count + 1,
                            today_video_count = 1,
                            today_date = :today
                        WHERE token_id = :tid
                    """), {"today": today, "tid": token_id})
                else:
                    await session.execute(text("""
                        UPDATE token_stats
                        SET video_count = video_count + 1,
                            today_video_count = today_video_count + 1,
                            today_date = :today
                        WHERE token_id = :tid
                    """), {"today": today, "tid": token_id})

    async def increment_error_count(self, token_id: int):
        """Increment error count with daily reset"""
        today = date.today()
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(text(
                    "SELECT today_date FROM token_stats WHERE token_id = :tid FOR UPDATE"
                ), {"tid": token_id})
                row = result.fetchone()

                if row and row[0] != today:
                    await session.execute(text("""
                        UPDATE token_stats
                        SET error_count = error_count + 1,
                            consecutive_error_count = consecutive_error_count + 1,
                            today_error_count = 1,
                            today_date = :today,
                            last_error_at = CURRENT_TIMESTAMP
                        WHERE token_id = :tid
                    """), {"today": today, "tid": token_id})
                else:
                    await session.execute(text("""
                        UPDATE token_stats
                        SET error_count = error_count + 1,
                            consecutive_error_count = consecutive_error_count + 1,
                            today_error_count = today_error_count + 1,
                            today_date = :today,
                            last_error_at = CURRENT_TIMESTAMP
                        WHERE token_id = :tid
                    """), {"today": today, "tid": token_id})

    async def reset_error_count(self, token_id: int):
        """Reset consecutive error count"""
        async with self.async_session() as session:
            async with session.begin():
                await session.execute(text(
                    "UPDATE token_stats SET consecutive_error_count = 0 WHERE token_id = :tid"
                ), {"tid": token_id})

    # Config operations
    async def get_admin_config(self) -> Optional[AdminConfig]:
        """Get admin configuration"""
        async with self.engine.connect() as conn:
            result = await conn.execute(text("SELECT * FROM admin_config WHERE id = 1"))
            row = result.mappings().fetchone()
            if row:
                return AdminConfig(**dict(row))
            return None

    async def update_admin_config(self, **kwargs):
        """Update admin configuration"""
        async with self.async_session() as session:
            async with session.begin():
                updates = []
                params = {"id": 1}

                for key, value in kwargs.items():
                    if value is not None:
                        updates.append(f"{key} = :{key}")
                        params[key] = value

                if updates:
                    updates.append("updated_at = CURRENT_TIMESTAMP")
                    query = f"UPDATE admin_config SET {', '.join(updates)} WHERE id = :id"
                    await session.execute(text(query), params)

    async def get_proxy_config(self) -> Optional[ProxyConfig]:
        """Get proxy configuration"""
        async with self.engine.connect() as conn:
            result = await conn.execute(text("SELECT * FROM proxy_config WHERE id = 1"))
            row = result.mappings().fetchone()
            if row:
                return ProxyConfig(**dict(row))
            return None

    async def update_proxy_config(self, enabled: bool, proxy_url: Optional[str] = None):
        """Update proxy configuration"""
        async with self.async_session() as session:
            async with session.begin():
                await session.execute(text("""
                    UPDATE proxy_config
                    SET enabled = :enabled, proxy_url = :url, updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                """), {"enabled": enabled, "url": proxy_url})

    async def get_generation_config(self) -> Optional[GenerationConfig]:
        """Get generation configuration"""
        async with self.engine.connect() as conn:
            result = await conn.execute(text("SELECT * FROM generation_config WHERE id = 1"))
            row = result.mappings().fetchone()
            if row:
                return GenerationConfig(**dict(row))
            return None

    async def update_generation_config(self, image_timeout: int, video_timeout: int):
        """Update generation configuration"""
        async with self.async_session() as session:
            async with session.begin():
                await session.execute(text("""
                    UPDATE generation_config
                    SET image_timeout = :it, video_timeout = :vt, updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                """), {"it": image_timeout, "vt": video_timeout})

    async def get_cache_config(self) -> CacheConfig:
        """Get cache configuration"""
        async with self.engine.connect() as conn:
            result = await conn.execute(text("SELECT * FROM cache_config WHERE id = 1"))
            row = result.mappings().fetchone()
            if row:
                return CacheConfig(**dict(row))
            return CacheConfig(cache_enabled=False, cache_timeout=7200)

    async def update_cache_config(self, enabled: bool = None, timeout: int = None, base_url: Optional[str] = None):
        """Update cache configuration"""
        async with self.async_session() as session:
            async with session.begin():
                # Select for update to handle read-modify-write if row exists
                # But here we just want to update fields if provided.
                
                # We can't easily do partial update without reading first unless we build dynamic query.
                # Or we can do `COALESCE(:val, column)` trick if we pass NULL for unset values.
                # But implementation in SQLite was: read existing, merge, update.
                
                result = await session.execute(text("SELECT * FROM cache_config WHERE id = 1 FOR UPDATE"))
                row = result.mappings().fetchone()
                
                if row:
                    current = dict(row)
                    new_enabled = enabled if enabled is not None else current.get("cache_enabled", False)
                    new_timeout = timeout if timeout is not None else current.get("cache_timeout", 7200)
                    new_base_url = base_url if base_url is not None else current.get("cache_base_url")
                    
                    if base_url == "":
                        new_base_url = None
                    
                    await session.execute(text("""
                        UPDATE cache_config
                        SET cache_enabled = :e, cache_timeout = :t, cache_base_url = :u, updated_at = CURRENT_TIMESTAMP
                        WHERE id = 1
                    """), {"e": new_enabled, "t": new_timeout, "u": new_base_url})
                else:
                    new_enabled = enabled if enabled is not None else False
                    new_timeout = timeout if timeout is not None else 7200
                    new_base_url = base_url if base_url is not None else None
                    
                    await session.execute(text("""
                        INSERT INTO cache_config (id, cache_enabled, cache_timeout, cache_base_url)
                        VALUES (1, :e, :t, :u)
                    """), {"e": new_enabled, "t": new_timeout, "u": new_base_url})

    async def get_debug_config(self) -> Optional[DebugConfig]:
        """Get debug configuration"""
        async with self.engine.connect() as conn:
            result = await conn.execute(text("SELECT * FROM debug_config WHERE id = 1"))
            row = result.mappings().fetchone()
            if row:
                return DebugConfig(**dict(row))
            return DebugConfig(enabled=False, log_requests=True, log_responses=True, mask_token=True)

    async def update_debug_config(self, **kwargs):
        """Update debug configuration"""
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(text("SELECT * FROM debug_config WHERE id = 1 FOR UPDATE"))
                row = result.mappings().fetchone()

                if row:
                    current = dict(row)
                    new_enabled = kwargs.get("enabled") if kwargs.get("enabled") is not None else current.get("enabled", False)
                    new_log_requests = kwargs.get("log_requests") if kwargs.get("log_requests") is not None else current.get("log_requests", True)
                    new_log_responses = kwargs.get("log_responses") if kwargs.get("log_responses") is not None else current.get("log_responses", True)
                    new_mask_token = kwargs.get("mask_token") if kwargs.get("mask_token") is not None else current.get("mask_token", True)
                    
                    await session.execute(text("""
                        UPDATE debug_config
                        SET enabled = :e, log_requests = :lr, log_responses = :lrs, mask_token = :m, updated_at = CURRENT_TIMESTAMP
                        WHERE id = 1
                    """), {"e": new_enabled, "lr": new_log_requests, "lrs": new_log_responses, "m": new_mask_token})
                else:
                     # Insert default if missing
                    new_enabled = kwargs.get("enabled", False)
                    new_log_requests = kwargs.get("log_requests", True)
                    new_log_responses = kwargs.get("log_responses", True)
                    new_mask_token = kwargs.get("mask_token", True)

                    await session.execute(text("""
                        INSERT INTO debug_config (id, enabled, log_requests, log_responses, mask_token)
                        VALUES (1, :e, :lr, :lrs, :m)
                    """), {"e": new_enabled, "lr": new_log_requests, "lrs": new_log_responses, "m": new_mask_token})

    # Request log operations
    async def add_request_log(self, log: RequestLog):
        """Add request log"""
        async with self.async_session() as session:
            async with session.begin():
                await session.execute(text("""
                    INSERT INTO request_logs (token_id, operation, request_body, response_body, status_code, duration)
                    VALUES (:token_id, :operation, :request_body, :response_body, :status_code, :duration)
                """), {
                    "token_id": log.token_id,
                    "operation": log.operation,
                    "request_body": log.request_body,
                    "response_body": log.response_body,
                    "status_code": log.status_code,
                    "duration": log.duration
                })

    async def get_logs(self, limit: int = 100, token_id: Optional[int] = None):
        """Get request logs"""
        async with self.engine.connect() as conn:
            if token_id:
                result = await conn.execute(text("""
                    SELECT
                        rl.id,
                        rl.token_id,
                        rl.operation,
                        rl.request_body,
                        rl.response_body,
                        rl.status_code,
                        rl.duration,
                        rl.created_at,
                        t.email as token_email,
                        t.name as token_username
                    FROM request_logs rl
                    LEFT JOIN tokens t ON rl.token_id = t.id
                    WHERE rl.token_id = :tid
                    ORDER BY rl.created_at DESC
                    LIMIT :limit
                """), {"tid": token_id, "limit": limit})
            else:
                result = await conn.execute(text("""
                    SELECT
                        rl.id,
                        rl.token_id,
                        rl.operation,
                        rl.request_body,
                        rl.response_body,
                        rl.status_code,
                        rl.duration,
                        rl.created_at,
                        t.email as token_email,
                        t.name as token_username
                    FROM request_logs rl
                    LEFT JOIN tokens t ON rl.token_id = t.id
                    ORDER BY rl.created_at DESC
                    LIMIT :limit
                """), {"limit": limit})
            
            rows = result.mappings().fetchall()
            return [dict(row) for row in rows]
