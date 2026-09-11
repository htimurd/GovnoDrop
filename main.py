import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

import db
from config import BOT_TOKEN, WEBHOOK_HOST, WEBHOOK_PATH, WEBHOOK_SECRET, PORT
from handlers import router as user_router
from admin import router as admin_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("govno_drop")

if not BOT_TOKEN:
    raise RuntimeError("Переменная окружения BOT_TOKEN не задана")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
dp.include_router(admin_router)  # админские команды регистрируем первыми
dp.include_router(user_router)


async def on_startup(app: web.Application):
    await db.init_db()
    logger.info("База данных инициализирована")

    if WEBHOOK_HOST:
        webhook_url = WEBHOOK_HOST.rstrip("/") + WEBHOOK_PATH
        await bot.set_webhook(
            webhook_url,
            secret_token=WEBHOOK_SECRET,
            drop_pending_updates=True,
        )
        logger.info(f"Webhook установлен: {webhook_url}")
    else:
        logger.warning(
            "WEBHOOK_HOST не задан — вебхук не установлен. "
            "Укажи WEBHOOK_HOST=https://<твой-сервис>.onrender.com в переменных окружения."
        )


async def on_shutdown(app: web.Application):
    await bot.delete_webhook()
    await bot.session.close()


async def health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "service": "govno-drop-bot"})


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET,
    ).register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="0.0.0.0", port=PORT)
