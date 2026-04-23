# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Educational Telegram bot: user sees a city photo and guesses its name. On correct answer receives Wikipedia facts and a map link. The codebase is **not yet written** — this file serves as the authoritative spec and architecture guide.

## Stack

- **Python 3.11+**, async everywhere
- **python-telegram-bot 20+** (asyncio, `JobQueue` for notifications)
- **PostgreSQL** + **asyncpg**
- **httpx** for external HTTP requests
- **python-dotenv** for config

## Commands

```bash
# Start services (PostgreSQL + bot)
docker-compose up -d

# Run bot directly (after pip install -r requirements.txt)
python -m bot.main

# Lint
ruff check bot/

# Tests
pytest
# Single test
pytest tests/test_game.py::test_answer_normalization
```

## Project Structure

```
city-quiz/
├── bot/
│   ├── handlers/         # Telegram handlers (/start, /stats, callbacks)
│   ├── services/         # Business logic (game, hints, stats, notifications)
│   ├── api/              # External API clients (unsplash, wikipedia, nominatim)
│   ├── db/               # CRUD, models, migrations
│   ├── config.py         # .env loading, constants
│   └── main.py           # Entry point, handler registration
├── data/
│   └── cities.json       # City pool: {name, country, population, difficulty}
├── .env
├── requirements.txt
└── docker-compose.yml
```

## Architecture

**Game flow:**
1. `/start` → greeting + "▶️ Start game" button
2. Button press → pick random city by difficulty → Unsplash photo → Nominatim coords (with DB cache) → send photo
3. Text answer → case-insensitive + whitespace-normalized comparison → update `user_stats`
4. Correct: Wikipedia facts + "➡️ Next" and "📍 Show on map" buttons
5. "📍 Show on map" → `sendLocation` from coord cache → button replaced with "➡️ Next"

**Key invariant:** Coordinates are always cached in `city_coordinates` before use. Never call Nominatim twice for the same city.

**Admin commands** (`/ban_city`) must verify `user_id` against `ADMIN_IDS` from `.env`.

**Hint limits:** 3 hints per round (5 questions per round).

## External APIs

| API | Purpose | Auth |
|-----|---------|------|
| Unsplash | City photo | `Authorization: Client-ID {UNSPLASH_ACCESS_KEY}` |
| Wikipedia REST | City facts | No key — **requires `User-Agent` header** |
| Nominatim (OSM) | lat/lon coords | No key — **requires `User-Agent` header** |

All external requests: 5s timeout, `try-except`, log errors.

- Wikipedia: `GET https://en.wikipedia.org/api/rest_v1/page/summary/{city_name}`
- Nominatim: `GET https://nominatim.openstreetmap.org/search?q={city}&format=json&limit=1`

## Database Schema

```sql
users (
  user_id      BIGINT PRIMARY KEY,   -- Telegram user_id
  username     TEXT,
  first_name   TEXT,
  last_name    TEXT,
  created_at   TIMESTAMPTZ DEFAULT NOW()
)

user_stats (
  stat_id          SERIAL PRIMARY KEY,
  user_id          BIGINT REFERENCES users(user_id),
  total_attempts   INTEGER DEFAULT 0,
  correct_answers  INTEGER DEFAULT 0,
  guessed_cities   TEXT[] DEFAULT '{}',
  difficulty_level TEXT DEFAULT 'medium',  -- easy | medium | hard
  hints_used       INTEGER DEFAULT 0
)

city_coordinates (
  coord_id     SERIAL PRIMARY KEY,
  city_name    TEXT UNIQUE,
  latitude     FLOAT,
  longitude    FLOAT,
  display_name TEXT,
  cached_at    TIMESTAMPTZ DEFAULT NOW()
)

excluded_cities (
  exclude_id  SERIAL PRIMARY KEY,
  city_name   TEXT,
  reason      TEXT,
  added_at    TIMESTAMPTZ DEFAULT NOW()
)
```

## Difficulty Levels

- `easy` — population > 1M
- `medium` — 100K–1M
- `hard` — < 100K

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Greeting |
| `/stats` | "Correct: 18/24 (75%)" + guessed cities list |
| `/подсказка` | Country or first letter hint (limit: 3/round) |
| `/сложность` | Choose easy/medium/hard |
| `/ежедневно` | Subscribe to daily notification at 12:00 MSK |
| `/ban_city` | Admin: add city to `excluded_cities` |

## Environment Variables (.env)

```
BOT_TOKEN=
UNSPLASH_ACCESS_KEY=
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/cityquiz
ADMIN_IDS=123456789,987654321
```
