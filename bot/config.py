import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
UNSPLASH_ACCESS_KEY: str = os.getenv("UNSPLASH_ACCESS_KEY", "")

# asyncpg принимает postgresql://, убираем суффикс +asyncpg если он есть
DATABASE_URL: str = os.getenv(
    "DATABASE_URL", "postgresql://user:pass@localhost:5432/cityquiz"
).replace("postgresql+asyncpg://", "postgresql://")

def _parse_admin_ids(raw: str) -> list[int]:
    """Парсит ADMIN_IDS, пропуская юзернеймы и невалидные значения."""
    result = []
    for x in raw.split(","):
        x = x.strip().lstrip("@")
        try:
            result.append(int(x))
        except ValueError:
            pass  # юзернейм вместо числового ID — игнорируем
    return result

ADMIN_IDS: list[int] = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))

# User-Agent обязателен для Wikipedia и Nominatim
USER_AGENT = "CityQuizBot/1.0 (github.com/cityquiz)"

HINTS_PER_QUESTION = 4    # максимум подсказок на один вопрос
