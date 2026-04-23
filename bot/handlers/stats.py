"""Хендлеры статистики, сложности и подписки на уведомления."""

import html

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.db import crud


def _difficulty_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🟢 Easy", callback_data="difficulty_easy"),
        InlineKeyboardButton("🟡 Medium", callback_data="difficulty_medium"),
        InlineKeyboardButton("🔴 Hard", callback_data="difficulty_hard"),
    ]])


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pool = context.bot_data["db_pool"]
    user = update.effective_user

    await crud.ensure_user(pool, user.id, user.username, user.first_name, user.last_name)
    await crud.ensure_user_stats(pool, user.id)

    stats = await crud.get_user_stats(pool, user.id)
    total = stats["total_attempts"]
    correct = stats["correct_answers"]
    pct = round(correct / total * 100) if total > 0 else 0
    guessed: list[str] = list(stats["guessed_cities"] or [])
    difficulty = stats["difficulty_level"]
    notify = "🔔 включены" if stats["daily_notify"] else "🔕 выключены"

    if guessed:
        shown = guessed[-10:]
        cities_text = html.escape(", ".join(shown))
        if len(guessed) > 10:
            cities_text += f" и ещё {len(guessed) - 10}"
    else:
        cities_text = "пока нет"

    _diff_label = {"easy": "🟢 Easy", "medium": "🟡 Medium", "hard": "🔴 Hard"}

    await update.message.reply_text(
        f"📊 <b>Твоя статистика:</b>\n\n"
        f"✅ Верно: {correct}/{total} ({pct}%)\n"
        f"🎯 Сложность: {_diff_label.get(difficulty, difficulty)}\n"
        f"💡 Всего подсказок использовано: {stats['hints_used']}\n"
        f"🔔 Уведомления: {notify}\n\n"
        f"🏙 Угаданные города:\n{cities_text}",
        parse_mode="HTML",
    )


_DIFFICULTY_TEXT = (
    "🎯 Выбери уровень сложности:\n\n"
    "🟢 <b>Easy</b> — города с населением более 1 млн\n"
    "🟡 <b>Medium</b> — 100 тыс. — 1 млн жителей\n"
    "🔴 <b>Hard</b> — менее 100 тыс. жителей"
)


async def difficulty_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        _DIFFICULTY_TEXT,
        reply_markup=_difficulty_keyboard(),
        parse_mode="HTML",
    )


async def set_difficulty_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    pool = context.bot_data["db_pool"]
    user_id = query.from_user.id
    difficulty = query.data.split("_", 1)[1]  # "difficulty_easy" → "easy"

    await crud.ensure_user_stats(pool, user_id)
    await crud.set_difficulty(pool, user_id, difficulty)

    _labels = {
        "easy": "🟢 Easy — города &gt;1 млн жителей",
        "medium": "🟡 Medium — 100K–1M жителей",
        "hard": "🔴 Hard — города &lt;100K жителей",
    }
    from bot.handlers.start import _main_menu_keyboard
    await query.edit_message_text(
        f"✅ Сложность установлена: {_labels.get(difficulty, difficulty)}\n\n"
        "Выбери действие:",
        reply_markup=_main_menu_keyboard(),
        parse_mode="HTML",
    )


