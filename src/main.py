"""FastAPI application initialization"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
import os

from .core.config import config
from .core.db.sqlite import SqliteAdapter
from .core.db.postgres import PostgresAdapter
from .services.flow_client import FlowClient
from .services.proxy_manager import ProxyManager
from .services.token_manager import TokenManager
from .services.load_balancer import LoadBalancer
from .services.concurrency_manager import ConcurrencyManager
from .services.generation_handler import GenerationHandler
from .api import routes, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("=" * 60)
    print("Flow2API Starting...")
    print("=" * 60)

    # Get config from setting.toml
    config_dict = config.get_raw_config()

    # Check if database exists (determine if first startup)
    is_first_startup = not await db.is_initialized()

    # Initialize database tables structure
    await db.init_db()

    # Handle database initialization based on startup type
    if is_first_startup:
        print("🎉 First startup detected. Initializing database and configuration from setting.toml...")
        await db.init_config_from_toml(config_dict, is_first_startup=True)
        print("✓ Database and configuration initialized successfully.")
    else:
        print("🔄 Existing database detected. Checking for missing tables and columns...")
        await db.check_and_migrate_db(config_dict)
        print("✓ Database migration check completed.")

    # Load admin config from database
    admin_config = await db.get_admin_config()
    if admin_config:
        config.set_admin_username_from_db(admin_config.username)
        config.set_admin_password_from_db(admin_config.password)
        config.api_key = admin_config.api_key
        config.set_error_ban_threshold(admin_config.error_ban_threshold)

    # Load cache configuration from database
    cache_config = await db.get_cache_config()
    if cache_config:
        config.set_cache_enabled(cache_config.cache_enabled)
        config.set_cache_timeout(cache_config.cache_timeout)
        config.set_cache_base_url(cache_config.cache_base_url or "")

    # Load generation configuration from database
    generation_config = await db.get_generation_config()
    if generation_config:
        config.set_image_timeout(generation_config.image_timeout)
        config.set_video_timeout(generation_config.video_timeout)

    # Load debug configuration from database
    debug_config = await db.get_debug_config()
    if debug_config:
        config.set_debug_enabled(debug_config.enabled)
        config.set_debug_log_requests(debug_config.log_requests)
        config.set_debug_log_responses(debug_config.log_responses)
        config.set_debug_mask_token(debug_config.mask_token)

    # Load proxy configuration from database
    proxy_config = await db.get_proxy_config()
    if proxy_config:
        config.set_proxy_enabled(proxy_config.enabled)
        config.set_proxy_url(proxy_config.proxy_url)

    # Initialize concurrency manager
    tokens = await token_manager.get_all_tokens()
    await concurrency_manager.initialize(tokens)

    # File cache cleanup is now manual/on-demand via purge endpoint
    # Start file cache cleanup task
    if not os.getenv("VERCEL"):
        await generation_handler.file_cache.start_cleanup_task()
        print(f"✓ File cache cleanup task started")
    else:
        print(f"✓ File cache cleanup task skipped (Vercel)")

    print(f"✓ Database initialized")
    print(f"✓ Total tokens: {len(tokens)}")
    print(f"✓ Cache: {'Enabled' if config.cache_enabled else 'Disabled'} (timeout: {config.cache_timeout}s)")
    print(f"✓ Storage Backend: {config.storage_backend}")
    print(f"✓ Server running on http://{config.server_host}:{config.server_port}")
    print("=" * 60)

    yield

    # Shutdown
    print("Flow2API Shutting down...")
    # Stop file cache cleanup task
    if not os.getenv("VERCEL"):
        await generation_handler.file_cache.stop_cleanup_task()
        print("✓ File cache cleanup task stopped")
    else:
        print("✓ File cache cleanup task stopped (Vercel)")


# Initialize components
if config.database_url and (config.database_url.startswith("postgres://") or config.database_url.startswith("postgresql://")):
    print(f"🔌 Using Postgres database")
    db = PostgresAdapter(config.database_url)
else:
    print("📂 Using SQLite database")
    db = SqliteAdapter()

db = Database()
proxy_manager = ProxyManager(db, config)
flow_client = FlowClient(proxy_manager, config)
db = Database(os.getenv("DATABASE_PATH"))
proxy_manager = ProxyManager(db)
flow_client = FlowClient(proxy_manager)
token_manager = TokenManager(db, flow_client)
concurrency_manager = ConcurrencyManager()
load_balancer = LoadBalancer(token_manager, concurrency_manager)
generation_handler = GenerationHandler(
    flow_client,
    token_manager,
    load_balancer,
    db,
    concurrency_manager,
    proxy_manager,
    config
)

# Set dependencies
routes.set_generation_handler(generation_handler)
admin.set_dependencies(token_manager, proxy_manager, db, generation_handler)
admin.set_dependencies(token_manager, proxy_manager, db, config)

# Create FastAPI app
app = FastAPI(
    title="Flow2API",
    description="OpenAI-compatible API for Google VideoFX (Veo)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes.router)
app.include_router(admin.router)

# Static files - serve tmp directory for cached files if using local backend
if config.storage_backend == "local":
    tmp_dir = Path(__file__).parent.parent / "tmp"
    tmp_dir.mkdir(exist_ok=True)
    app.mount("/tmp", StaticFiles(directory=str(tmp_dir)), name="tmp")
# Static files - serve tmp directory for cached files
if os.getenv("VERCEL"):
    tmp_dir = Path("/tmp")
else:
    tmp_dir = Path(__file__).parent.parent / "tmp"
tmp_dir.mkdir(exist_ok=True)
app.mount("/tmp", StaticFiles(directory=str(tmp_dir)), name="tmp")

# HTML routes for frontend
static_path = Path(__file__).parent.parent / "static"


@app.get("/", response_class=HTMLResponse)
async def index():
    """Redirect to login page"""
    login_file = static_path / "login.html"
    if login_file.exists():
        return FileResponse(str(login_file))
    return HTMLResponse(content="<h1>Flow2API</h1><p>Frontend not found</p>", status_code=404)


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Login page"""
    login_file = static_path / "login.html"
    if login_file.exists():
        return FileResponse(str(login_file))
    return HTMLResponse(content="<h1>Login Page Not Found</h1>", status_code=404)


@app.get("/manage", response_class=HTMLResponse)
async def manage_page():
    """Management console page"""
    manage_file = static_path / "manage.html"
    if manage_file.exists():
        return FileResponse(str(manage_file))
    return HTMLResponse(content="<h1>Management Page Not Found</h1>", status_code=404)
