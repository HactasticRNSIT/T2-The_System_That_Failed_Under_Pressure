"""
Urban Resilience Platform — Database & Redis Infrastructure
Part 1: Core Backend Foundation
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from sqlalchemy import event, text
import redis.asyncio as aioredis
from redis.asyncio.connection import ConnectionPool
from typing import AsyncGenerator, Optional
import logging
from contextlib import asynccontextmanager

from app.core.config import settings

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════
# DATABASE ENGINE
# ══════════════════════════════════════════════════════════════════

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
    pool_pre_ping=True,           # Verify connections before use
    echo=settings.DEBUG,          # Log SQL in dev
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for database sessions"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions (for services)"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Initialize database with PostGIS extension"""
    from app.models.models import Base
    async with engine.begin() as conn:
        # Enable PostGIS
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis_topology;"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))  # Fuzzy search
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS uuid-ossp;"))

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database initialized with PostGIS")


async def check_db_health() -> dict:
    """Database health check"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1 AS healthy, version() AS version"))
            row = result.fetchone()
            return {
                "status": "healthy",
                "version": row.version if row else "unknown",
                "pool_size": engine.pool.size(),
                "checked_out": engine.pool.checkedout(),
            }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


# ══════════════════════════════════════════════════════════════════
# REDIS CONNECTIONS
# ══════════════════════════════════════════════════════════════════

class RedisManager:
    """
    Multi-database Redis manager.
    DB 0: General cache
    DB 1: Cache layer
    DB 2: Sessions
    DB 3: Queue (Celery)
    DB 4: Pub/Sub
    """

    def __init__(self):
        self._connections: dict[int, aioredis.Redis] = {}

    def _build_url(self, db: int) -> str:
        base = settings.REDIS_URL.rsplit("/", 1)[0]
        return f"{base}/{db}"

    async def get(self, db: int = 0) -> aioredis.Redis:
        if db not in self._connections:
            pool = ConnectionPool.from_url(
                self._build_url(db),
                decode_responses=True,
                max_connections=50,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            self._connections[db] = aioredis.Redis(connection_pool=pool)
        return self._connections[db]

    async def cache(self) -> aioredis.Redis:
        return await self.get(settings.REDIS_CACHE_DB)

    async def session(self) -> aioredis.Redis:
        return await self.get(settings.REDIS_SESSION_DB)

    async def pubsub(self) -> aioredis.Redis:
        return await self.get(settings.REDIS_PUBSUB_DB)

    async def close_all(self):
        for conn in self._connections.values():
            await conn.aclose()
        self._connections.clear()

    async def health_check(self) -> dict:
        try:
            r = await self.get(0)
            pong = await r.ping()
            info = await r.info("server")
            return {
                "status": "healthy" if pong else "unhealthy",
                "version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


redis_manager = RedisManager()


# ══════════════════════════════════════════════════════════════════
# CACHE UTILITIES
# ══════════════════════════════════════════════════════════════════

class CacheService:
    """High-level caching service with prefix management"""

    PREFIXES = {
        "worker": "w:",
        "district": "d:",
        "fatigue": "f:",
        "leaderboard": "lb:",
        "resilience": "rs:",
        "session": "s:",
        "gps": "gps:",
        "alert": "al:",
        "prediction": "pred:",
        "task": "t:",
        "simulation": "sim:",
    }

    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None

    async def _get_redis(self) -> aioredis.Redis:
        if not self._redis:
            self._redis = await redis_manager.cache()
        return self._redis

    def _key(self, prefix: str, identifier: str) -> str:
        pfx = self.PREFIXES.get(prefix, f"{prefix}:")
        return f"{pfx}{identifier}"

    async def get(self, prefix: str, identifier: str) -> Optional[str]:
        r = await self._get_redis()
        return await r.get(self._key(prefix, identifier))

    async def set(self, prefix: str, identifier: str, value: str, ttl: int = None) -> bool:
        r = await self._get_redis()
        ttl = ttl or settings.REDIS_TTL_DEFAULT
        return await r.set(self._key(prefix, identifier), value, ex=ttl)

    async def delete(self, prefix: str, identifier: str) -> int:
        r = await self._get_redis()
        return await r.delete(self._key(prefix, identifier))

    async def exists(self, prefix: str, identifier: str) -> bool:
        r = await self._get_redis()
        return bool(await r.exists(self._key(prefix, identifier)))

    async def increment(self, key: str, amount: int = 1) -> int:
        r = await self._get_redis()
        return await r.incrby(key, amount)

    async def expire(self, prefix: str, identifier: str, ttl: int) -> bool:
        r = await self._get_redis()
        return await r.expire(self._key(prefix, identifier), ttl)

    async def get_hash(self, key: str) -> dict:
        r = await self._get_redis()
        return await r.hgetall(key)

    async def set_hash(self, key: str, mapping: dict, ttl: int = None) -> bool:
        r = await self._get_redis()
        await r.hset(key, mapping=mapping)
        if ttl:
            await r.expire(key, ttl)
        return True

    async def add_to_sorted_set(self, key: str, score: float, member: str) -> int:
        r = await self._get_redis()
        return await r.zadd(key, {member: score})

    async def get_sorted_set_range(self, key: str, start: int = 0, end: int = -1, desc: bool = True) -> list:
        r = await self._get_redis()
        if desc:
            return await r.zrevrange(key, start, end, withscores=True)
        return await r.zrange(key, start, end, withscores=True)

    async def publish(self, channel: str, message: str) -> int:
        r = await redis_manager.pubsub()
        return await r.publish(channel, message)

    async def flush_pattern(self, pattern: str) -> int:
        r = await self._get_redis()
        keys = await r.keys(pattern)
        if keys:
            return await r.delete(*keys)
        return 0


cache_service = CacheService()