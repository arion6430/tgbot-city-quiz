"""Клиент Unsplash API для получения фотографий городов."""

import random
import logging

import httpx

from bot.config import UNSPLASH_ACCESS_KEY

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://api.unsplash.com/search/photos"


async def get_city_photo(city_name: str) -> str | None:
    """
    Возвращает URL фотографии города с Unsplash.
    При ошибке или отсутствии результатов возвращает None.
    """
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                _SEARCH_URL,
                params={
                    "query": f"{city_name} city",
                    "per_page": 10,
                    "orientation": "landscape",
                },
                headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if not results:
                logger.warning("Unsplash: фото для '%s' не найдены", city_name)
                return None
            photo = random.choice(results[:10])
            return photo["urls"]["regular"]
    except Exception as exc:
        logger.error("Ошибка Unsplash для '%s': %s", city_name, exc)
        return None
