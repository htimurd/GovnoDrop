import random
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import db
from items import TIERS, TIERS_BY_KEY, next_tier, case_price, format_odds_table


def fmt_user(u: dict) -> str:
    return f"@{u['username']}" if u.get("username") else f"id{u['user_id']}"


async def _blocked_if_banned(update: Update) -> bool:
    """Возвращает True и отправляет сообщение, если пользователь забанен."""
    if await db.is_banned(update.effective_user.id):
        await update.message.reply_text("🚫 Ты забанен в Govno Drop и не можешь пользоваться ботом.")
        return True
    return False


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await db.get_or_create_user(update.effective_user.id, update.effective_user.username)
    if user["banned"]:
        await update.message.reply_text("🚫 Ты забанен в Govno Drop.")
        return
    await update.message.reply_text(
        "💩 <b>Добро пожаловать в Govno Drop!</b>\n\n"
        "Это шуточная игра про прокачку абсолютно бесполезных виртуальных "
        "предметов. Никакой реальной ценности монеты и предметы не имеют — "
        "это просто игра для развлечения.\n\n"
        f"Тебе начислено {db.START_COINS} монет для старта.\n\n"
        "<b>Команды:</b>\n"
        "/case — открыть кейс за монеты\n"
        "/portfolio — твой портфель предметов\n"
        "/upgrade — попробовать улучшить предмет\n"
        "/profile — твой профиль\n"
        "/odds — честные шансы дропа и апгрейда\n"
        "/daily — ежедневный бонус монет\n"
        "/top_coins — топ игроков по монетам\n"
        "/top_items — топ игроков по количеству предметов\n"
    )


