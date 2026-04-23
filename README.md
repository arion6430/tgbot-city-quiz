# City Quiz Bot

Образовательный Telegram-бот: пользователь видит фото города и угадывает его название. При правильном ответе получает факты из Wikipedia и ссылку на карту.

## Стек

- Python 3.11+, async
- python-telegram-bot 20+ (asyncio, JobQueue)
- PostgreSQL + asyncpg
- httpx, python-dotenv

## Быстрый старт

```bash
cp .env.example .env
# Заполните переменные в .env

docker-compose up -d
pip install -r requirements.txt
python -m bot.main
```

## Переменные окружения (.env)

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен от @BotFather |
| `UNSPLASH_ACCESS_KEY` | Ключ Unsplash API |
| `DATABASE_URL` | postgresql+asyncpg://user:pass@localhost:5432/cityquiz |
| `ADMIN_IDS` | Telegram user_id администраторов через запятую |

## Команды бота

| Команда | Описание |
|---|---|
| `/start` | Приветствие и начало игры |
| `/stats` | Статистика: правильные ответы, угаданные города |
| `/подсказка` | Подсказка (страна или первая буква, до 3 за раунд) |
| `/сложность` | Выбор уровня: easy / medium / hard |
| `/ежедневно` | Подписка на ежедневное уведомление в 12:00 МСК |
| `/ban_city` | Админ: добавить город в исключения |

## Уровни сложности

- `easy` — население > 1 млн
- `medium` — 100 тыс. – 1 млн
- `hard` — до 100 тыс.

## Разработка

```bash
ruff check bot/   # линтер
pytest            # тесты
```
