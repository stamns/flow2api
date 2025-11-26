import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.db.sqlite import SqliteAdapter
from src.core.db.postgres import PostgresAdapter
from src.core.models import Token

async def test_adapter(adapter, name):
    print(f"Testing {name}...")
    try:
        if name == "SQLite":
             # Ensure db dir exists for sqlite
             Path(adapter.db_path).parent.mkdir(exist_ok=True)

        await adapter.init_db()
        if not await adapter.is_initialized():
             print(f"❌ {name} not initialized")
             return

        print(f"✓ {name} initialized")
        
        # Create a test token
        token_st = f"test_st_{datetime.now().timestamp()}"
        token = Token(
            st=token_st,
            email="test@example.com",
            name="Test Token",
            is_active=True
        )
        
        token_id = await adapter.add_token(token)
        print(f"✓ Added token with ID: {token_id}")
        
        fetched_token = await adapter.get_token(token_id)
        if fetched_token and fetched_token.st == token_st:
            print(f"✓ Verified token: {fetched_token.email}")
        else:
             print(f"❌ Failed to verify token")

        # Clean up
        await adapter.delete_token(token_id)
        print(f"✓ Cleaned up test token")

    except Exception as e:
        print(f"❌ Error testing {name}: {e}")
        import traceback
        traceback.print_exc()

async def run_smoke_test():
    print("Starting smoke test...")
    
    # Test SQLite
    try:
        sqlite_adapter = SqliteAdapter()
        await test_adapter(sqlite_adapter, "SQLite")
    except Exception as e:
        print(f"Failed to instantiate SQLite adapter: {e}")
    
    # Test Postgres if URL provided
    pg_url = os.getenv("DATABASE_URL")
    if pg_url:
        print("\n")
        try:
            pg_adapter = PostgresAdapter(pg_url)
            await test_adapter(pg_adapter, "Postgres")
        except Exception as e:
            print(f"Failed to instantiate Postgres adapter: {e}")
    else:
        print("\nSkipping Postgres test (DATABASE_URL not set)")

if __name__ == "__main__":
    asyncio.run(run_smoke_test())
