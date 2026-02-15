import asyncio, json, random
from aiogram import Router, types, html, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.capybara_mechanics import get_user_inventory
from database.postgres_db import get_db_connection
from config import ARTIFACTS, RARITY_META
GACHA_ITEMS = ARTIFACTS

router = Router()

import json
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

async def render_inventory_page(message, user_id, page="food", current_page=0, is_callback=False):
    meta_data = await get_user_inventory(user_id)
    if not meta_data:
        return await message.answer("❌ Профіль не знайдено.")

    meta = json.loads(meta_data) if isinstance(meta_data, str) else meta_data
    inv = meta.get("inventory", {})
    builder = InlineKeyboardBuilder()
    
    title = ""
    content = ""
    ITEMS_PER_PAGE = 5

    if page == "food":
        title = "🍎 <b>Провізія</b>"
        food = inv.get("food", {})
        food_names = {"tangerines": "🍊", "melon": "🍈", "watermelon_slices": "🍉", "mango": "🥭", "kiwi": "🥝"}
        active_food = {k: v for k, v in food.items() if v > 0}
        if not active_food:
            content = "<i>Твій кошик порожній...</i>"
        else:
            content = "<i>Обери їжу:</i>"
            for k, v in active_food.items():
                icon = food_names.get(k, "🍱")
                builder.row(types.InlineKeyboardButton(text=f"{icon} ({v})", callback_data=f"food_choice:{k}"))

    elif page == "loot":
        title = "🧳 <b>Скарби та ресурси</b>"
        loot = inv.get("loot", {})
        loot_lines = [f"🎟️ Квитки: <b>{loot.get('lottery_ticket', 0)}</b>", 
                      f"🗝️ Ключі: <b>{loot.get('key', 0)}</b>", 
                      f"🗃 Скрині: <b>{loot.get('chest', 0)}</b>"]
        content = "\n".join([line for line in loot_lines if "<b>0</b>" not in line]) or "<i>Твій сейф порожній...</i>"
        if loot.get('chest', 0) > 0 and loot.get('key', 0) > 0:
            builder.row(types.InlineKeyboardButton(text="🔓 Відкрити скриню", callback_data="open_chest"))

    elif page == "items":
        title = "⚔️ <b>Амуніція</b>"
        curr_equip = meta.get("equipment", {})
        all_items = inv.get("equipment", [])
        if not all_items:
            content = "<i>Твій трюм порожній...</i>"
        else:
            unique_list = []
            seen = {}
            for item in all_items:
                name = item['name']
                if name not in seen:
                    seen[name] = len(unique_list)
                    unique_list.append({"data": item, "count": 1})
                else:
                    unique_list[seen[name]]["count"] += 1
            
            items_slice = unique_list[current_page * ITEMS_PER_PAGE : (current_page + 1) * ITEMS_PER_PAGE]
            SELL_PRICES = {"Common": 1, "Rare": 2, "Epic": 3, "Legendary": 5}
            
            for info in items_slice:
                item, count = info["data"], info["count"]
                name, rarity = item['name'], item.get('rarity', 'Common')
                is_equipped = (name == curr_equip.get("weapon") or name == curr_equip.get("armor"))
                r_icon = RARITY_META.get(rarity, {}).get('emoji', '⚪')
                price = SELL_PRICES.get(rarity, 1)
                builder.row(
                    types.InlineKeyboardButton(text=f"{r_icon} {name} x{count}{' ✅' if is_equipped else ''}", callback_data=f"equip:item:{name}"),
                    types.InlineKeyboardButton(text=f"💰 {price}", callback_data=f"sell:{rarity}:{name}")
                )
            
            if len(unique_list) > ITEMS_PER_PAGE:
                max_p = (len(unique_list) - 1) // ITEMS_PER_PAGE
                nav = []
                if current_page > 0: nav.append(types.InlineKeyboardButton(text="⬅️", callback_data=f"inv_page:{page}:{current_page-1}"))
                nav.append(types.InlineKeyboardButton(text=f"{current_page+1}/{max_p+1}", callback_data="none"))
                if current_page < max_p: nav.append(types.InlineKeyboardButton(text="➡️", callback_data=f"inv_page:{page}:{current_page+1}"))
                builder.row(*nav)
            content = "Обери спорядження:"

    elif page == "materials":
        title = "📦 <b>Ресурси</b>"
        mats = inv.get("materials", {})
        names = {"carp": "🐟 Карась", "perch": "🐠 Окунь", "herbs": "🌿 Трави", "wood": "🪵 Дерево"}
        mat_lines = [f"{names.get(k, k)}: <b>{v}</b>" for k, v in mats.items() if v > 0]
        content = "Твої запаси:\n\n" + "\n".join(mat_lines) if mat_lines else "<i>Трюм порожній.</i>"

    elif page == "maps":
        title = "🗺 <b>Карти скарбів</b>"
        maps = inv.get("loot", {}).get("treasure_maps", [])
        content = "<i>Твої замітки:</i>\n\n" + "\n\n".join([f"📍 <b>Карта {m['id']}</b>\n╰ <code>{m['pos']}</code>" for m in maps]) if maps else "<i>Карт немає.</i>"

    pages_meta = {"food": "🍎 Їжа", "loot": "🧳 Лут", "maps": "🗺 Мапи", "items": "⚔️ Речі", "materials": "🌱 Матеріали"}
    cat_builder = InlineKeyboardBuilder()
    for p_key, p_text in pages_meta.items():
        cat_builder.button(text=f"· {p_text} ·" if page == p_key else p_text, callback_data=f"inv_page:{p_key}:0")
    cat_builder.adjust(2, 2, 1)
    
    builder.attach(cat_builder)
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад до Трюму", callback_data="back_to_main"))
    
    text = f"{title}\n━━━━━━━━━━━━━━━\n{content}"
    if is_callback:
        try:
            await message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        except:
            pass
    else:
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.startswith("inv_pagination:"))
async def handle_inv_pagination(callback: types.CallbackQuery):
    _, category, p_idx = callback.data.split(":")
    await render_inventory_page(
        callback.message, 
        callback.from_user.id, 
        page=category, 
        current_page=int(p_idx), 
        is_callback=True
    )
    await callback.answer()

