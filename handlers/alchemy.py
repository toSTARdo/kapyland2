import json
import os
from aiogram import types, F, Router
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import load_game_data
from database import get_db_connection

router = Router()

EMOJI_MAP = {
    "mango": "🥭",
    "mint": "🌿",
    "tangerines": "🍊",
    "watermelon_slices": "🍉",
    "kiwi": "🥝"
}

RECIPES = load_game_data("craft.json")

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
        first_ing = list(r_data['ingredients'].keys())[0]
        emoji = EMOJI_MAP.get(first_ing, "🧪")
        display_name = r_id.replace("_", " ").title()
        stamina = r_data.get("plus_stamina", 0)
        builder.button(
            text=f"{emoji} {display_name} (+{stamina}⚡)",
            callback_data=f"brew:{r_id}"
        )
    builder.button(text="⬅️ Назад", callback_data="open_adventure")
    builder.adjust(1)
    return builder.as_markup()

@router.callback_query(F.data == "open_alchemy")
async def process_open_alchemy(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_data = await get_user_profile(user_id) 
    raw_inventory = user_data['meta']['inventory'].get('food', [])
    user_inv_dict = {item['name']: item.get('count', 0) for item in raw_inventory}
    
    available = filter_available_potions(user_inv_dict, RECIPES)
    
    text = (
        "🧪 <b>Лавка Лінивця Омо</b>\n\n"
        "🦥 <i>«П-р-и-в-і-т... Щ-о... в-а-р-и-т-и-м-е-м-о?»</i>"
    )
    
    await callback.message.edit_text(
        text=text,
        reply_markup=get_alchemy_kb(available),
        parse_mode="HTML"
    )