async def subscribe_daily_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    pool = context.bot_data["db_pool"]
    user = update.effective_user

    await crud.ensure_user(pool, user.id, user.username, user.first_name, user.last_name)
    await crud.ensure_user_stats(pool, user.id)

    stats = await crud.get_user_stats(pool, user.id)
    new_state = not stats["daily_notify"]
    await crud.set_daily_notify(pool, user.id, new_state)

    if new_state:
        await update.message.reply_text(
            "🔔 Ты подписан на ежедневные уведомления в <b>12:00 МСК</b>!\n\n"
            "Каждый день я буду напоминать тебе сыграть. "
            "Чтобы отписаться, снова нажми кнопку 🔔.",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(
            "🔕 Ты отписался от ежедневных уведомлений.\n\n"
            "Чтобы снова подписаться — нажми кнопку 🔔."
        )


async def _send_stats(chat_id: int, user_id: int, pool, bot) -> None:
    stats = await crud.get_user_stats(pool, user_id)
    total = stats["total_attempts"]
    correct = stats["correct_answers"]
    pct = round(correct / total * 100) if total > 0 else 0
    guessed: list[str] = list(stats["guessed_cities"] or [])
    difficulty = stats["difficulty_level"]
    notify = "🔔 включены" if stats["daily_notify"] else "🔕 выключены"

    if guessed:
        shown = guessed[-10:]
        cities_text = html.escape(", ".join(shown))
        if len(guessed) > 10:
            cities_text += f" и ещё {len(guessed) - 10}"
    else:
        cities_text = "пока нет"

    _diff_label = {"easy": "🟢 Easy", "medium": "🟡 Medium", "hard": "🔴 Hard"}
    from bot.handlers.start import _main_menu_keyboard

    await bot.send_message(
        chat_id=chat_id,
        text=(
            f"📊 <b>Твоя статистика:</b>\n\n"
            f"✅ Верно: {correct}/{total} ({pct}%)\n"
            f"🎯 Сложность: {_diff_label.get(difficulty, difficulty)}\n"
            f"💡 Всего подсказок использовано: {stats['hints_used']}\n"
            f"🔔 Уведомления: {notify}\n\n"
            f"🏙 Угаданные города:\n{cities_text}"
        ),
        reply_markup=_main_menu_keyboard(),
        parse_mode="HTML",
    )


async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pool = context.bot_data["db_pool"]
    rows = await crud.get_top_players(pool)

    if not rows:
        await update.message.reply_text("🏆 Таблица лидеров пока пуста — сыграй первым!")
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, row in enumerate(rows):
        name = html.escape(row["first_name"] or row["username"] or "Аноним")
        pct = round(row["correct_answers"] / row["total_attempts"] * 100) if row["total_attempts"] else 0
        prefix = medals[i] if i < 3 else f"{i + 1}."
        lines.append(f"{prefix} <b>{name}</b> — {row['correct_answers']} верных ({pct}%)")

    await update.message.reply_text(
        "🏆 <b>Таблица лидеров:</b>\n\n" + "\n".join(lines),
        parse_mode="HTML",
    )


async def menu_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    pool = context.bot_data["db_pool"]
    user = query.from_user
    await crud.ensure_user(pool, user.id, user.username, user.first_name, user.last_name)
    await crud.ensure_user_stats(pool, user.id)
    await _send_stats(query.message.chat_id, user.id, pool, context.bot)


async def menu_top_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    pool = context.bot_data["db_pool"]
    rows = await crud.get_top_players(pool)

    if not rows:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🏆 Таблица лидеров пока пуста — сыграй первым!",
        )
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, row in enumerate(rows):
        name = html.escape(row["first_name"] or row["username"] or "Аноним")
        pct = round(row["correct_answers"] / row["total_attempts"] * 100) if row["total_attempts"] else 0
        prefix = medals[i] if i < 3 else f"{i + 1}."
        lines.append(f"{prefix} <b>{name}</b> — {row['correct_answers']} верных ({pct}%)")

    from bot.handlers.start import _main_menu_keyboard
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="🏆 <b>Таблица лидеров:</b>\n\n" + "\n".join(lines),
        reply_markup=_main_menu_keyboard(),
        parse_mode="HTML",
    )


async def menu_difficulty_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=_DIFFICULTY_TEXT,
        reply_markup=_difficulty_keyboard(),
        parse_mode="HTML",
    )


async def menu_daily_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    pool = context.bot_data["db_pool"]
    user = query.from_user

    await crud.ensure_user(pool, user.id, user.username, user.first_name, user.last_name)
    await crud.ensure_user_stats(pool, user.id)

    stats = await crud.get_user_stats(pool, user.id)
    new_state = not stats["daily_notify"]
    await crud.set_daily_notify(pool, user.id, new_state)

    from bot.handlers.start import _main_menu_keyboard
    if new_state:
        text = "🔔 Ты подписан на ежедневные уведомления в <b>12:00 МСК</b>!"
    else:
        text = "🔕 Ты отписался от ежедневных уведомлений."

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=text,
        reply_markup=_main_menu_keyboard(),
        parse_mode="HTML",
    )
