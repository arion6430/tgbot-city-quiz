"""Клиент OpenStreetMap Nominatim для геокодирования городов."""

import logging

import httpx

from bot.config import USER_AGENT
from bot.db import crud

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://nominatim.openstreetmap.org/search"


async def _fetch_coords(city_name: str) -> tuple[float, float, str] | None:
    """
    Запрашивает координаты у Nominatim.
    Возвращает (latitude, longitude, display_name) или None.
    """
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                _SEARCH_URL,
                params={"q": city_name, "format": "json", "limit": 1},
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
            results = resp.json()
            if not results:
                logger.warning("Nominatim: координаты для '%s' не найдены", city_name)
                return None
            r = results[0]
            return float(r["lat"]), float(r["lon"]), r.get("display_name", city_name)
    except Exception as exc:
        logger.error("Ошибка Nominatim для '%s': %s", city_name, exc)
        return None


async def ensure_coords_cached(
    pool, city_name: str
) -> tuple[float, float] | None:
    """
    Возвращает координаты города (lat, lon).
    Сначала проверяет кэш в БД, при отсутствии — запрашивает Nominatim и сохраняет.
    """
    cached = await crud.get_coord(pool, city_name)
    if cached:
        return cached["latitude"], cached["longitude"]

    result = await _fetch_coords(city_name)
    if result:
        lat, lon, display = result
        await crud.save_coord(pool, city_name, lat, lon, display)
        return lat, lon

    return None
