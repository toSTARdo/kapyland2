import asyncio, json, random
from aiogram import Router, types, html, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.capybara_mechanics import get_user_inventory
from database.postgres_db import get_db_connection
from config import ARTIFACTS, RARITY_META, DISPLAY_NAMES
from config import load_game_data
GACHA_ITEMS = ARTIFACTS

RECIPES = load_game_data("data/craft.json")

router = Router()

async def render_inventory_page(message, user_id, page="food", current_page=0, is_callback=False):
    meta_data = await get_user_inventory(user_id)
    if not meta_data:
        return await message.answer("❌ Профіль не знайдено.")

    meta = json.loads(meta_data) if isinstance(meta_data, str) else meta_data
    inv = meta.get("inventory", {})
    builder = InlineKeyboardBuilder()
    
    ITEMS_PER_PAGE = 5
    TYPE_ICONS = {"weapon": "🗡️", "armor": "🔰", "artifact": "🧿"}
    title, content = "", ""

    if page == "food":
        title = "🍎 <b>Провізія</b>"
        food = inv.get("food", {})
        food_names = {"tangerines": "🍊", "melon": "🍈", "watermelon_slices": "🍉", "mango": "🥭", "kiwi": "🥝"}
        active_food = {k: v for k, v in food.items() if v > 0}
        
        if not active_food:
            content = "<i>Твій кошик порожній... Пошукай щось на мапі!</i>"
        else:
            content = "<i>Обери їжу:</i>"
            for k, v in active_food.items():
                icon = food_names.get(k, "🍱")
                builder.button(text=f"{icon} ({v})", callback_data=f"food_choice:{k}")
        builder.adjust(2)

    elif page == "potions":
        title = "🧪 <b>Зілля</b>"
        potions = inv.get("potions", {})
        
        active_potions = {k: v for k, v in potions.items() if v > 0}
        
        if not active_potions:
            content = "<i>У тебе немає готових зілль. Зазирни до Омо!</i>"
        else:
            content = "<i>Твої магічні шмурдяки:</i>"
            for p_id, count in active_potions.items():
                recipe_info = RECIPES.get(p_id, {})
                p_name = recipe_info.get("name", p_id)
                p_emoji = recipe_info.get("emoji", "🧪")
                
                builder.row(types.InlineKeyboardButton(
                    text=f"{p_emoji} {p_name} ({count})", 
                    callback_data=f"use_potion:{p_id}"
                ))

    elif page == "items":
        title = "⚔️ <b>Амуніція</b>"
        selected_key = None
        if ":" in page and len(page.split(":")) > 1:
            _, selected_key = page.split(":", 1)
            page_type = "items"
        else:
            page_type = "items"

        curr_equip = meta.get("equipment", {})
        all_items = inv.get("equipment", [])
        
        if not all_items:
            content = "<i>Твій трюм порожній...</i>"
        else:
            unique_list = []
            seen = {}
            for item in all_items:
                if isinstance(item, str): item = {"name": item, "lvl": 0, "type": "artifact", "rarity": "Common"}
                n, l = item.get('name', '???'), item.get('lvl', 0)
                k = f"{n}_{l}"
                if k not in seen:
                    seen[k] = len(unique_list)
                    unique_list.append({"data": item, "count": 1, "key": k})
                else:
                    unique_list[seen[k]]["count"] += 1
            
            max_p = (len(unique_list) - 1) // ITEMS_PER_PAGE
            items_slice = unique_list[current_page * ITEMS_PER_PAGE : (current_page + 1) * ITEMS_PER_PAGE]
            SELL_PRICES = {"Common": 1, "Rare": 2, "Epic": 3, "Legendary": 5, "Mythic": 10}

            for info in items_slice:
                item, count, k = info["data"], info["count"], info["key"]
                name, rarity, lvl = item['name'], item.get('rarity', 'Common'), item.get('lvl', 0)
                i_type = item.get('type', 'artifact')
                
                t_icon = TYPE_ICONS.get(i_type, "🧿")
                r_icon = RARITY_META.get(rarity, {}).get('emoji', '⚪')
                stars = "⭐" * lvl if lvl > 0 else ""
                
                is_eq = False
                if isinstance(curr_equip, dict):
                    for slot, eq_val in curr_equip.items():
                        en = eq_val.get("name") if isinstance(eq_val, dict) else eq_val
                        el = eq_val.get("lvl", 0) if isinstance(eq_val, dict) else 0
                        if en == name and el == lvl:
                            is_eq = True; break
                
                status = " ✅" if is_eq else ""
                
                builder.row(types.InlineKeyboardButton(
                    text=f"{r_icon}{t_icon} {name} {stars} x{count}{status}", 
                    callback_data=f"inv_page:items:{current_page}:{k}" 
                ))

                if selected_key == k:
                    price = SELL_PRICES.get(rarity, 1) + lvl
                    desc = item.get("desc", "Опис відсутній.")
                    content = f"<b>{r_icon} {name} {stars}</b>\n<i>{desc}</i>\n\nЦіна продажу: {price} 🍉"
                    
                    sub_btns = [
                        types.InlineKeyboardButton(text="⚔️ Одягнути", callback_data=f"equip:{i_type}:{name}:{lvl}"),
                        types.InlineKeyboardButton(text=f"💰 Продати ({price}🍉)", callback_data=f"sell_item:{rarity}:{name}:{lvl}")
                    ]
                    builder.row(*sub_btns)

            if len(unique_list) > ITEMS_PER_PAGE:
                nav = []
                if current_page > 0: 
                    nav.append(types.InlineKeyboardButton(text="⬅️", callback_data=f"inv_page:items:{current_page-1}"))
                nav.append(types.InlineKeyboardButton(text=f"{current_page+1}/{max_p+1}", callback_data="none"))
                if current_page < max_p: 
                    nav.append(types.InlineKeyboardButton(text="➡️", callback_data=f"inv_page:items:{current_page+1}"))
                builder.row(*nav)

    elif page == "loot":
        title = "🧳 <b>Скарби</b>"
        loot = inv.get("loot", {})
        loot_lines = [f"🎟️ Квитки: <b>{loot.get('lottery_ticket', 0)}</b>", 
                      f"🗝️ Ключі: <b>{loot.get('key', 0)}</b>", 
                      f"🗃 Скрині: <b>{loot.get('chest', 0)}</b>"]
        content = "\n".join([l for l in loot_lines if "<b>0</b>" not in l]) or "<i>Твій сейф порожній...</i>"
        if loot.get('chest', 0) > 0 and loot.get('key', 0) > 0:
            builder.row(types.InlineKeyboardButton(text="🔓 Відкрити скриню", callback_data="open_chest"))

    elif page == "materials":
        title = "📦 <b>Ресурси</b>"
        mats = inv.get("materials", {})
        mat_lines = [f"{DISPLAY_NAMES.get(k, k.capitalize())}: <b>{v}</b>" for k, v in mats.items() if v > 0]
        content = "Твої запаси:\n\n" + "\n".join(mat_lines) if mat_lines else "<i>Твій трюм порожній...</i>"

    elif page == "maps":
        title = "🗺 <b>Карти скарбів</b>"
        maps = inv.get("loot", {}).get("treasure_maps", [])
        content = "\n".join([f"📍 <b>Карта {m['id']}</b>\n╰ <code>{m['pos']}</code>" for m in maps]) if maps else "<i>У тебе немає жодної карти.</i>"

    if page != "items":
        pages_meta = {
            "food": "🍎 Їжа", 
            "potions": "🧪 Зілля",
            "loot": "🧳 Лут", 
            "maps": "🗺 Мапи", 
            "items": "⚔️ Речі", 
            "materials": "🌱 Матеріали"
        }
        nav_builder = InlineKeyboardBuilder()
        for p_key, p_text in pages_meta.items():
            if page != p_key:
                nav_builder.button(text=p_text, callback_data=f"inv_page:{p_key}:0")
        nav_builder.adjust(2)
        builder.attach(nav_builder)

    builder.row(types.InlineKeyboardButton(text="⬅️ Назад до Трюму", callback_data="open_inventory_main"))
    
    text = f"{title}\n━━━━━━━━━━━━━━━\n{content}"
    markup = builder.as_markup()

    if is_callback:
        try:
            await message.edit_text(text, reply_markup=markup, parse_mode="HTML")
        except:
            pass
    else:
        await message.answer(text, reply_markup=markup, parse_mode="HTML")

