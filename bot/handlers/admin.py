"""Хендлеры команд администратора."""

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import ADMIN_IDS
from bot.db import crud


async def ban_city_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /ban_city <название> [причина]
    Добавляет город в список excluded_cities, исключая его из игры.
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ У тебя нет прав администратора.")
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "Использование: /ban_city <название> [причина]\n"
            "Пример: /ban_city Chernobyl радиационная зона"
        )
        return

    pool = context.bot_data["db_pool"]
    city_name = args[0]
    reason = " ".join(args[1:]) if len(args) > 1 else "не указана"

    await crud.add_excluded_city(pool, city_name, reason)
    await update.message.reply_text(
        f"✅ Город «{city_name}» добавлен в список заблокированных.\n"
        f"Причина: {reason}"
    )
