"""CRUD-операции с базой данных."""

import asyncpg


async def ensure_user(
    pool: asyncpg.Pool,
    user_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
) -> None:
    """Создаёт профиль пользователя или обновляет его данные."""
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (user_id, username, first_name, last_name)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id) DO UPDATE
              SET username   = EXCLUDED.username,
                  first_name = EXCLUDED.first_name,
                  last_name  = EXCLUDED.last_name
            """,
            user_id, username, first_name, last_name,
        )


async def ensure_user_stats(pool: asyncpg.Pool, user_id: int) -> None:
    """Создаёт строку статистики для пользователя, если её ещё нет."""
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO user_stats (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING",
            user_id,
        )


async def get_user_stats(pool: asyncpg.Pool, user_id: int) -> asyncpg.Record | None:
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM user_stats WHERE user_id = $1", user_id
        )


async def increment_total_attempts(pool: asyncpg.Pool, user_id: int) -> None:
    """Увеличивает счётчик показанных городов (вызывается при старте нового вопроса)."""
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE user_stats SET total_attempts = total_attempts + 1 WHERE user_id = $1",
            user_id,
        )


async def update_stats_correct(
    pool: asyncpg.Pool, user_id: int, city_name: str
) -> None:
    """Засчитывает правильный ответ и добавляет город в список угаданных."""
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE user_stats
            SET correct_answers = correct_answers + 1,
                guessed_cities  = array_append(guessed_cities, $2)
            WHERE user_id = $1
            """,
            user_id, city_name,
        )


async def update_hints_used(pool: asyncpg.Pool, user_id: int) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE user_stats SET hints_used = hints_used + 1 WHERE user_id = $1",
            user_id,
        )


async def get_difficulty(pool: asyncpg.Pool, user_id: int) -> str:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT difficulty_level FROM user_stats WHERE user_id = $1", user_id
        )
        return row["difficulty_level"] if row else "medium"


async def set_difficulty(pool: asyncpg.Pool, user_id: int, difficulty: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE user_stats SET difficulty_level = $2 WHERE user_id = $1",
            user_id, difficulty,
        )


async def get_guessed_cities(pool: asyncpg.Pool, user_id: int) -> list[str]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT guessed_cities FROM user_stats WHERE user_id = $1", user_id
        )
        return list(row["guessed_cities"]) if row and row["guessed_cities"] else []


async def get_excluded_cities(pool: asyncpg.Pool) -> list[str]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT city_name FROM excluded_cities")
        return [r["city_name"] for r in rows]


async def add_excluded_city(
    pool: asyncpg.Pool, city_name: str, reason: str
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO excluded_cities (city_name, reason) VALUES ($1, $2)",
            city_name, reason,
        )


async def get_coord(pool: asyncpg.Pool, city_name: str) -> asyncpg.Record | None:
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT latitude, longitude, display_name FROM city_coordinates WHERE city_name = $1",
            city_name,
        )


async def save_coord(
    pool: asyncpg.Pool,
    city_name: str,
    lat: float,
    lon: float,
    display_name: str,
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO city_coordinates (city_name, latitude, longitude, display_name)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (city_name) DO NOTHING
            """,
            city_name, lat, lon, display_name,
        )


async def set_daily_notify(
    pool: asyncpg.Pool, user_id: int, enabled: bool
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE user_stats SET daily_notify = $2 WHERE user_id = $1",
            user_id, enabled,
        )


async def get_daily_subscribers(pool: asyncpg.Pool) -> list[int]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT user_id FROM user_stats WHERE daily_notify = TRUE"
        )
        return [r["user_id"] for r in rows]


async def get_top_players(pool: asyncpg.Pool, limit: int = 10) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return await conn.fetch(
            """
            SELECT u.first_name, u.username, us.correct_answers, us.total_attempts
            FROM user_stats us
            JOIN users u ON us.user_id = u.user_id
            WHERE us.correct_answers > 0
            ORDER BY us.correct_answers DESC
            LIMIT $1
            """,
            limit,
        )
