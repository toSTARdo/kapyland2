import json
import asyncio
from aiogram import types, F, Router
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import load_game_data, DISPLAY_NAMES
from database.postgres_db import get_db_connection

router = Router()

FORGE_RECIPES = load_game_data("data/forge_craft.json")

def find_item_in_inventory(inv, item_key):
    for category in ["food", "materials", "plants", "loot"]:
        cat_dict = inv.get(category)
        if isinstance(cat_dict, dict):
            count = cat_dict.get(item_key)
            if count is not None:
                return category, count
    return None, 0

@router.callback_query(F.data == "open_forge")
async def process_open_forge(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT lvl, meta FROM capybaras WHERE owner_id = $1", user_id)
        if not row: return

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
            "Твій запас ківі: <b>{kiwi_count} 🥝</b>\n\n"
            "<i>«Гей, пухнастий! Хочеш гостріший ніж чи міцніший панцир?\n Можливості залежать від кількості ківі в твоїх кишенях»</i>"
        ).format(kiwi_count=kiwi_count)
        
        await callback.message.edit_caption(caption=text, reply_markup=builder.as_markup(), parse_mode="HTML")
    finally:
        await conn.close()

@router.callback_query(F.data == "upgrade_menu")
async def upgrade_list(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", user_id)
        if not row: return
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        
        inv = meta.get("inventory", {})
        equip = inv.get("equipment", {})
        
        builder = InlineKeyboardBuilder()

        if isinstance(equip, dict):
            for slot, item_data in equip.items():
                item_name = item_data if isinstance(item_data, str) else item_data.get("name")
                if item_name and item_name not in ["Лапки", "Хутро", "Нічого"]:
                    builder.button(text=f"💎 {item_name}", callback_data=f"up_item:{slot}")
        elif isinstance(equip, list):
            for index, item_data in enumerate(equip):
                item_name = item_data if isinstance(item_data, str) else item_data.get("name")
                if item_name and item_name not in ["Лапки", "Хутро", "Нічого"]:
                    builder.button(text=f"💎 {item_name}", callback_data=f"up_item:{index}")

        builder.button(text="⬅️ Назад", callback_data="open_forge")
        builder.adjust(1)

        await callback.message.edit_caption(
            caption="🛠️ <b>Загартування спорядження</b>\n\nОбери предмет, який хочеш посилити.\nВартість: <b>5 🥝</b>",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    finally:
        await conn.close()

@router.callback_query(F.data.startswith("up_item:"))
async def confirm_upgrade(callback: types.CallbackQuery):
    slot_key = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", user_id)
        if not row: return
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        inv = meta.get("inventory", {})
        equip = inv.get("equipment", {})
        
        cat, kiwi_count = find_item_in_inventory(inv, "kiwi")
        if kiwi_count < 5:
            return await callback.answer("❌ Бракує ківі! Потрібно 5 🥝", show_alert=True)

        if isinstance(equip, list):
            try:
                slot_key = int(slot_key)
                item_data = equip[slot_key]
            except (ValueError, IndexError):
                return await callback.answer("❌ Предмет не знайдено")
        else:
            item_data = equip.get(slot_key)

        if not item_data:
            return await callback.answer("❌ Предмет не знайдено")

        current_name = item_data if isinstance(item_data, str) else item_data.get("name")
        
        inv[cat]["kiwi"] -= 5
        
        if " +" in current_name:
            base_name, lvl = current_name.rsplit(" +", 1)
            new_name = f"{base_name} +{int(lvl) + 1}"
        else:
            new_name = f"{current_name} +1"
            
        if isinstance(equip, list):
            if isinstance(equip[slot_key], dict):
                equip[slot_key]["name"] = new_name
            else:
                equip[slot_key] = new_name
        else:
            if isinstance(equip[slot_key], dict):
                equip[slot_key]["name"] = new_name
            else:
                equip[slot_key] = new_name

        await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(meta, ensure_ascii=False), user_id)
        await callback.answer(f"🔥 Успішно! Тепер у тебе {new_name}")
        await upgrade_list(callback)
    finally:
        await conn.close()

@router.callback_query(F.data == "forge_craft_list")
async def forge_craft_list(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT lvl FROM capybaras WHERE owner_id = $1", user_id)
        if row['lvl'] < 30:
            return await callback.answer("❌ Складна робота! Повертайся на 30 рівні.", show_alert=True)

        builder = InlineKeyboardBuilder()
        mythics = FORGE_RECIPES.get("mythic_artifacts", {})
        
        for r_id, r_data in mythics.items():
            builder.button(text=f"⚒️ {r_data.get('name')}", callback_data=f"mythic_info:{r_id}")
        
        builder.button(text="⬅️ Назад", callback_data="open_forge")
        builder.adjust(1)
        await callback.message.edit_caption(caption="⚒️ <b>Доступні креслення:</b>", reply_markup=builder.as_markup(), parse_mode="HTML")
    finally:
        await conn.close()

@router.callback_query(F.data.startswith("mythic_info:"))
async def show_mythic_recipe(callback: types.CallbackQuery):
    mythic_id = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", user_id)
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        inv = meta.get("inventory", {})
        
        recipe = FORGE_RECIPES.get("mythic_artifacts", {}).get(mythic_id)
        if not recipe:
            return await callback.answer("❌ Рецепт не знайдено")

        text = f"✨ <b>{recipe['name']}</b>\n"
        text += f"<i>{recipe['desc']}</i>\n"
        text += "━━━━━━━━━━━━━━━\n\n"
        text += "<b>Необхідні артефакти:</b>\n"

        can_craft = True
        
        for ing_name in recipe["ingredients"]:
            in_loot = inv.get("loot", {}).get(ing_name, 0) > 0
            
            in_equip = False
            equip = inv.get("equipment", {})
            if isinstance(equip, dict):
                for item in equip.values():
                    name = item if isinstance(item, str) else item.get("name", "")
                    if ing_name in name:
                        in_equip = True
                        break
            elif isinstance(equip, list):
                for item in equip:
                    name = item if isinstance(item, str) else item.get("name", "")
                    if ing_name in name:
                        in_equip = True
                        break
            
            if in_loot or in_equip:
                text += f"✅ {ing_name}\n"
            else:
                text += f"❌ {ing_name}\n"
                can_craft = False

        if "requirements" in recipe:
            text += "\n<b>Особливі умови:</b>\n"
            reqs = recipe["requirements"]
            stats = meta.get("stats_track", {})
            
            if "wins" in reqs:
                current_wins = stats.get("wins", 0)
                icon = "✅" if current_wins >= reqs["wins"] else "⏳"
                text += f"{icon} Перемоги: {current_wins}/{reqs['wins']}\n"
                if current_wins < reqs["wins"]: can_craft = False

            if "stamina_regen_total" in reqs:
                current_regen = stats.get("stamina_regen", 0)
                icon = "✅" if current_regen >= reqs["stamina_regen_total"] else "⏳"
                text += f"{icon} Реген ХП: {current_regen}/{reqs['stamina_regen_total']}\n"
                if current_regen < reqs["stamina_regen_total"]: can_craft = False

        builder = InlineKeyboardBuilder()
        
        if can_craft:
            builder.button(text="🔥 КУВАТИ АРТЕФАКТ", callback_data=f"craft_mythic:{mythic_id}")
        else:
            builder.button(text="⚠️ Бракує ресурсів", callback_data="none")
            
        builder.button(text="⬅️ Назад", callback_data="forge_craft_list")
        builder.adjust(1)

        await callback.message.edit_caption(
            caption=text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    finally:
        await conn.close()

@router.callback_query(F.data.startswith("craft_mythic:"))
async def process_mythic_craft(callback: types.CallbackQuery):
    mythic_id = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", user_id)
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        inv = meta.get("inventory", {})
        equip = inv.get("equipment", {})
        loot = inv.get("loot", {})
        
        recipe = FORGE_RECIPES.get("mythic_artifacts", {}).get(mythic_id)
        
        to_remove_from_loot = []
        to_remove_from_equip = []
        
        temp_loot = loot.copy()
        temp_equip = equip.copy()
        
        to_remove_from_loot = []
        to_remove_from_equip = []
        
        for ing_name in recipe["ingredients"]:
            found = False
            
            if temp_loot.get(ing_name, 0) > 0:
                temp_loot[ing_name] -= 1
                to_remove_from_loot.append(ing_name)
                found = True
            
            if not found and isinstance(temp_equip, dict):
                for slot, item in temp_equip.items():
                    current_item_name = item if isinstance(item, str) else item.get("name", "")
                    
                    if current_item_name == ing_name and slot not in to_remove_from_equip:
                        to_remove_from_equip.append(slot)
                        temp_equip[slot] = "Використано" 
                        found = True
                        break
            
            if not found:
                print(f"DEBUG: Not found ingredient: {ing_name}")
                return await callback.answer(f"❌ Немає інгредієнта: {ing_name}", show_alert=True)

        for ing in to_remove_from_loot:
            loot[ing] -= 1
            if loot[ing] <= 0: del loot[ing]
            
        for slot in to_remove_from_equip:
            if slot == "weapon": equip[slot] = "Лапки"
            elif slot == "armor": equip[slot] = "Хутро"
            else: equip[slot] = "Нічого"

        mythic_item = {
            "name": recipe["name"],
            "type": "mythic",
            "stats": recipe.get("stats", {})
        }
        
        if "weapon" in mythic_id or "drill" in mythic_id or "sword" in mythic_id or "staff" in mythic_id or "axe" in mythic_id:
            equip["weapon"] = mythic_item
        else:
            loot[recipe["name"]] = loot.get(recipe["name"], 0) + 1

        await conn.execute(
            "UPDATE capybaras SET meta = $1 WHERE owner_id = $2", 
            json.dumps(meta, ensure_ascii=False), 
            user_id
        )

        success_text = (
            "✨ <b>РИТУАЛ ЗАВЕРШЕНО!</b> ✨\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"Легендарні предмети переплавились у:\n"
            f"⚡️ <b>{recipe['name']}</b>\n\n"
            "<i>Ви відчуваєте, як сила предків наповнює ваші лапки...</i>"
        )
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🔥 ВІДЧУТИ МОГУТНІСТЬ", callback_data="open_forge")
        
        await callback.message.edit_caption(
            caption=success_text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        await callback.answer("⚔️ Міфічний предмет створено!")

    except Exception as e:
        print(f"Craft Error: {e}")
        await callback.answer("🛑 Помилка при ковці артефакту.")
    finally:
        await conn.close()

