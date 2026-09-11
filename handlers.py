import random
import time

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

import db
from items import TIERS, TIERS_BY_KEY, next_tier, case_price, format_odds_table

router = Router()


def fmt_user(u: dict) -> str:
    return f"@{u['username']}" if u.get("username") else f"id{u['user_id']}"


async def check_not_banned(message: Message) -> bool:
    if await db.is_banned(message.from_user.id):
        await message.answer("🚫 Ты забанен в Govno Drop и не можешь пользоваться ботом.")
        return False
    return True


@router.message(CommandStart())
async def cmd_start(message: Message):
    user = await db.get_or_create_user(message.from_user.id, message.from_user.username)
    if user["banned"]:
        await message.answer("🚫 Ты забанен в Govno Drop.")
        return
    await message.answer(
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


@router.message(Command("odds"))
async def cmd_odds(message: Message):
    await message.answer(format_odds_table())


@router.message(Command("daily"))
async def cmd_daily(message: Message):
    if not await check_not_banned(message):
        return
    await db.get_or_create_user(message.from_user.id, message.from_user.username)
    ok, wait = await db.try_claim_daily(message.from_user.id)
    if ok:
        await message.answer(f"🎁 Ты получил ежедневный бонус: +{db.DAILY_BONUS} монет!")
    else:
        h = wait // 3600
        m = (wait % 3600) // 60
        await message.answer(f"⏳ Бонус уже получен. Приходи через {h} ч {m} мин.")


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    if not await check_not_banned(message):
        return
    user = await db.get_or_create_user(message.from_user.id, message.from_user.username)
    inv = await db.get_inventory(message.from_user.id)
    total_value = sum(TIERS_BY_KEY[i["item_key"]].value for i in inv)
    joined = time.strftime("%d.%m.%Y", time.localtime(user["created_at"]))

    await message.answer(
        f"👤 <b>Профиль {fmt_user(user)}</b>\n\n"
        f"💰 Монеты: {user['coins']}\n"
        f"🎒 Предметов в портфеле: {len(inv)}\n"
        f"💎 Оценочная стоимость портфеля: {total_value} монет\n"
        f"📅 В игре с: {joined}"
    )


@router.message(Command("portfolio"))
async def cmd_portfolio(message: Message):
    if not await check_not_banned(message):
        return
    await db.get_or_create_user(message.from_user.id, message.from_user.username)
    inv = await db.get_inventory(message.from_user.id)
    if not inv:
        await message.answer("🎒 Твой портфель пуст. Открой кейс командой /case!")
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

    # Telegram лимит на сообщение ~4096 символов
    if len(text) > 3900:
        text = text[:3900] + "\n… список обрезан"
    await message.answer(text)


@router.message(Command("case"))
async def cmd_case(message: Message):
    if not await check_not_banned(message):
        return
    user = await db.get_or_create_user(message.from_user.id, message.from_user.username)
    price = case_price()
    if user["coins"] < price:
        await message.answer(f"💸 Недостаточно монет. Кейс стоит {price} монет.")
        return

    weights = [t.drop_weight for t in TIERS]
    chosen = random.choices(TIERS, weights=weights, k=1)[0]

    await db.add_coins(message.from_user.id, -price)
    item_id = await db.add_item(message.from_user.id, chosen.key)

    await message.answer(
        f"📦 Открываешь кейс за {price} монет...\n\n"
        f"🎉 Выпало: {chosen.emoji} <b>{chosen.title}</b> (#{item_id})\n"
        f"Стоимость: ~{chosen.value} монет\n\n"
        "Посмотреть шансы: /odds"
    )


@router.message(Command("upgrade"))
async def cmd_upgrade(message: Message):
    if not await check_not_banned(message):
        return
    await db.get_or_create_user(message.from_user.id, message.from_user.username)
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        inv = await db.get_inventory(message.from_user.id)
        if not inv:
            await message.answer("🎒 Портфель пуст, сначала открой /case.")
            return
        await message.answer(
            "Укажи номер предмета из /portfolio, например:\n<code>/upgrade 5</code>"
        )
        return

    item_id = int(parts[1])
    item = await db.get_item(item_id, message.from_user.id)
    if not item:
        await message.answer("❌ Предмет с таким номером не найден в твоём портфеле.")
        return

    tier = TIERS_BY_KEY[item["item_key"]]
    nt = next_tier(tier.key)
    if nt is None:
        await message.answer(f"{tier.emoji} {tier.title} — уже максимальный тир, апгрейдить некуда.")
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Попробовать апгрейд", callback_data=f"upg_confirm:{item_id}")
    builder.button(text="❌ Отмена", callback_data="upg_cancel")
    builder.adjust(1)

    await message.answer(
        f"⬆️ Апгрейд {tier.emoji} {tier.title} → {nt.emoji} {nt.title}\n"
        f"Шанс успеха: <b>{tier.upgrade_chance*100:.0f}%</b>\n"
        f"⚠️ При неудаче предмет будет потерян!",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == "upg_cancel")
async def cb_upgrade_cancel(callback: CallbackQuery):
    await callback.message.edit_text("Апгрейд отменён.")
    await callback.answer()


@router.callback_query(F.data.startswith("upg_confirm:"))
async def cb_upgrade_confirm(callback: CallbackQuery):
    if await db.is_banned(callback.from_user.id):
        await callback.answer("Ты забанен.", show_alert=True)
        return

    item_id = int(callback.data.split(":")[1])
    item = await db.get_item(item_id, callback.from_user.id)
    if not item:
        await callback.message.edit_text("❌ Предмет уже недоступен (возможно, уже использован).")
        await callback.answer()
        return

    tier = TIERS_BY_KEY[item["item_key"]]
    nt = next_tier(tier.key)
    if nt is None:
        await callback.message.edit_text("Этот предмет уже максимального тира.")
        await callback.answer()
        return

    success = random.random() < tier.upgrade_chance
    await db.remove_item(item_id, callback.from_user.id)

    if success:
        new_id = await db.add_item(callback.from_user.id, nt.key)
        await callback.message.edit_text(
            f"🎉 Успех! {tier.emoji} {tier.title} превратился в "
            f"{nt.emoji} <b>{nt.title}</b> (#{new_id})"
        )
    else:
        await callback.message.edit_text(
            f"💀 Неудача! {tier.emoji} {tier.title} потерян навсегда.\n"
            "Не переживай, это просто игра — попробуй ещё раз с /case"
        )
    await callback.answer()


@router.message(Command("top_coins"))
async def cmd_top_coins(message: Message):
    top = await db.top_by_coins(10)
    if not top:
        await message.answer("Пока никого нет в топе.")
        return
    medals = ["🥇", "🥈", "🥉"]
    lines = ["💰 <b>Топ по монетам</b>\n"]
    for i, u in enumerate(top):
        prefix = medals[i] if i < 3 else f"{i+1}."
        lines.append(f"{prefix} {fmt_user(u)} — {u['coins']} монет")
    await message.answer("\n".join(lines))


@router.message(Command("top_items"))
async def cmd_top_items(message: Message):
    top = await db.top_by_items(10)
    if not top:
        await message.answer("Пока никого нет в топе.")
        return
    medals = ["🥇", "🥈", "🥉"]
    lines = ["🎒 <b>Топ по количеству предметов</b>\n"]
    for i, u in enumerate(top):
        prefix = medals[i] if i < 3 else f"{i+1}."
        lines.append(f"{prefix} {fmt_user(u)} — {u['item_count']} предметов")
    await message.answer("\n".join(lines))