@router.callback_query(F.data.startswith("sell_item:"))
async def handle_sell_equipment(callback: types.CallbackQuery):
    _, rarity, item_name = callback.data.split(":")
    uid = callback.from_user.id
    
    prices = {"Common": 1, "Rare": 2, "Epic": 3, "Legendary": 5}
    reward = prices.get(rarity, 1)
    
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
        if not row: return
        
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        
        curr_eq = meta.get("equipment", {})
        if item_name in [curr_eq.get("weapon"), curr_eq.get("armor"), curr_eq.get("artifact")]:
            return await callback.answer("❌ Спочатку зніми цей предмет!", show_alert=True)

        inventory_eq = meta.get("inventory", {}).get("equipment", [])
        
        found_index = -1
        for i, it in enumerate(inventory_eq):
            if it.get("name") == item_name:
                found_index = i
                break
        
        if found_index == -1:
            return await callback.answer("❌ Предмет не знайдено в інвентарі.")

        inventory_eq.pop(found_index)
        
        food_dict = meta.get("inventory", {}).get("food", {})
        current_slices = food_dict.get("watermelon_slices", 0)
        
        food_dict["watermelon_slices"] = current_slices + reward
        meta["inventory"]["food"] = food_dict
        meta["inventory"]["equipment"] = inventory_eq

        await conn.execute(
            "UPDATE capybaras SET meta = $1 WHERE owner_id = $2", 
            json.dumps(meta), uid
        )

        await callback.answer(f"🍉 Продано! Отримано {reward} скибочок кавуна.")

    finally:
        await conn.close()

@router.message(F.text.startswith("🎒"))
async def show_inventory_start(message: types.Message):
    await render_inventory_page(message, message.from_user.id, page="food")

@router.callback_query(F.data.startswith("equip:"))
async def handle_equip_item(callback: types.CallbackQuery):
    _, itype, iname = callback.data.split(":")
    user_id = callback.from_user.id
    
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", user_id)
        if not row: return await callback.answer("Де твоя капібара?")
            
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        
        if "equipment" not in meta:
            meta["equipment"] = {"weapon": "Лапки", "armor": ""}
            
        current_item = meta["equipment"].get(itype)
        
        if current_item == iname:
            default_val = "Лапки" if itype == "weapon" else ""
            meta["equipment"][itype] = default_val
            msg = f"❌ Знято: {iname}"
        else:
            meta["equipment"][itype] = iname
            msg = f"✅ Одягнено: {iname}"
            
        await conn.execute(
            "UPDATE capybaras SET meta = $1 WHERE owner_id = $2",
            json.dumps(meta, ensure_ascii=False), user_id
        )
        
        await callback.answer(msg)
        await render_inventory_page(callback.message, user_id, page="items", is_callback=True)
        
    finally:
        await conn.close()

@router.callback_query(F.data.startswith("inv_page:"))
async def handle_inventory_pagination(callback: types.CallbackQuery):
    page = callback.data.split(":")[1]
    await render_inventory_page(callback.message, callback.from_user.id, page=page, is_callback=True)
    await callback.answer()