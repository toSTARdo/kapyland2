import asyncio, json, random
from aiogram import Router, types, html, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from core.capybara_mechanics import get_user_inventory
from database.postgres_db import get_db_connection
from core.capybara_mechanics import grant_exp_and_lvl

router = Router()

@router.callback_query(F.data.startswith("food_choice:"))
async def handle_food_choice(callback: types.CallbackQuery):
    food_type = callback.data.split(":")[1]
    user_id = callback.from_user.id
    bot = callback.bot
    
    meta_data = await get_user_inventory(user_id)
    meta = json.loads(meta_data) if isinstance(meta_data, str) else meta_data
    count = meta.get("inventory", {}).get("food", {}).get(food_type, 0)
    
    if count <= 0:
        return await callback.answer("Нічого немає! Ти бідний, ти жебрак...")

    food_names = {"tangerines": "🍊", "melon": "🍈", "watermelon_slices": "🍉", "mango": "🥭", "kiwi": "🥝"}
    icon = food_names.get(food_type, "🍱")

    builder = InlineKeyboardBuilder()
    builder.button(text=f"🍴 З'їсти 1", callback_data=f"eat:one:{food_type}")
    
    if count > 1:
        builder.button(text=f"🍴 З'їсти все ({count})", callback_data=f"eat:all:{food_type}")
    
    builder.button(text="🔙 Назад", callback_data="inv_page:food")
    builder.adjust(1)

    await callback.message.edit_text(
        f"🍎 <b>Твій вибір: {icon}</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("eat:"))
async def handle_eat(callback: types.CallbackQuery):
    _, amount_type, food_type = callback.data.split(":")
    user_id = callback.from_user.id
    
    WEIGHT_TABLE = {
        "tangerines": 0.5,
        "watermelon_slices": 1.0,
        "melon": 5.0,
        "mango": 0.5,
        "kiwi": 0.5
    }
    
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow(
            "SELECT meta FROM capybaras WHERE owner_id = $1", 
            user_id
        )
        if not row: return
        
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        current_count = meta.get("inventory", {}).get("food", {}).get(food_type, 0)
        
        if current_count <= 0:
            await callback.answer("Нічого не залишилося! Ти бідний, ти жебрак...")
            return await render_inventory_page(callback.message, user_id, page="food", is_callback=True)

        to_eat = 1 if amount_type == "one" else current_count
        
        unit_weight = WEIGHT_TABLE.get(food_type, 0.5)
        total_bonus = to_eat * unit_weight
        
        exp_gain = int(total_bonus)
        if total_bonus < 1 and random.random() < total_bonus:
            exp_gain = 1

        meta["inventory"]["food"][food_type] -= to_eat
        
        await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", 
                           json.dumps(meta, ensure_ascii=False), user_id)
        
        from core.capybara_mechanics import grant_exp_and_lvl
        res = await grant_exp_and_lvl(user_id, exp_gain=exp_gain, weight_gain=total_bonus, bot=bot)

        if not res:
            return await callback.answer("Помилка магії травлення...")
        
        await callback.answer(
            f"Капі-ням!\n"
            f"Вага: +{total_bonus} кг\n"
            f"Досвід: +{exp_gain} EXP"
        )
        
        await render_inventory_page(callback.message, user_id, page="food", is_callback=True)

    finally:
        await conn.close()
