from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

import db
from config import ADMIN_IDS

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("admin"))
async def cmd_admin_help(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "🛠 <b>Админ-панель Govno Drop</b>\n\n"
        "/stats — общая статистика бота\n"
        "/give &lt;user_id&gt; &lt;amount&gt; — начислить монеты\n"
        "/take &lt;user_id&gt; &lt;amount&gt; — списать монеты\n"
        "/ban &lt;user_id&gt; — забанить пользователя\n"
        "/unban &lt;user_id&gt; — разбанить пользователя\n"
        "/broadcast &lt;текст&gt; — рассылка всем пользователям\n\n"
        "Примечание: шансы дропа/апгрейда едины для всех и публичны (/odds), "
        "админка их не меняет."
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    s = await db.get_stats()
    await message.answer(
        "📊 <b>Статистика Govno Drop</b>\n\n"
        f"👥 Пользователей: {s['users_count']}\n"
        f"🚫 Забанено: {s['banned_count']}\n"
        f"💰 Всего монет в обороте: {s['total_coins']}\n"
        f"🎒 Всего предметов выдано: {s['items_count']}"
    )


@router.message(Command("give"))
async def cmd_give(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 3 or not parts[1].isdigit() or not parts[2].lstrip("-").isdigit():
        await message.answer("Использование: /give <user_id> <amount>")
        return
    user_id, amount = int(parts[1]), int(parts[2])
    await db.get_or_create_user(user_id, None)
    await db.add_coins(user_id, amount)
    await message.answer(f"✅ Начислено {amount} монет пользователю {user_id}.")


@router.message(Command("take"))
async def cmd_take(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 3 or not parts[1].isdigit() or not parts[2].isdigit():
        await message.answer("Использование: /take <user_id> <amount>")
        return
    user_id, amount = int(parts[1]), int(parts[2])
    await db.add_coins(user_id, -amount)
    await message.answer(f"✅ Списано {amount} монет у пользователя {user_id}.")


@router.message(Command("ban"))
async def cmd_ban(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /ban <user_id>")
        return
    user_id = int(parts[1])
    await db.set_banned(user_id, True)
    await message.answer(f"🚫 Пользователь {user_id} забанен.")


@router.message(Command("unban"))
async def cmd_unban(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /unban <user_id>")
        return
    user_id = int(parts[1])
    await db.set_banned(user_id, False)
    await message.answer(f"✅ Пользователь {user_id} разбанен.")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if not is_admin(message.from_user.id):
        return
    text = message.text.partition(" ")[2].strip()
    if not text:
        await message.answer("Использование: /broadcast <текст сообщения>")
        return

    ids = await db.all_user_ids()
    sent, failed = 0, 0
    status = await message.answer(f"📢 Рассылка запущена для {len(ids)} пользователей...")
    for uid in ids:
        try:
            await message.bot.send_message(uid, f"📢 <b>Объявление Govno Drop</b>\n\n{text}")
            sent += 1
        except Exception:
            failed += 1
    await status.edit_text(f"📢 Рассылка завершена. Успешно: {sent}, ошибок: {failed}.")
