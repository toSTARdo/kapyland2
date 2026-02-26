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

RESOURCES_POOL = [
    "mint", "thyme", "rosemary", 
    "chamomile", "lavender", "tulip", "lotus",
    "fly_agaric", "mushroom", "wood",
    "carp", "perch", "pufferfish", "octopus", "crab", "jellyfish", "swordfish", "shark"
]

def get_item_name(item_key):
    if item_key in DISPLAY_NAMES:
        return DISPLAY_NAMES[item_key]
    for rarity in ARTIFACTS:
        for item in ARTIFACTS[rarity]:
            if item["name"] == item_key:
                return item["name"]
    return item_key

async def get_weekly_bazaar_stock():
    conn = await get_db_connection()
    try:
        now = datetime.now(timezone.utc)
        row = await conn.fetchrow("SELECT value FROM world_state WHERE key = 'bazaar_weekly'")
        state = json.loads(row['value']) if row and row['value'] else {}
        
        if not state.get("next_update") or now > datetime.fromisoformat(state["next_update"]):
            new_stock = {}
            all_gacha_items = []
            for rarity in ARTIFACTS:
                all_gacha_items.extend([i["name"] for i in ARTIFACTS[rarity]])
            
            selected_gacha = random.choice(all_gacha_items)
            selected_res = random.sample(RESOURCES_POOL, 4)
            
            new_stock[selected_gacha] = {"base_cost": random.randint(250, 600), "cat": "loot"}
            
            for res in selected_res:
                cost = random.randint(20, 100)
                if res in ["mint", "thyme", "rosemary", "chamomile", "lavender", "tulip", "lotus"]:
                    cat = "plants"
                elif res in ["carp", "perch", "pufferfish", "octopus", "crab", "jellyfish", "swordfish", "shark"]:
                    cat = "materials" 
                else:
                    cat = "materials"
                new_stock[res] = {"base_cost": cost, "cat": cat}
            
            next_monday = (now + timedelta(days=(7 - now.weekday()))).replace(hour=0, minute=0, second=0, microsecond=0)
            new_state = {"items": new_stock, "next_update": next_monday.isoformat()}
            
            await conn.execute("INSERT INTO world_state (key, value) VALUES ('bazaar_weekly', $1) ON CONFLICT (key) DO UPDATE SET value = $1", json.dumps(new_state))
            return new_stock, next_monday
        
        return state["items"], datetime.fromisoformat(state["next_update"])
    finally:
        await conn.close()

@router.callback_query(F.data == "open_bazaar")
async def open_bazaar(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Товари", callback_data="bazaar_shop")
    builder.button(text="⬅️ Назад", callback_data="open_port")
    builder.adjust(1)
    await callback.message.edit_caption(
        caption="🏺 <b>Базар Капіграда</b>\n━━━━━━━━━━━━━━━━━━━━\nСвіжий вилов, запашні трави та рідкісна гача — все за фрукти!",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "bazaar_shop")
async def bazaar_shop(callback: types.CallbackQuery):
    stock, next_up = await get_weekly_bazaar_stock()
    builder = InlineKeyboardBuilder()
    text = f"🛒 <b>Асортимент</b> (до {next_up.strftime('%d.%m')})\n━━━━━━━━━━━━━━━━━━━━\n\n"

    for item_key, data in stock.items():
        cost = data['base_cost']
        name = get_item_name(item_key)
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
    name = get_item_name(item_key)
    
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
    stock, _ = await get_weekly_bazaar_stock()

    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", user_id)
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        inv = meta.get("inventory", {})
        
        if inv.get("food", {}).get(food_id, 0) < amount:
            return await callback.answer("❌ Бракує їжі!", show_alert=True)

        inv["food"][food_id] -= amount
        
        cat = stock[item_key].get("cat", "materials")
        cat_dict = inv.setdefault(cat, {})
        cat_dict[item_key] = cat_dict.get(item_key, 0) + 1
        
        await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(meta, ensure_ascii=False), user_id)
        await callback.answer(f"✅ Придбано: {get_item_name(item_key)}")
        await bazaar_shop(callback)
    finally:
        await conn.close()
