import asyncio
import json
import random
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import datetime

from config import RARITY_META, ARTIFACTS
from database.postgres_db import get_db_connection

GACHA_ITEMS = ARTIFACTS
router = Router()

async def is_eligible_for_lega(meta: dict) -> bool:
    last_lega_str = meta.get("last_weekly_lega")
    if not last_lega_str:
        return True
    
    last_lega_date = datetime.datetime.fromisoformat(last_lega_str)
    return datetime.datetime.now() >= last_lega_date + datetime.timedelta(days=7)

@router.message(F.text.startswith("🎟️"))
@router.callback_query(F.data == "lottery_menu")
async def cmd_lottery_start(event: types.Message | types.CallbackQuery):
    is_callback = isinstance(event, types.CallbackQuery)
    uid = event.from_user.id
    
    conn = await get_db_connection()
    row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
    await conn.close()

    can_get_lega = True
    if row:
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        can_get_lega = await is_eligible_for_lega(meta)

    label = "LEGENDARY" if can_get_lega else "EPIC"
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🏴‍☠️ Крутити (1🎟 / 5кг)", callback_data="gacha_spin"))
    builder.row(types.InlineKeyboardButton(text=f"🔥 10+1 / 100% {label} (10🎟)", callback_data="gacha_guaranteed_10"))
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="open_inventory_main"))

    c, r, e, l = RARITY_META['Common'], RARITY_META['Rare'], RARITY_META['Epic'], RARITY_META['Legendary']

    text = (
        f"🎰 <b>ГАЗИНО «ФОРТУНА КАПІ»</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Ціна: 1 🎟 або <b>5 кг</b> ваги\n\n"
        f"{c['emoji']} {c['label']}: 60%\n"
        f"{r['emoji']} {r['label']}: 25%\n"
        f"{e['emoji']} {e['label']}: 12%\n"
        f"{l['emoji']} {l['label']}: 3%\n\n"
        f"<i>Удача посміхається сміливим!</i>"
    )

    if is_callback:
        try:
            await event.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        except:
            pass
        await event.answer()
    else:
        await event.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

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
        f"🎉 <b>ТВІЙ ПРИЗ!</b>\n\n"
        f"📦 Предмет: <b>{item['name']}</b>\n"
        f"{rarity_info['emoji']} Рідкість: <b>{rarity_info['label']}</b>\n"
        f"🛠 Тип: {item['type'].capitalize()}\n"
        f"━━━━━━━━━━━━━━\n"
        f"📜 <i>{item['desc']}</i>"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Крутити ще (1🎟/5кг)", callback_data="gacha_spin")
    builder.adjust(1)

    await callback.message.edit_text(
            res_text, 
            reply_markup=builder.as_markup(), 
            parse_mode="HTML"
        )
    await callback.answer()

@router.callback_query(F.data == "gacha_guaranteed_10")
async def handle_bulk_spin(callback: types.CallbackQuery):
    uid = callback.from_user.id
    conn = await get_db_connection()
    now = datetime.datetime.now()
    
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
        if not row:
            return await callback.answer("❌ Капібару не знайдено!", show_alert=True)
        
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        inventory = meta.setdefault("inventory", {})
        loot = inventory.setdefault("loot", {})
        tickets = loot.get("lottery_ticket", 0)
        
        if tickets < 10:
            return await callback.answer(f"❌ Треба 🎟️x10, а маєш лише 🎟️x{tickets}", show_alert=True)
        
        can_get_lega = await is_eligible_for_lega(meta)

        await callback.answer("🎰 КРУТИМО БАРАБАН (10+1)...")

        equipment = inventory.setdefault("equipment", [])
        owned_names = [i["name"] for i in equipment]
        
        results_icons = []
        watermelons_gain = 0
        new_items_count = 0
        used_weekly_bonus = False

        for i in range(11):
            if i == 10:
                if can_get_lega:
                    rarity = "Legendary"
                    used_weekly_bonus = True
                else:
                    rarity = "Epic"
            else:
                r = random.random()
                if r < 0.03: rarity = "Legendary"
                elif r < 0.15: rarity = "Epic"
                elif r < 0.40: rarity = "Rare"
                else: rarity = "Common"

            item = random.choice(GACHA_ITEMS[rarity])
            item_name = item["name"]
            prefix = RARITY_META[rarity]["emoji"]

            if item_name in owned_names:
                compensation = {"Common": 1, "Rare": 2, "Epic": 3, "Legendary": 5}
                gain = compensation.get(rarity, 1)
                
                food = inventory.setdefault("food", {})
                food["watermelon_slices"] = food.get("watermelon_slices", 0) + gain
                watermelons_gain += gain
                results_icons.append(f"{prefix} <s>{item_name}</s> 🍉+{gain}")
            else:
                equipment.append({
                    "name": item_name, "type": item["type"],
                    "rarity": rarity, "desc": item["desc"]
                })
                owned_names.append(item_name)
                new_items_count += 1
                results_icons.append(f"{prefix} <b>{item_name}</b>")

        if used_weekly_bonus:
            meta["last_weekly_lega"] = now.isoformat()

        loot["lottery_ticket"] -= 10
        await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(meta), uid)
        
        status_msg = "🌟 <b>ВИКОРИСТАНО ЩОТИЖНЕВИЙ ГАРАНТ!</b>" if used_weekly_bonus else "💎 Гарант: Epic"
        
        res_list = "\n".join(results_icons)
        text = (
            f"🎰 <b>МЕГА КУШ: 10 + 1 БОНУС</b>\n"
            f"________________________________\n\n"
            f"{res_list}\n"
            f"________________________________\n"
            f"{status_msg}\n"
            f"🎁 Нових предметів: <b>{new_items_count}</b>\n"
            f"🍉 Нарізано з повторок: <b>{watermelons_gain}</b>\n"
            f"🎟️ Залишилось квитків: <b>{loot['lottery_ticket']}</b>"
        )
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🎰 Знову (🎟️x10)", callback_data="gacha_guaranteed_10")
        builder.button(text="🔙 Назад", callback_data="lottery")
        builder.adjust(1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")

    finally:
        await conn.close()

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