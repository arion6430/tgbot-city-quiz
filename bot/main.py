"""Точка входа: сборка Application, регистрация хендлеров, запуск бота."""

import datetime
import logging

from telegram import BotCommand
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot.config import BOT_TOKEN
from bot.db import close_pool, get_pool, init_db
from bot.handlers.admin import ban_city_command
from bot.handlers.game import (
    answer_handler,
    give_up_callback,
    hint_callback,
    next_city_callback,
    show_map_callback,
)
from bot.handlers.start import start_command, start_game_callback
from bot.handlers.stats import (
    difficulty_command,
    menu_daily_callback,
    menu_difficulty_callback,
    menu_stats_callback,
    menu_top_callback,
    set_difficulty_callback,
    stats_command,
    subscribe_daily_command,
    top_command,
)
from bot.services.notifications import daily_notify

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def _post_init(app: Application) -> None:
    pool = await get_pool()
    await init_db(pool)
    app.bot_data["db_pool"] = pool
    logger.info("База данных инициализирована")

    app.job_queue.run_daily(
        daily_notify,
        time=datetime.time(hour=9, minute=0, tzinfo=datetime.timezone.utc),
        name="daily_notification",
    )
    logger.info("Задача ежедневных уведомлений запланирована на 09:00 UTC")

    await app.bot.set_my_commands([
        BotCommand("start",      "🏠 Главное меню"),
        BotCommand("stats",      "📊 Моя статистика"),
        BotCommand("top",        "🏆 Таблица лидеров"),
        BotCommand("difficulty", "🎯 Уровень сложности"),
        BotCommand("daily",      "🔔 Ежедневные уведомления"),
    ])
    logger.info("Меню команд зарегистрировано")


async def _post_shutdown(app: Application) -> None:
    await close_pool()
    logger.info("Пул соединений с БД закрыт")


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан в .env")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )

    # --- Команды ---
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CommandHandler("difficulty", difficulty_command))
    app.add_handler(CommandHandler("daily", subscribe_daily_command))
    app.add_handler(CommandHandler("ban_city", ban_city_command))

    # --- Inline-кнопки: игра ---
    app.add_handler(CallbackQueryHandler(start_game_callback, pattern="^start_game$"))
    app.add_handler(CallbackQueryHandler(next_city_callback, pattern="^next_city$"))
    app.add_handler(CallbackQueryHandler(show_map_callback, pattern="^show_map$"))
    app.add_handler(CallbackQueryHandler(hint_callback, pattern="^hint$"))
    app.add_handler(CallbackQueryHandler(give_up_callback, pattern="^give_up$"))

    # --- Inline-кнопки: главное меню ---
    app.add_handler(CallbackQueryHandler(menu_stats_callback, pattern="^menu_stats$"))
    app.add_handler(CallbackQueryHandler(menu_top_callback, pattern="^menu_top$"))
    app.add_handler(CallbackQueryHandler(menu_difficulty_callback, pattern="^menu_difficulty$"))
    app.add_handler(CallbackQueryHandler(menu_daily_callback, pattern="^menu_daily$"))
    app.add_handler(CallbackQueryHandler(set_difficulty_callback, pattern="^difficulty_"))

    # --- Текстовые ответы пользователя (не команды) ---
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, answer_handler))

    logger.info("Бот запускается...")
    app.run_polling()


if __name__ == "__main__":
    main()