@router.callback_query(F.data.startswith("inv_page:"))
async def handle_inventory_pagination(callback: types.CallbackQuery):
    data = callback.data.split(":")
    page_type = data[1]
    
    if len(data) > 2 and data[2].isdigit():
        p_idx = int(data[2])
        selected_item = data[3] if len(data) > 3 else None
    else:
        p_idx = int(data[3]) if len(data) > 3 and data[3].isdigit() else 0
        selected_item = data[2] if len(data) > 2 else None

    target_page = f"{page_type}:{selected_item}" if selected_item else page_type
    
    await render_inventory_page(
        callback.message, 
        callback.from_user.id, 
        page=target_page, 
        current_page=p_idx, 
        is_callback=True
    )

@router.callback_query(F.data.startswith("sell_item:"))
async def handle_sell_equipment(callback: types.CallbackQuery):
    _, rarity, item_name = callback.data.split(":")
    uid = callback.from_user.id
    
    prices = {"Common": 1, "Rare": 2, "Epic": 3, "Legendary": 5}
    reward = prices.get(rarity, 1)
    
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        
        curr_eq = meta.get("equipment", {})
        if item_name in [curr_eq.get("weapon"), curr_eq.get("armor"), curr_eq.get("artifact")]:
            return await callback.answer("❌ Спочатку зніми цей предмет!", show_alert=True)

        inv_eq = meta.get("inventory", {}).get("equipment", [])
        
        found = False
        for i, it in enumerate(inv_eq):
            if it.get("name") == item_name:
                inv_eq.pop(i)
                found = True
                break
        
        if not found: return await callback.answer("❌ Предмет зник...")

        food = meta.get("inventory", {}).get("food", {})
        food["watermelon_slices"] = food.get("watermelon_slices", 0) + reward
        
        await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(meta), uid)
        await callback.answer(f"🍉 +{reward} скибочок за {item_name}")
        await render_inventory_page(callback.message, uid, page="items", is_callback=True)
    finally:
        await conn.close()

