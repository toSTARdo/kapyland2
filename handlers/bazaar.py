import json
import random
from datetime import datetime, timedelta, timezone
from aiogram import types, F, Router
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ARTIFACTS, DISPLAY_NAMES
from database.postgres_db import get_db_connection

router = Router()

CURRENCY_VALUE = {
    "watermelon_slices": 1,
    "tangerines": 5,
    "mango": 15,
    "kiwi": 50
}

FOOD_ICONS = {
    "watermelon_slices": "🍉",
    "tangerines": "🍊",
    "mango": "🥭",
    "kiwi": "🥝"
}

async def get_weekly_bazaar_stock():
    conn = await get_db_connection()
    try:
        now = datetime.now(timezone.utc)
        row = await conn.fetchrow("SELECT value FROM world_state WHERE key = 'bazaar_weekly'")
        
        state = json.loads(row['value']) if row and row['value'] else {}
        next_update_str = state.get("next_update")
        
        if not next_update_str or now > datetime.fromisoformat(next_update_str):
            new_stock = {}
            gacha_pool = list(ARTIFACTS.keys())
            res_pool = ["wood", "carp", "octopus", "lotus", "fly_agaric", "shark", "iron_ore", "crystal"]
            
            selected_items = random.sample(gacha_pool, 2) + random.sample(res_pool, 3)
            
            for item in selected_items:
                base = random.randint(150, 400) if item in ARTIFACTS else random.randint(20, 80)
                new_stock[item] = {"base_cost": base}
            
            next_monday = (now + timedelta(days=(7 - now.weekday()))).replace(hour=0, minute=0, second=0, microsecond=0)
            
            new_state = {
                "items": new_stock,
                "next_update": next_monday.isoformat()
            }
            
            await conn.execute("""
                INSERT INTO world_state (key, value) 
                VALUES ('bazaar_weekly', $1)
                ON CONFLICT (key) DO UPDATE SET value = $1
            """, json.dumps(new_state))
            
            return new_stock, next_monday
        
        return state["items"], datetime.fromisoformat(state["next_update"])
    finally:
        await conn.close()

@router.callback_query(F.data == "open_bazaar")
async def open_bazaar(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Вітрина", callback_data="bazaar_shop")
    builder.button(text="⬅️ Назад", callback_data="open_port")
    builder.adjust(1)
    
    await callback.message.edit_caption(
        caption="🏺 <b>Центральний Базар</b>\n━━━━━━━━━━━━━━━━━━━━\nТорговці чекають на твій врожай фруктів.",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "bazaar_shop")
async def bazaar_shop(callback: types.CallbackQuery):
    stock, next_up = await get_weekly_bazaar_stock()
    builder = InlineKeyboardBuilder()
    
    text = f"🛒 <b>Товари тижня</b> (до {next_up.strftime('%d.%m')})\n━━━━━━━━━━━━━━━━━━━━\n\n"

    for item_key, data in stock.items():
        cost = data['base_cost']
        name = DISPLAY_NAMES.get(item_key, item_key)
        if item_key in ARTIFACTS:
            name = ARTIFACTS[item_key].get("name", item_key)
        
        text += f"📦 <b>{name}</b>\n└ 🍉{cost} | 🍊{max(1, cost//5)} | 🥭{max(1, cost//15)} | 🥝{max(1, cost//50)}\n\n"
        builder.button(text=f"Купити {name}", callback_data=f"b_prebuy:{item_key}")

    builder.button(text="⬅️ Назад", callback_data="open_bazaar")
    builder.adjust(1)
    await callback.message.edit_caption(caption=text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.startswith("b_prebuy:"))
async def bazaar_prebuy(callback: types.CallbackQuery):
    item_key = callback.data.split(":")[1]
    stock, _ = await get_weekly_bazaar_stock()
    cost = stock[item_key]['base_cost']
    
    name = DISPLAY_NAMES.get(item_key, item_key)
    if item_key in ARTIFACTS:
        name = ARTIFACTS[item_key].get("name", item_key)
    
    builder = InlineKeyboardBuilder()
    for f_id, f_icon in FOOD_ICONS.items():
        needed = max(1, cost // CURRENCY_VALUE[f_id])
        builder.button(text=f"{f_icon} Сплатити {needed}", callback_data=f"b_pay:{f_id}:{needed}:{item_key}")
    
    builder.button(text="⬅️ Назад", callback_data="bazaar_shop")
    builder.adjust(1)
    await callback.message.edit_caption(caption=f"❓ Оплата за <b>{name}</b>:", reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.startswith("b_pay:"))
async def bazaar_process_pay(callback: types.CallbackQuery):
    _, food_id, amount, item_key = callback.data.split(":")
    amount, user_id = int(amount), callback.from_user.id

    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", user_id)
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        inv = meta.get("inventory", {})
        
        if inv.get("food", {}).get(food_id, 0) < amount:
            return await callback.answer("❌ Бракує їжі!", show_alert=True)

        inv["food"][food_id] -= amount
        
        if item_key in ARTIFACTS:
            cat = "loot"
        elif item_key in ["wood", "iron_ore", "crystal"]:
            cat = "materials"
        elif item_key in ["mint", "thyme", "rosemary", "chamomile", "lavender", "tulip", "lotus"]:
            cat = "plants"
        else:
            cat = "loot"
            
        cat_dict = inv.setdefault(cat, {})
        cat_dict[item_key] = cat_dict.get(item_key, 0) + 1
        
        await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(meta, ensure_ascii=False), user_id)
        await callback.answer(f"✅ Успішно придбано!")
        await bazaar_shop(callback)
    finally:
        await conn.close()
