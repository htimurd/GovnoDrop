import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Список ID администраторов (модераторов) через запятую в переменной окружения ADMIN_IDS.
# Права админа: бан/разбан, начисление/списание монет, статистика, рассылка.
# Админка НЕ даёт скрытого влияния на шансы дропа/апгрейда — они одинаковы для всех
# и опубликованы командой /odds.
_raw_admins = os.environ.get("ADMIN_IDS", "8080874290")
ADMIN_IDS = {int(x) for x in _raw_admins.split(",") if x.strip().isdigit()}

WEBHOOK_HOST = os.environ.get("WEBHOOK_HOST", "")  # например https://govno-drop.onrender.com
WEBHOOK_PATH = "/webhook"
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "govnodrop-secret")

PORT = int(os.environ.get("PORT", "8080"))
