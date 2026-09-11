# Govno Drop 💩

Шуточный Telegram-бот про "прокачку" полностью вымышленных предметов
(драные носки, ржавые банки, золотые унитазы и т.д.). Игровая валюта и
предметы **не имеют реальной ценности** и нигде не обмениваются на деньги —
это просто мини-игра для развлечения в чате.

Технологии: Python 3.11, aiogram 3, aiohttp (webhook), SQLite.

## Возможности

- `/start` — регистрация, стартовый баланс
- `/case` — открыть кейс за монеты (случайный предмет)
- `/upgrade <id>` — попытаться улучшить предмет (шанс виден заранее)
- `/portfolio` — список твоих предметов
- `/profile` — профиль: монеты, кол-во предметов, оценочная стоимость
- `/odds` — **честная и публичная** таблица шансов дропа и апгрейда
- `/daily` — ежедневный бонус монет
- `/top_coins`, `/top_items` — таблицы лидеров

Админ-команды (только для ID из `ADMIN_IDS`):
- `/admin` — список команд
- `/stats` — статистика бота
- `/give <user_id> <amount>` / `/take <user_id> <amount>` — монеты
- `/ban <user_id>` / `/unban <user_id>`
- `/broadcast <текст>` — рассылка всем игрокам

Админка даёт права **модерации**, а не скрытого влияния на исход игры —
шансы одинаковы для всех и опубликованы командой `/odds`.

## Локальный запуск

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # заполни BOT_TOKEN и остальные переменные
```

Для локального теста без вебхука проще временно переключиться на polling
(см. раздел ниже), т.к. вебхуку нужен публичный HTTPS-адрес.

### Быстрый тест через polling (опционально)

Если хочешь погонять бота локально без Render, создай `poll.py`:

```python
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from bot import db
from bot.config import BOT_TOKEN
from bot.handlers import router as user_router
from bot.admin import router as admin_router

async def main():
    await db.init_db()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(admin_router)
    dp.include_router(user_router)
    await dp.start_polling(bot)

asyncio.run(main())
```

```bash
python poll.py
```

## Деплой на Render.com (Web Service)

1. Залей этот проект в свой репозиторий на GitHub/GitLab.
2. На [render.com](https://render.com) → **New** → **Web Service** →
   подключи репозиторий (Render подхватит `render.yaml` автоматически,
   либо настрой вручную).
3. Если настраиваешь вручную, укажи:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
4. В разделе **Environment** добавь переменные:
   - `BOT_TOKEN` — токен от [@BotFather](https://t.me/BotFather)
   - `WEBHOOK_HOST` — URL твоего сервиса, например
     `https://govno-drop-bot.onrender.com` (Render выдаст его после
     первого деплоя — можно передеплоить после того, как узнаешь адрес)
   - `WEBHOOK_SECRET` — любая случайная строка
   - `ADMIN_IDS` — `8080874290` (можно перечислить несколько через запятую)
5. Дождись деплоя. При старте бот сам установит вебхук на Telegram.
6. Проверь: открой `https://<твой-сервис>.onrender.com/health` — должен
   вернуться `{"status": "ok", ...}`.
7. Напиши боту `/start` в Telegram.

### Важно про бесплатный план Render

Бесплатные веб-сервисы на Render "засыпают" после ~15 минут без запросов
и просыпаются по первому входящему запросу (в т.ч. по вебхуку от
Telegram, так что первое сообщение после простоя может прийти с
задержкой в несколько секунд). Для бота без пауз нужен платный план
или внешний "пинговщик" health-эндпоинта.

### Хранилище данных

Бот использует SQLite-файл `govno_drop.db` рядом с приложением. На
бесплатном плане Render диск **не персистентный** между деплоями —
при каждом новом деплое база обнулится. Для постоянного хранения
подключи Render Disk (Persistent Disk, платная опция) или вынеси БД во
внешний managed Postgres/Render PostgreSQL и адаптируй `bot/db.py`.

## Структура проекта

```
.
├── main.py              # aiohttp-приложение + вебхук aiogram, health-check
├── bot/
│   ├── config.py         # переменные окружения
│   ├── db.py              # работа с SQLite (пользователи, инвентарь)
│   ├── items.py            # тиры предметов, вероятности дропа/апгрейда
│   ├── handlers.py          # пользовательские команды
│   └── admin.py              # админ-команды (модерация)
├── requirements.txt
├── render.yaml            # Render Blueprint для автодеплоя
└── .env.example
```

## Изменить баланс/шансы

Все тиры предметов, их эмодзи, стоимость, вес дропа и шанс апгрейда
задаются в одном месте — `bot/items.py`, список `TIERS`. Правь его,
чтобы настроить экономику игры.
