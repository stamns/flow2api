import asyncio
import os
import aiosqlite
import asyncpg
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

BOOLEAN_COLUMNS = {
    "tokens": ["is_active", "image_enabled", "video_enabled"],
    "projects": ["is_active"],
    "proxy_config": ["enabled"],
    "cache_config": ["cache_enabled"],
    "debug_config": ["enabled", "log_requests", "log_responses", "mask_token"],
}

async def migrate():
    sqlite_path = Path(__file__).parent.parent / "data" / "flow.db"
    pg_url = os.getenv("DATABASE_URL")

    if not sqlite_path.exists():
        print(f"SQLite database not found at {sqlite_path}")
        return

    if not pg_url:
        print("DATABASE_URL environment variable not set")
        return

    print(f"Migrating from {sqlite_path} to Postgres...")

    async with aiosqlite.connect(sqlite_path) as sqlite_conn:
        sqlite_conn.row_factory = aiosqlite.Row
        
        try:
            conn = await asyncpg.connect(pg_url)
        except Exception as e:
            print(f"Failed to connect to Postgres: {e}")
            return

        try:
            async with conn.transaction():
                # Config tables first
                await migrate_table(sqlite_conn, conn, "admin_config")
                await migrate_table(sqlite_conn, conn, "proxy_config")
                await migrate_table(sqlite_conn, conn, "generation_config")
                await migrate_table(sqlite_conn, conn, "cache_config")
                await migrate_table(sqlite_conn, conn, "debug_config")

                # Core tables
                await migrate_table(sqlite_conn, conn, "tokens")
                await migrate_table(sqlite_conn, conn, "projects")
                await migrate_table(sqlite_conn, conn, "token_stats")
                await migrate_table(sqlite_conn, conn, "tasks")
                await migrate_table(sqlite_conn, conn, "request_logs")
                
                # Reset sequences
                tables_with_id = ["tokens", "projects", "token_stats", "tasks", "request_logs"]
                for table in tables_with_id:
                     # Check if table has rows
                    count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                    if count > 0:
                        print(f"Resetting sequence for {table}...")
                        try:
                            await conn.execute(f"SELECT setval('{table}_id_seq', (SELECT MAX(id) FROM {table}))")
                        except Exception as e:
                            print(f"Warning: Failed to reset sequence for {table}: {e}")

            print("Migration completed successfully!")
            
        finally:
            await conn.close()

async def migrate_table(sqlite_conn, pg_conn, table_name):
    print(f"Migrating table {table_name}...")
    
    # Check if table exists in SQLite
    cursor = await sqlite_conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    if not await cursor.fetchone():
        print(f"Table {table_name} does not exist in SQLite, skipping.")
        return

    # Get data
    cursor = await sqlite_conn.execute(f"SELECT * FROM {table_name}")
    rows = await cursor.fetchall()
    
    if not rows:
        print(f"Table {table_name} is empty.")
        return

    columns = rows[0].keys()
    placeholders = ",".join([f"${i+1}" for i in range(len(columns))])
    cols_str = ",".join(columns)
    
    # Prepare insertion
    # Use ON CONFLICT DO NOTHING to avoid errors if running multiple times or if IDs clash
    query = f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING"
    
    # Convert rows to list of values, handling boolean conversion
    pg_rows = []
    bool_cols = BOOLEAN_COLUMNS.get(table_name, [])
    
    for row in rows:
        row_dict = dict(row)
        values = []
        for col in columns:
            val = row_dict[col]
            if col in bool_cols and isinstance(val, int):
                 values.append(bool(val))
            else:
                 values.append(val)
        pg_rows.append(values)

    # Batch insert
    try:
        await pg_conn.executemany(query, pg_rows)
        print(f"Migrated {len(pg_rows)} rows to {table_name}.")
    except Exception as e:
        print(f"Error migrating table {table_name}: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(migrate())
