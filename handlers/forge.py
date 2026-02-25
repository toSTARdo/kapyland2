import json
import asyncio
from aiogram import types, F, Router
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import load_game_data, DISPLAY_NAMES
from database.postgres_db import get_db_connection

router = Router()

FORGE_RECIPES = load_game_data("data/forge_recipes.json")

def find_item_in_inventory(inv, item_key):
    for category in ["food", "materials", "plants", "loot"]:
        count = inv.get(category, {}).get(item_key)
        if count is not None:
            return category, count
    return None, 0

@router.callback_query(F.data == "open_forge")
async def process_open_forge(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT lvl, meta FROM capybaras WHERE owner_id = $1", user_id)
        
        if row['lvl'] < 10:
            return await callback.answer("🔒 Кузня доступна лише з 10 рівня!", show_alert=True)

        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        inv = meta.get('inventory', {})
        _, kiwi_count = find_item_in_inventory(inv, "kiwi")

        builder = InlineKeyboardBuilder()
        builder.button(text="🔨 Покращити спорядження (5 🥝)", callback_data="upgrade_menu")
        builder.button(text="⚒️ Крафт нових речей (Lvl 30)", callback_data="forge_craft_list")
        builder.button(text="⬅️ Назад", callback_data="open_port")
        builder.adjust(1)

        text = (
            "🐦 <b>Кузня ківі</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Тут пахне сталлю та тропічними фруктами.\n"
            f"Твій запас ківі: <b>{kiwi_count} 🥝</b>\n\n"
            "<i>«Гей, пухнастий! Хочеш гостріший ніж чи міцніший панцир?\n Можливості залежать від кількості ківі в твоїх кишенях»</i>"
        )
        
        await callback.message.edit_caption(caption=text, reply_markup=builder.as_markup(), parse_mode="HTML")
    finally:
        await conn.close()

@router.callback_query(F.data == "upgrade_menu")
async def upgrade_list(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = await get_db_connection()
    row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", user_id)
    meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
    await conn.close()

    equip = meta.get("equipment", {})
    builder = InlineKeyboardBuilder()

    for slot, item_name in equip.items():
        if item_name and item_name not in ["Лапки", "Хутро"]:
            builder.button(text=f"💎 {item_name}", callback_data=f"up_item:{slot}")

    builder.button(text="⬅️ Назад", callback_data="open_forge")
    builder.adjust(1)

    await callback.message.edit_caption(
        caption="🛠️ <b>Яку річ хочеш загартувати?</b>\nВартість: <b>5 🥝</b> за +1 рівень.",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("up_item:"))
async def confirm_upgrade(callback: types.CallbackQuery):
    slot = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", user_id)
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        inv = meta.get("inventory", {})
        
        cat, kiwi_count = find_item_in_inventory(inv, "kiwi")
        if kiwi_count < 5:
            return await callback.answer("❌ Бракує ківі! Потрібно 5 🥝", show_alert=True)

        current_name = meta["equipment"][slot]
        inv[cat]["kiwi"] -= 5
        
        if "+" in current_name:
            base_name, lvl = current_name.split(" +")
            new_name = f"{base_name} +{int(lvl) + 1}"
        else:
            new_name = f"{current_name} +1"
            
        meta["equipment"][slot] = new_name

        await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(meta, ensure_ascii=False), user_id)
        await callback.answer(f"🔥 Успішно! Тепер у тебе {new_name}")
        await upgrade_list(callback)
    finally:
        await conn.close()

@router.callback_query(F.data == "forge_craft_list")
async def forge_craft_list(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = await get_db_connection()
    row = await conn.fetchrow("SELECT lvl FROM capybaras WHERE owner_id = $1", user_id)
    await conn.close()

    if row['lvl'] < 30:
        return await callback.answer("❌ Складна робота! Повертайся на 30 рівні.", show_alert=True)

    builder = InlineKeyboardBuilder()
    for r_id, r_data in FORGE_RECIPES.items():
        builder.button(text=f"⚒️ {r_data.get('name')}", callback_data=f"fbrew:{r_id}")
    
    builder.button(text="⬅️ Назад", callback_data="open_forge")
    builder.adjust(1)
    await callback.message.edit_caption(caption="⚒️ <b>Доступні креслення:</b>", reply_markup=builder.as_markup(), parse_mode="HTML")

