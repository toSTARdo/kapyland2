import asyncio
import json
import random
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import RARITY_META, ARTIFACTS
from database.postgres_db import get_db_connection

GACHA_ITEMS = ARTIFACTS
router = Router()

@router.message(F.text == "🎟️ Лотерея")
@router.message(Command("lottery"))
async def cmd_lottery_start(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="🏴‍☠️ Крутити (1🎟 або 5кг)", callback_data="gacha_spin")
    builder.adjust(1)
    
    c, r, e, l = RARITY_META['common'], RARITY_META['rare'], RARITY_META['epic'], RARITY_META['legendary']

    await message.answer(
        f"🎰 <b>ГАЗИНО</b>\n\n"
        f"Ціна: 1 лотерейний квиток 🎟\n"
        f"<i>Або 5 кг власної ваги, якщо квитків немає!</i>\n\n"
        f"{c['emoji']} {c['label']}: 60%\n"
        f"{r['emoji']} {r['label']}: 25%\n"
        f"{e['emoji']} {e['label']}: 12%\n"
        f"{l['emoji']} {l['label']}: 3%\n",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "gacha_spin")
async def handle_gacha_spin(callback: types.CallbackQuery):
    uid = callback.from_user.id
    
    payment_status, meta = await check_and_pay_for_spin(uid)
    
    if payment_status == "no_balance":
        return await callback.answer("❌ Ти занадто худий для цього! Треба хоча б 5 кг.", show_alert=True)
    
    pay_msg = "🎟 Використано квиток!" if payment_status == "ticket" else "⚖️ Списано 5 кг ваги!"
    await callback.message.edit_text(f"🌀 {pay_msg}\n<i>Крутимо барабан...</i>", parse_mode="HTML")
    await asyncio.sleep(1.5)
    
    rarity_key = random.choices(
        ["Common", "Rare", "Epic", "Legendary"],
        weights=[60, 25, 12, 3],
        k=1
    )[0]

    item = random.choice(GACHA_ITEMS[rarity_key])  

    await save_gacha_result(uid, meta, item, rarity_key)

    rarity_info = RARITY_META[rarity_key]
    res_text = (
        f"🎉 <b>ТВІЙ ЛУТ!</b>\n\n"
        f"📦 Предмет: <b>{item['name']}</b>\n"
        f"{rarity_info['emoji']} Рідкість: <b>{rarity_info['label']}</b>\n"
        f"🛠 Тип: {item['type'].capitalize()}\n"
        f"━━━━━━━━━━━━━━\n"
        f"📜 <i>{item['desc']}</i>"
    )

    await callback.message.edit_text(res_text, parse_mode="HTML")
    await callback.answer()

async def check_and_pay_for_spin(uid: int):
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
        if not row: return "no_user", None
        
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        inventory = meta.setdefault("inventory", {})
        loot = inventory.setdefault("loot", {})
        
        tickets = loot.get("lottery_ticket", 0)
        if tickets > 0:
            loot["lottery_ticket"] -= 1
            status = "ticket"
        else:
            current_weight = meta.get("weight", 0)
            if current_weight >= 5.1:
                meta["weight"] -= 5.0
                status = "weight"
            else:
                return "no_balance", None

        await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(meta), uid)
        return status, meta
    finally:
        await conn.close()

async def save_gacha_result(uid: int, meta: dict, item: dict, rarity: str):
    inventory = meta.setdefault("inventory", {})
    equipment = inventory.setdefault("equipment", [])
    
    equipment.append({
        "name": item["name"],
        "type": item["type"],
        "rarity": rarity,
        "desc": item["desc"]
    })
    
    conn = await get_db_connection()
    try:
        await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(meta), uid)
    finally:
        await conn.close()