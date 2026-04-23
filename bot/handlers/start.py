"""Хендлеры команды /start, главного меню и кнопок навигации."""

import html

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.db import crud
from bot.services.game import start_round


def _main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Начать игру", callback_data="start_game")],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="menu_stats"),
            InlineKeyboardButton("🏆 Топ-10", callback_data="menu_top"),
        ],
        [
            InlineKeyboardButton("🎯 Сложность", callback_data="menu_difficulty"),
            InlineKeyboardButton("🔔 Уведомления", callback_data="menu_daily"),
        ],
    ])


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pool = context.bot_data["db_pool"]
    user = update.effective_user

    await crud.ensure_user(pool, user.id, user.username, user.first_name, user.last_name)
    await crud.ensure_user_stats(pool, user.id)

    name = html.escape(user.first_name or "")
    await update.message.reply_text(
        f"👋 Привет, <b>{name}</b>!\n\n"
        "🏙 Добро пожаловать в <b>Город-загадку</b>!\n\n"
        "Я буду показывать тебе фотографии городов, а ты угадываешь их названия. "
        "За каждый правильный ответ узнаешь интересные факты! 🌍",
        reply_markup=_main_menu_keyboard(),
        parse_mode="HTML",
    )


async def start_game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    pool = context.bot_data["db_pool"]
    await query.edit_message_reply_markup(reply_markup=None)
    await start_round(query.from_user.id, context, pool)