@router.message(F.text.startswith("🎒"))
@router.callback_query(F.data == "open_inventory_main")
async def show_inventory_start(event: types.Message | types.CallbackQuery):
    is_callback = isinstance(event, types.CallbackQuery)
    message = event.message if is_callback else event
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🧺 Відкрити інвентар", callback_data="inv_page:food:0"))
    builder.row(types.InlineKeyboardButton(text="🎟️ Відкрити Газино", callback_data="lottery_menu"))

    text = "<i>Тут всі твої предмети та можна відвідати казино</i>"
    markup = builder.as_markup()

    if is_callback:
        if event.message.photo:
            await event.message.delete()
            await event.message.answer(text, reply_markup=markup, parse_mode="HTML")
        else:
            await event.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
        
        await event.answer()
        return

    await message.answer(text, reply_markup=markup, parse_mode="HTML")

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
            meta["equipment"] = {"weapon": "Лапки", "armor": "", "artifact": ""}
            
        current_item = meta["equipment"].get(itype)
        
        if current_item == iname:
            meta["equipment"][itype] = "Лапки" if itype == "weapon" else ""
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
    data = callback.data.split(":")
    category = data[1]
    p_idx = int(data[2]) if len(data) > 2 else 0
    
    await render_inventory_page(
        callback.message, 
        callback.from_user.id, 
        page=category, 
        current_page=p_idx, 
        is_callback=True
    )
    await callback.answer()
