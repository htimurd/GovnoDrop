import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, Defaults

import db
from config import BOT_TOKEN, WEBHOOK_HOST, WEBHOOK_PATH, WEBHOOK_SECRET, PORT
from handlers import (
    cmd_start,
    cmd_odds,
    cmd_daily,
    cmd_profile,
    cmd_portfolio,
    cmd_case,
    cmd_upgrade,
    cb_upgrade_confirm,
    cb_upgrade_cancel,
    cmd_top_coins,
    cmd_top_items,
)
from admin import (
    cmd_admin_help,
    cmd_stats,
    cmd_give,
    cmd_take,
    cmd_ban,
    cmd_unban,
    cmd_broadcast,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("govno_drop")

if not BOT_TOKEN:
    raise RuntimeError("Переменная окружения BOT_TOKEN не задана")


async def post_init(application: Application) -> None:
    await db.init_db()
    logger.info("База данных инициализирована")


def build_application() -> Application:
    defaults = Defaults(parse_mode=ParseMode.HTML)
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .defaults(defaults)
        .post_init(post_init)
        .build()
    )

    # Админские хендлеры регистрируем первыми
    application.add_handler(CommandHandler("admin", cmd_admin_help))
    application.add_handler(CommandHandler("stats", cmd_stats))
    application.add_handler(CommandHandler("give", cmd_give))
    application.add_handler(CommandHandler("take", cmd_take))
    application.add_handler(CommandHandler("ban", cmd_ban))
    application.add_handler(CommandHandler("unban", cmd_unban))
    application.add_handler(CommandHandler("broadcast", cmd_broadcast))

    # Пользовательские команды
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("odds", cmd_odds))
    application.add_handler(CommandHandler("daily", cmd_daily))
    application.add_handler(CommandHandler("profile", cmd_profile))
    application.add_handler(CommandHandler("portfolio", cmd_portfolio))
    application.add_handler(CommandHandler("case", cmd_case))
    application.add_handler(CommandHandler("upgrade", cmd_upgrade))
    application.add_handler(CommandHandler("top_coins", cmd_top_coins))
    application.add_handler(CommandHandler("top_items", cmd_top_items))

    application.add_handler(CallbackQueryHandler(cb_upgrade_confirm, pattern=r"^upg_confirm:\d+$"))
    application.add_handler(CallbackQueryHandler(cb_upgrade_cancel, pattern=r"^upg_cancel$"))

    return application


def main() -> None:
    application = build_application()

    if not WEBHOOK_HOST:
        logger.warning(
            "WEBHOOK_HOST не задан — вебхук не будет корректно установлен. "
            "Укажи WEBHOOK_HOST=https://<твой-сервис>.onrender.com в переменных окружения."
        )

    webhook_url = WEBHOOK_HOST.rstrip("/") + WEBHOOK_PATH

    # python-telegram-bot запускает собственный встроенный веб-сервер (tornado)
    # и сам вызывает setWebhook перед стартом приёма обновлений.
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_PATH.lstrip("/"),
        webhook_url=webhook_url,
        secret_token=WEBHOOK_SECRET,
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()
    
