"""Игровая логика: выбор города, проверка ответа, отправка вопроса."""

import json
import random
import logging
from pathlib import Path

import asyncpg
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.db import crud
from bot.api import unsplash, nominatim
from bot.config import HINTS_PER_QUESTION



logger = logging.getLogger(__name__)

_CITIES_PATH = Path(__file__).parent.parent.parent / "data" / "cities.json"

with open(_CITIES_PATH, encoding="utf-8") as _f:
    ALL_CITIES: list[dict] = json.load(_f)

_DIFFICULTY_EMOJI = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}
_DIFFICULTY_LABEL = {"easy": "Easy (&gt;1 млн)", "medium": "Medium (100K–1M)", "hard": "Hard (&lt;100K)"}


def normalize(text: str) -> str:
    """Нижний регистр + нормализация пробелов."""
    return " ".join(text.lower().split())


def check_answer(user_answer: str, city: dict) -> bool:
    names = [city["name"]] + city.get("alt_names", [])
    if city.get("name_ru"):
        names.append(city["name_ru"])
    normalized = normalize(user_answer)
    return any(normalize(name) == normalized for name in names)


def format_population(pop: int) -> str:
    if pop >= 1_000_000:
        return f"~{pop / 1_000_000:.1f} млн"
    if pop >= 1_000:
        return f"~{pop // 1_000} тыс."
    return str(pop)


def pick_city(difficulty: str, exclude_names: list[str]) -> dict | None:
    """
    Возвращает случайный город нужной сложности, исключая уже угаданные и заблокированные.
    Если все города данной сложности угаданы — сбрасывает историю (начинает заново).
    """
    exclude_set = {normalize(n) for n in exclude_names}
    candidates = [
        c for c in ALL_CITIES
        if c["difficulty"] == difficulty and normalize(c["name"]) not in exclude_set
    ]
    if not candidates:
        # Все города угаданы — берём любой кроме административно заблокированных
        blocked = set(exclude_names) - {c["name"] for c in ALL_CITIES if c["difficulty"] == difficulty}
        blocked_norm = {normalize(n) for n in blocked}
        candidates = [
            c for c in ALL_CITIES
            if c["difficulty"] == difficulty and normalize(c["name"]) not in blocked_norm
        ]
    return random.choice(candidates) if candidates else None


async def start_round(
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    pool: asyncpg.Pool,
) -> bool:
    """
    Выбирает город, получает фото, отправляет вопрос пользователю.
    Возвращает True при успехе, False при ошибке.
    """
    user_data = context.user_data

    difficulty = await crud.get_difficulty(pool, chat_id)
    guessed = await crud.get_guessed_cities(pool, chat_id)
    excluded = await crud.get_excluded_cities(pool)

    # Выбираем город; при неудаче с фото пробуем до 3 раз с разными городами
    city = None
    photo_url = None
    tried: list[str] = []

    for _ in range(3):
        city = pick_city(difficulty, guessed + excluded + tried)
        if not city:
            break
        photo_url = await unsplash.get_city_photo(city["name"])
        if photo_url:
            break
        tried.append(city["name"])

    if not city:
        await context.bot.send_message(
            chat_id,
            "😔 Города закончились! Смени сложность командой /difficulty или продолжай — "
            "история угаданных городов будет сброшена."
        )
        return False

    if not photo_url:
        await context.bot.send_message(
            chat_id, "⚠️ Не удалось загрузить фото. Попробуй ещё раз — нажми /start"
        )
        return False

    # Кэшируем координаты заранее (ошибки не блокируют игру)
    try:
        await nominatim.ensure_coords_cached(pool, city["name"])
    except Exception as exc:
        logger.warning("Не удалось закэшировать координаты для '%s': %s", city["name"], exc)

    # Увеличиваем счётчик попыток (показан новый город)
    await crud.increment_total_attempts(pool, chat_id)

    # Сохраняем состояние сессии
    user_data["current_city"] = city
    user_data["is_playing"] = True
    user_data["hints_used"] = 0

    diff_emoji = _DIFFICULTY_EMOJI.get(difficulty, "")
    diff_label = _DIFFICULTY_LABEL.get(difficulty, difficulty)

    keyboard = [
        [InlineKeyboardButton(f"💡 Подсказка ({HINTS_PER_QUESTION} из {HINTS_PER_QUESTION})", callback_data="hint")],
        [InlineKeyboardButton("🏳️ Сдаться", callback_data="give_up")],
    ]
    msg = await context.bot.send_photo(
        chat_id=chat_id,
        photo=photo_url,
        caption=(
            f"🌍 <b>Угадай город по фото!</b>\n\n"
            f"Сложность: {diff_emoji} {diff_label}\n\n"
            f"Введи название города в чат"
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    user_data["question_msg_id"] = msg.message_id
    return True
