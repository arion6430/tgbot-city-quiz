"""Сервис ежедневных уведомлений (12:00 МСК = 09:00 UTC)."""

import logging

from telegram.ext import ContextTypes

from bot.db import crud

logger = logging.getLogger(__name__)


async def daily_notify(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Рассылает мотивационное сообщение всем подписчикам.
    Вызывается JobQueue каждый день в 09:00 UTC (12:00 МСК).
    """
    pool = context.bot_data["db_pool"]
    subscribers = await crud.get_daily_subscribers(pool)

    sent = 0
    for user_id in subscribers:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="🌅 <b>Доброе утро!</b>\n\nПора угадывать города! Нажми /start чтобы начать игру 🏙",
                parse_mode="HTML",
            )
            sent += 1
        except Exception as exc:
            # Пользователь мог заблокировать бота
            logger.warning(
                "Не удалось отправить уведомление пользователю %d: %s", user_id, exc
            )

    logger.info(
        "Ежедневные уведомления отправлены: %d из %d подписчиков", sent, len(subscribers)
    )
