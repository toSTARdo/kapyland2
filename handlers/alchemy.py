import json
import asyncio
from aiogram import types, F, Router
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import load_game_data, DISPLAY_NAMES
from database.postgres_db import get_db_connection

router = Router()

RECIPES = load_game_data("data/craft.json")

def find_item_in_inventory(inv, item_key):
    """Шукає предмет у всіх категоріях інвентарю"""
    for category in ["food", "materials", "plants", "loot"]:
        count = inv.get(category, {}).get(item_key)
        if count is not None:
            return category, count
    return None, 0

@router.callback_query(F.data == "open_alchemy")
async def process_open_alchemy(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", user_id)
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        inv = meta.get('inventory', {})

        builder = InlineKeyboardBuilder()
        for r_id, r_data in RECIPES.items():
            can_brew = True
            for ing, count in r_data['ingredients'].items():
                _, owned = find_item_in_inventory(inv, ing)
                if owned < count:
                    can_brew = False
                    break
            
            prefix = "🟢" if can_brew else "🔴"
            builder.button(
                text=f"{prefix} {r_data.get('emoji')} {r_data.get('name')}",
                callback_data=f"brew:{r_id}"
            )

        builder.row(types.InlineKeyboardButton(text="📜 Всі рецепти", callback_data="all_recipes"))
        builder.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="open_port"))
        builder.adjust(1)

        text = (
            "🧪 <b>Лавка Лінивця Омо</b>\n\n"
            "🦥 <i>«П-р-и-в-і-т... Щ-о...\nс-ь-о-г-о-д-н-і в-а-р-и-т-и-м-е-м-о?»</i>"
        )
        
        await callback.message.edit_caption(
            caption=text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    finally:
        await conn.close()

@router.callback_query(F.data.startswith("brew:"))
async def preview_recipe(callback: types.CallbackQuery):
    recipe_id = callback.data.split(":")[1]
    recipe = RECIPES.get(recipe_id)
    user_id = callback.from_user.id

    conn = await get_db_connection()
    row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", user_id)
    meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
    inv = meta.get('inventory', {})
    await conn.close()

    ing_text = ""
    can_brew = True
    
    for ing, req_count in recipe['ingredients'].items():
        _, owned = find_item_in_inventory(inv, ing)
        display_name = DISPLAY_NAMES.get(ing, ing)
        status = "✅" if owned >= req_count else "❌"
        ing_text += f"\n{status} {display_name}: <b>{owned}/{req_count}</b>"
        if owned < req_count: can_brew = False

    effect_desc = ""
    if "plus_stamina" in recipe: effect_desc = f"⚡ +{recipe['plus_stamina']} Енергії"
    elif "plus_max_hp" in recipe: effect_desc = f"❤️ +{recipe['plus_max_hp']} Макс. HP (Назавжди)"
    elif recipe.get("effect") == "stats_reset": effect_desc = "🌀 Скидання всіх характеристик"

    text = (
        f"{recipe.get('emoji')} <b>{recipe.get('name')}</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"<i>{recipe.get('description')}</i>\n"
        f"{ing_text}\n\n"
        f"✨ Результат: <b>{effect_desc}</b>"
    )

    builder = InlineKeyboardBuilder()
    if can_brew:
        builder.button(text="🥘 Варити!", callback_data=f"confirm_brew:{recipe_id}")
    builder.button(text="⬅️ Назад", callback_data="open_alchemy")
    builder.adjust(1)

    await callback.message.edit_caption(caption=text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.startswith("confirm_brew:"))
async def process_confirm_brew(callback: types.CallbackQuery):
    recipe_id = callback.data.split(":")[1]
    user_id = callback.from_user.id
    recipe = RECIPES.get(recipe_id)

    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", user_id)
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        inv = meta.setdefault("inventory", {})

        for ing, count in recipe['ingredients'].items():
            cat, owned = find_item_in_inventory(inv, ing)
            if owned < count:
                return await callback.answer("❌ Недостатньо інгредієнтів!", show_alert=True)
            inv[cat][ing] -= count

        potions = inv.setdefault("potions", {})
        potions[recipe_id] = potions.get(recipe_id, 0) + 1

        await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", 
                           json.dumps(meta, ensure_ascii=False), user_id)

        await callback.answer(f"✨ {recipe.get('name')} готове і додане в інвентар!")
        await process_open_alchemy(callback)
        
    finally:
        await conn.close()
