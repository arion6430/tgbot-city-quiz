"""Клиент Wikipedia REST API для получения фактов о городах на русском языке."""

import logging

import httpx

from bot.config import USER_AGENT

logger = logging.getLogger(__name__)

_SUMMARY_URL_RU = "https://ru.wikipedia.org/api/rest_v1/page/summary/{}"
_SUMMARY_URL_EN = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
_MAX_LENGTH = 600


async def get_city_summary(city_name: str, city_name_ru: str | None = None) -> str | None:
    """
    Возвращает краткое описание города из Википедии.
    Сначала пробует русскую версию, при неудаче — английскую.
    """
    async with httpx.AsyncClient(timeout=5) as client:
        # Пробуем русскую Википедию
        if city_name_ru:
            text = await _fetch(client, _SUMMARY_URL_RU, city_name_ru)
            if text:
                return text

        # Fallback: английская Википедия
        text = await _fetch(client, _SUMMARY_URL_EN, city_name)
        return text


async def _fetch(client: httpx.AsyncClient, url_template: str, name: str) -> str | None:
    url = url_template.format(name.replace(" ", "_"))
    try:
        resp = await client.get(url, headers={"User-Agent": USER_AGENT})
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        extract: str = resp.json().get("extract", "")
        if not extract:
            return None
        return extract[:_MAX_LENGTH] + ("…" if len(extract) > _MAX_LENGTH else "")
    except Exception as exc:
        logger.error("Ошибка Wikipedia (%s): %s", name, exc)
        return None
