"""Хендлеры игрового процесса: приём ответов, карта, следующий город, подсказки, сдача."""

import html
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.db import crud
from bot.api import wikipedia
from bot.services.game import check_answer, format_population, start_round
from bot.config import HINTS_PER_QUESTION

logger = logging.getLogger(__name__)


def _question_keyboard(hints_used: int) -> InlineKeyboardMarkup:
    remaining = HINTS_PER_QUESTION - hints_used
    if remaining > 0:
        hint_text = f"💡 Подсказка ({remaining} из {HINTS_PER_QUESTION})"
    else:
        hint_text = "💡 Подсказки кончились"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(hint_text, callback_data="hint")],
        [InlineKeyboardButton("🏳️ Сдаться", callback_data="give_up")],
    ])


async def answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data

    if not user_data.get("is_playing"):
        return

    city = user_data.get("current_city")
    if not city:
        return

    pool = context.bot_data["db_pool"]
    user_id = update.effective_user.id

    if check_answer(update.message.text, city):
        user_data["is_playing"] = False

        await crud.update_stats_correct(pool, user_id, city["name"])

        # Убираем кнопки с фото-вопроса
        question_msg_id = user_data.get("question_msg_id")
        if question_msg_id:
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=update.effective_chat.id,
                    message_id=question_msg_id,
                    reply_markup=None,
                )
            except Exception:
                pass

        facts = await wikipedia.get_city_summary(city["name"], city.get("name_ru"))
        facts_block = f"\n\n📖 <i>{html.escape(facts)}</i>" if facts else ""

        keyboard = [[
            InlineKeyboardButton("📍 Показать на карте", callback_data="show_map"),
            InlineKeyboardButton("➡️ Дальше", callback_data="next_city"),
        ]]
        msg = await update.message.reply_text(
            f"✅ <b>Правильно! Это {html.escape(city['name'])}!</b>{facts_block}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )
        user_data["answer_message_id"] = msg.message_id
    else:
        await update.message.reply_text("❌ Неверно! Попробуй ещё раз.")


async def next_city_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    pool = context.bot_data["db_pool"]
    await query.edit_message_reply_markup(reply_markup=None)
    await start_round(query.from_user.id, context, pool)


async def show_map_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    pool = context.bot_data["db_pool"]
    city = context.user_data.get("current_city")

    if not city:
        await query.answer("Город не найден", show_alert=True)
        return

    coords = await crud.get_coord(pool, city["name"])
    if not coords:
        await query.answer("Координаты недоступны", show_alert=True)
        return

    await context.bot.send_location(
        chat_id=query.message.chat_id,
        latitude=coords["latitude"],
        longitude=coords["longitude"],
    )

    keyboard = [[InlineKeyboardButton("➡️ Дальше", callback_data="next_city")]]
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))


async def hint_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_data = context.user_data

    if not user_data.get("is_playing") or not user_data.get("current_city"):
        await query.answer("Сначала начни игру!", show_alert=True)
        return

    hints_used = user_data.get("hints_used", 0)
    if hints_used >= HINTS_PER_QUESTION:
        await query.answer("Подсказки на этот вопрос исчерпаны!", show_alert=True)
        return

    await query.answer()

    city = user_data["current_city"]
    pool = context.bot_data["db_pool"]
    user_id = query.from_user.id

    country = html.escape(city.get("country_ru") or city["country"])
    if hints_used == 0:
        neighbors = city.get("neighbors") or []
        if neighbors:
            hint = f"🗺 Граничит с: <b>{html.escape(', '.join(neighbors))}</b>"
        else:
            hint = "🌊 Страна — островное государство, нет сухопутных границ"
    elif hints_used == 1:
        hint = f"👥 Население: <b>{format_population(city['population'])}</b>"
    elif hints_used == 2:
        hint = f"🌍 Страна: <b>{country}</b>"
    else:
        name = city.get("name_ru") or city["name"]
        hint = f"🔤 Первая буква: <b>{html.escape(name[0])}</b>"

    user_data["hints_used"] = hints_used + 1
    await crud.update_hints_used(pool, user_id)

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=hint,
        parse_mode="HTML",
    )

    await query.edit_message_reply_markup(
        reply_markup=_question_keyboard(user_data["hints_used"])
    )


async def give_up_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_data = context.user_data
    city = user_data.get("current_city")
    if not city:
        return

    user_data["is_playing"] = False
    pool = context.bot_data["db_pool"]

    # Убираем кнопки с фото
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

    facts = await wikipedia.get_city_summary(city["name"], city.get("name_ru"))
    facts_block = f"\n\n📖 <i>{html.escape(facts)}</i>" if facts else ""

    keyboard = [[
        InlineKeyboardButton("📍 Показать на карте", callback_data="show_map"),
        InlineKeyboardButton("➡️ Дальше", callback_data="next_city"),
    ]]
    msg = await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"🏳️ <b>Это был {html.escape(city['name'])}!</b>{facts_block}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    user_data["answer_message_id"] = msg.message_id