async def cmd_odds(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(format_odds_table())


async def cmd_daily(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _blocked_if_banned(update):
        return
    await db.get_or_create_user(update.effective_user.id, update.effective_user.username)
    ok, wait = await db.try_claim_daily(update.effective_user.id)
    if ok:
        await update.message.reply_text(f"🎁 Ты получил ежедневный бонус: +{db.DAILY_BONUS} монет!")
    else:
        h = wait // 3600
        m = (wait % 3600) // 60
        await update.message.reply_text(f"⏳ Бонус уже получен. Приходи через {h} ч {m} мин.")


async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _blocked_if_banned(update):
        return
    user = await db.get_or_create_user(update.effective_user.id, update.effective_user.username)
    inv = await db.get_inventory(update.effective_user.id)
    total_value = sum(TIERS_BY_KEY[i["item_key"]].value for i in inv)
    joined = time.strftime("%d.%m.%Y", time.localtime(user["created_at"]))

    await update.message.reply_text(
        f"👤 <b>Профиль {fmt_user(user)}</b>\n\n"
        f"💰 Монеты: {user['coins']}\n"
        f"🎒 Предметов в портфеле: {len(inv)}\n"
        f"💎 Оценочная стоимость портфеля: {total_value} монет\n"
        f"📅 В игре с: {joined}"
    )


async def cmd_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _blocked_if_banned(update):
        return
    await db.get_or_create_user(update.effective_user.id, update.effective_user.username)
    inv = await db.get_inventory(update.effective_user.id)
    if not inv:
        await update.message.reply_text("🎒 Твой портфель пуст. Открой кейс командой /case!")
        return

    lines = ["🎒 <b>Твой портфель:</b>\n"]
    total_value = 0
    for item in inv:
        tier = TIERS_BY_KEY[item["item_key"]]
        total_value += tier.value
        lines.append(f"#{item['id']} {tier.emoji} {tier.title} (~{tier.value} монет)")
    lines.append(f"\n💎 Общая стоимость: {total_value} монет")
    lines.append("\nИспользуй /upgrade чтобы попытаться улучшить предмет.")
    text = "\n".join(lines)

    if len(text) > 3900:
        text = text[:3900] + "\n… список обрезан"
    await update.message.reply_text(text)


async def cmd_case(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _blocked_if_banned(update):
        return
    user = await db.get_or_create_user(update.effective_user.id, update.effective_user.username)
    price = case_price()
    if user["coins"] < price:
        await update.message.reply_text(f"💸 Недостаточно монет. Кейс стоит {price} монет.")
        return

    weights = [t.drop_weight for t in TIERS]
    chosen = random.choices(TIERS, weights=weights, k=1)[0]

    await db.add_coins(update.effective_user.id, -price)
    item_id = await db.add_item(update.effective_user.id, chosen.key)

    await update.message.reply_text(
        f"📦 Открываешь кейс за {price} монет...\n\n"
        f"🎉 Выпало: {chosen.emoji} <b>{chosen.title}</b> (#{item_id})\n"
        f"Стоимость: ~{chosen.value} монет\n\n"
        "Посмотреть шансы: /odds"
    )


async def cmd_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _blocked_if_banned(update):
        return
    await db.get_or_create_user(update.effective_user.id, update.effective_user.username)

    if not context.args or not context.args[0].isdigit():
        inv = await db.get_inventory(update.effective_user.id)
        if not inv:
            await update.message.reply_text("🎒 Портфель пуст, сначала открой /case.")
            return
        await update.message.reply_text(
            "Укажи номер предмета из /portfolio, например:\n<code>/upgrade 5</code>"
        )
        return

    item_id = int(context.args[0])
    item = await db.get_item(item_id, update.effective_user.id)
    if not item:
        await update.message.reply_text("❌ Предмет с таким номером не найден в твоём портфеле.")
        return

    tier = TIERS_BY_KEY[item["item_key"]]
    nt = next_tier(tier.key)
    if nt is None:
        await update.message.reply_text(f"{tier.emoji} {tier.title} — уже максимальный тир, апгрейдить некуда.")
        return

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Попробовать апгрейд", callback_data=f"upg_confirm:{item_id}")],
            [InlineKeyboardButton("❌ Отмена", callback_data="upg_cancel")],
        ]
    )

    await update.message.reply_text(
        f"⬆️ Апгрейд {tier.emoji} {tier.title} → {nt.emoji} {nt.title}\n"
        f"Шанс успеха: <b>{tier.upgrade_chance*100:.0f}%</b>\n"
        f"⚠️ При неудаче предмет будет потерян!",
        reply_markup=keyboard,
    )


async def cb_upgrade_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.edit_message_text("Апгрейд отменён.")
    await update.callback_query.answer()


async def cb_upgrade_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if await db.is_banned(query.from_user.id):
        await query.answer("Ты забанен.", show_alert=True)
        return

    item_id = int(query.data.split(":")[1])
    item = await db.get_item(item_id, query.from_user.id)
    if not item:
        await query.edit_message_text("❌ Предмет уже недоступен (возможно, уже использован).")
        await query.answer()
        return

    tier = TIERS_BY_KEY[item["item_key"]]
    nt = next_tier(tier.key)
    if nt is None:
        await query.edit_message_text("Этот предмет уже максимального тира.")
        await query.answer()
        return

    success = random.random() < tier.upgrade_chance
    await db.remove_item(item_id, query.from_user.id)

    if success:
        new_id = await db.add_item(query.from_user.id, nt.key)
        await query.edit_message_text(
            f"🎉 Успех! {tier.emoji} {tier.title} превратился в "
            f"{nt.emoji} <b>{nt.title}</b> (#{new_id})"
        )
    else:
        await query.edit_message_text(
            f"💀 Неудача! {tier.emoji} {tier.title} потерян навсегда.\n"
            "Не переживай, это просто игра — попробуй ещё раз с /case"
        )
    await query.answer()


async def cmd_top_coins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    top = await db.top_by_coins(10)
    if not top:
        await update.message.reply_text("Пока никого нет в топе.")
        return
    medals = ["🥇", "🥈", "🥉"]
    lines = ["💰 <b>Топ по монетам</b>\n"]
    for i, u in enumerate(top):
        prefix = medals[i] if i < 3 else f"{i+1}."
        lines.append(f"{prefix} {fmt_user(u)} — {u['coins']} монет")
    await update.message.reply_text("\n".join(lines))


async def cmd_top_items(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    top = await db.top_by_items(10)
    if not top:
        await update.message.reply_text("Пока никого нет в топе.")
        return
    medals = ["🥇", "🥈", "🥉"]
    lines = ["🎒 <b>Топ по количеству предметов</b>\n"]
    for i, u in enumerate(top):
        prefix = medals[i] if i < 3 else f"{i+1}."
        lines.append(f"{prefix} {fmt_user(u)} — {u['item_count']} предметов")
    await update.message.reply_text("\n".join(lines))
    
