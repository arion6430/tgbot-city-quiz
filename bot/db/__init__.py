import asyncpg
from bot.config import DATABASE_URL

_pool: asyncpg.Pool | None = None

# SQL создания таблиц (идемпотентно — IF NOT EXISTS)
_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS users (
    user_id    BIGINT PRIMARY KEY,
    username   TEXT,
    first_name TEXT,
    last_name  TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_stats (
    stat_id          SERIAL PRIMARY KEY,
    user_id          BIGINT REFERENCES users(user_id) ON DELETE CASCADE UNIQUE,
    total_attempts   INTEGER DEFAULT 0,
    correct_answers  INTEGER DEFAULT 0,
    guessed_cities   TEXT[] DEFAULT '{}',
    difficulty_level TEXT DEFAULT 'medium',
    hints_used       INTEGER DEFAULT 0,
    daily_notify     BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS city_coordinates (
    coord_id     SERIAL PRIMARY KEY,
    city_name    TEXT UNIQUE,
    latitude     FLOAT,
    longitude    FLOAT,
    display_name TEXT,
    cached_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS excluded_cities (
    exclude_id SERIAL PRIMARY KEY,
    city_name  TEXT,
    reason     TEXT,
    added_at   TIMESTAMPTZ DEFAULT NOW()
);
"""


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    return _pool


async def init_db(pool: asyncpg.Pool) -> None:
    """Создаёт таблицы, если они ещё не существуют."""
    async with pool.acquire() as conn:
        await conn.execute(_CREATE_TABLES)


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
