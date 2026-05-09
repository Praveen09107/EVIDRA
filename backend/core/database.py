"""
EVIDRA — Async PostgreSQL Connection Pool (asyncpg).

Production-grade pool with connection health checks.
Every module imports this single instance:

    from core.database import db
    rows = await db.fetch("SELECT * FROM cases WHERE status=$1", "OPEN")
    row  = await db.fetchrow("SELECT * FROM users WHERE email=$1", email)
    val  = await db.fetchval("SELECT count(*) FROM cases")
    await db.execute("INSERT INTO cases (title) VALUES ($1)", "Test")
    await db.executemany("INSERT INTO ...", [(a,b), (c,d)])
"""
import asyncpg
import logging
from core.config import settings

logger = logging.getLogger("evidra.database")

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Get or create the global connection pool."""
    global _pool
    if _pool is None:
        logger.info(f"Creating asyncpg pool → {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'local'}")
        _pool = await asyncpg.create_pool(
            dsn=settings.DATABASE_URL,
            min_size=settings.DB_MIN_POOL,
            max_size=settings.DB_MAX_POOL,
            command_timeout=30.0,
            statement_cache_size=100,
        )
        logger.info(f"Pool created (min={settings.DB_MIN_POOL}, max={settings.DB_MAX_POOL})")
    return _pool


async def close_pool():
    """Close the connection pool gracefully."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Pool closed")


async def fetch(query: str, *args) -> list:
    """Execute a query and return all rows as list of Records."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)


async def fetchrow(query: str, *args):
    """Execute a query and return a single row."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *args)


async def fetchval(query: str, *args):
    """Execute a query and return a single value."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(query, *args)


async def execute(query: str, *args) -> str:
    """Execute a query (INSERT/UPDATE/DELETE) and return status."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)


async def executemany(query: str, args_list: list) -> None:
    """Execute a query for each set of args in the list (batch insert)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.executemany(query, args_list)


# Module-level shorthand object so callers do: db.fetch(...), db.execute(...)
class _DB:
    get_pool = staticmethod(get_pool)
    close_pool = staticmethod(close_pool)
    fetch = staticmethod(fetch)
    fetchrow = staticmethod(fetchrow)
    fetchval = staticmethod(fetchval)
    execute = staticmethod(execute)
    executemany = staticmethod(executemany)

db = _DB()
