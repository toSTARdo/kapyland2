import json
import os
from aiogram import types, F, Router
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import load_game_data, DISPLAY_NAMES
from database.postgres_db import get_db_connection

router = Router()

EMOJI_MAP = {
    "mango": "🥭",
    "mint": "🌿",
    "tangerines": "🍊",
    "watermelon_slices": "🍉",
    "kiwi": "🥝"
}

RECIPES = load_game_data("data/craft.json")

async def get_user_inventory(tg_id: int):
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", tg_id)
        
        if not row or not row['meta']:
            return {}

        meta = row['meta']
        if isinstance(meta, str):
            try:
                return json.loads(meta)
            except json.JSONDecodeError:
                return {}
        return meta
    finally:
        await conn.close()

def filter_available_potions(user_inventory, all_recipes):
    available = []
    for r_id, r_data in all_recipes.items():
        can_brew = True
        for ingredient, required_count in r_data['ingredients'].items():
            if user_inventory.get(ingredient, 0) < required_count:
                can_brew = False
                break
        if can_brew:
            available.append((r_id, r_data))
    return available

def get_alchemy_kb(available_recipes):
    builder = InlineKeyboardBuilder()
    for r_id, r_data in available_recipes:
        name = r_data.get("name", r_id) 
        emoji = r_data.get("emoji", "🧪")
        stamina = r_data.get("plus_stamina", 0)
        builder.button(
            text=f"{emoji} {name} (+{stamina}⚡)",
            callback_data=f"brew:{r_id}"
        )
    builder.button(text="⬅️ Назад", callback_data="open_port")
    builder.adjust(1)
    return builder.as_markup()

@router.callback_query(F.data == "open_alchemy")
async def process_open_alchemy(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    meta = await get_user_inventory(user_id)
    
    user_inv_dict = meta.get('inventory', {}).get('food', {})

    available = filter_available_potions(user_inv_dict, RECIPES)
    
    text = (
        "🧪 <b>Лавка Лінивця Омо</b>\n\n"
        "🦥 <i>«П-р-и-в-і-т... Щ-о... в-а-р-и-т-и-м-е-м-о?»</i>"
    )
    
    await callback.message.edit_caption(
        caption=text,
        reply_markup=get_alchemy_kb(available),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("use_potion:"))
async def process_drink_potion(callback: types.CallbackQuery):
    potion_id = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    recipe = RECIPES.get(potion_id)
    if not recipe:
        return await callback.answer("❌ Це зілля здається зіпсованим...")

    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", user_id)
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        
        potions = meta.get("inventory", {}).get("potions", {})
        
        if potions.get(potion_id, 0) <= 0:
            return await callback.answer("❌ У тебе немає цього зілля!", show_alert=True)

        boost = recipe.get("plus_stamina", 0)
        current_stamina = meta.get("stamina", 0)
        max_stamina = meta.get("max_stamina", 100)
        
        new_stamina = min(current_stamina + boost, max_stamina)
        meta["stamina"] = new_stamina

        potions[potion_id] -= 1
        if potions[potion_id] <= 0:
            del potions[potion_id]

        await conn.execute(
            "UPDATE capybaras SET meta = $1 WHERE owner_id = $2",
            json.dumps(meta, ensure_ascii=False), user_id
        )

        name = recipe.get("name", potion_id)
        emoji = recipe.get("emoji", "🧪")
        await callback.answer(f"Ви бахнули {name}! +{boost}⚡", show_alert=True)

        from handlers.inventory import render_inventory_page 
        await render_inventory_page(callback.message, user_id, page="potions", is_callback=True)

    finally:
        await conn.close()

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
        food = inv.setdefault("food", {})
        potions = inv.setdefault("potions", {})

        for ing, count in recipe['ingredients'].items():
            if food.get(ing, 0) < count:
                return await callback.answer("❌ Інгредієнти раптово зникли!", show_alert=True)

        for ing, count in recipe['ingredients'].items():
            food[ing] -= count
        
        potions[recipe_id] = potions.get(recipe_id, 0) + 1

        await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", 
                           json.dumps(meta, ensure_ascii=False), user_id)

        await callback.answer(f"✨ {recipe.get('name')} готове!")
        
        await process_open_alchemy(callback)
        
    finally:
        await conn.close()

@router.callback_query(F.data.startswith("brew:"))
async def preview_recipe(callback: types.CallbackQuery):
    recipe_id = callback.data.split(":")[1]
    recipe = RECIPES.get(recipe_id)
    user_id = callback.from_user.id

    meta = await get_user_inventory(user_id)
    inv = meta.get('inventory', {})
    food = inv.get('food', {})
    mats = inv.get('materials', {})

    ing_text = ""
    can_brew = True
    
    for ing, req_count in recipe['ingredients'].items():
        owned = food.get(ing, 0) or mats.get(ing, 0)
        
        display_info = DISPLAY_NAMES.get(ing, ing.capitalize())
        
        status = "✅" if owned >= req_count else "❌"
        ing_text += f"\n{status} {display_info}: <b>{owned}/{req_count}</b>"
        
        if owned < req_count:
            can_brew = False

    text = (
        f"🧪 <b>{recipe.get('name')}</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"<i>Омо повільно перевіряє інгредієнти...</i>\n"
        f"{ing_text}\n\n"
        f"✨ Ефект: <b>+{recipe.get('plus_stamina')}⚡</b>"
    )

    builder = InlineKeyboardBuilder()
    if can_brew:
        builder.button(text="🥘 Варити!", callback_data=f"confirm_brew:{recipe_id}")
    else:
        builder.button(text="🚫 Не вистачає інгредієнтів", callback_data="none")
    
    builder.button(text="⬅️ Назад до лавки", callback_data="open_alchemy")
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")