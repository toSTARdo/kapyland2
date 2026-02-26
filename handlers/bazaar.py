import json
import random
from datetime import datetime, timedelta, timezone
from aiogram import types, F, Router
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ARTIFACTS, DISPLAY_NAMES
from database.postgres_db import get_db_connection

router = Router()

CURRENCY_VALUE = {"watermelon_slices": 1, "tangerines": 5, "mango": 15, "kiwi": 50}
FOOD_ICONS = {"watermelon_slices": "🍉", "tangerines": "🍊", "mango": "🥭", "kiwi": "🥝"}

RESOURCES_POOL = [
    "mint", "thyme", "rosemary", "chamomile", "lavender", "tulip", "lotus",
    "fly_agaric", "mushroom", "wood",
    "carp", "perch", "pufferfish", "octopus", "crab", "jellyfish", "swordfish", "shark"
]

# Ціни продажу (скільки кавунових одиниць дають за 1 шт ресурсу)
SELL_PRICES = {
    "wood": 10, "mint": 12, "thyme": 12, "rosemary": 15,
    "chamomile": 10, "lavender": 15, "tulip": 20, "lotus": 35,
    "fly_agaric": 25, "mushroom": 8,
    "carp": 15, "perch": 20, "pufferfish": 40, "octopus": 50, "crab": 45, "jellyfish": 30, "swordfish": 70, "shark": 120
}

def get_item_name(item_key):
    if item_key in DISPLAY_NAMES: return DISPLAY_NAMES[item_key]
    for rarity in ARTIFACTS:
        for item in ARTIFACTS[rarity]:
            if item["name"] == item_key: return item["name"]
    return item_key

async def get_weekly_bazaar_stock():
    conn = await get_db_connection()
    try:
        now = datetime.now(timezone.utc)
        row = await conn.fetchrow("SELECT value FROM world_state WHERE key = 'bazaar_weekly'")
        state = json.loads(row['value']) if row and row['value'] else {}
        if not state.get("next_update") or now > datetime.fromisoformat(state["next_update"]):
            new_stock = {}
            all_gacha = [i["name"] for r in ARTIFACTS.values() for i in r]
            new_stock[random.choice(all_gacha)] = {"base_cost": random.randint(250, 600), "cat": "loot"}
            for res in random.sample(RESOURCES_POOL, 4):
                cat = "plants" if res in ["mint", "thyme", "rosemary", "chamomile", "lavender", "tulip", "lotus"] else "materials"
                new_stock[res] = {"base_cost": random.randint(25, 110), "cat": cat}
            next_monday = (now + timedelta(days=(7 - now.weekday()))).replace(hour=0, minute=0, second=0, microsecond=0)
            new_state = {"items": new_stock, "next_update": next_monday.isoformat()}
            await conn.execute("INSERT INTO world_state (key, value) VALUES ('bazaar_weekly', $1) ON CONFLICT (key) DO UPDATE SET value = $1", json.dumps(new_state))
            return new_stock, next_monday
        return state["items"], datetime.fromisoformat(state["next_update"])
    finally: await conn.close()

@router.callback_query(F.data == "open_bazaar")
async def open_bazaar(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Купити", callback_data="bazaar_shop")
    builder.button(text="💰 Продати ресурси", callback_data="bazaar_sell_list")
    builder.button(text="⬅️ Назад", callback_data="open_port")
    builder.adjust(2, 1)
    await callback.message.edit_caption(caption="🏺 <b>Базар Капіграда</b>\n━━━━━━━━━━━━━━━━━━━━\nОбмінюй фрукти на артефакти або здавай свій вилов за соковиті кавуни!", reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data == "bazaar_shop")
async def bazaar_shop(callback: types.CallbackQuery):
    stock, next_up = await get_weekly_bazaar_stock()
    builder = InlineKeyboardBuilder()
    text = f"🛒 <b>Асортимент</b> (до {next_up.strftime('%d.%m')})\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for k, v in stock.items():
        cost = v['base_cost']
        name = get_item_name(k)
        text += f"📦 <b>{name}</b>\n└ 🍉{cost} | 🍊{max(1, cost//5)} | 🥭{max(1, cost//15)} | 🥝{max(1, cost//50)}\n\n"
        builder.button(text=f"Купити {name}", callback_data=f"b_prebuy:{k}")
    builder.button(text="⬅️ Назад", callback_data="open_bazaar")
    builder.adjust(1)
    await callback.message.edit_caption(caption=text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data == "bazaar_sell_list")
async def bazaar_sell_list(callback: types.CallbackQuery):
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", callback.from_user.id)
        inv = json.loads(row['meta']).get("inventory", {}) if row else {}
        builder = InlineKeyboardBuilder()
        text = "💰 <b>Твій інвентар для продажу:</b>\n<i>(Ціна вказана за 1 шт. у 🍉)</i>\n━━━━━━━━━━━━━━━━━━━━\n"
        found = False
        for cat in ["materials", "plants"]:
            for item_key, count in inv.get(cat, {}).items():
                if count > 0 and item_key in SELL_PRICES:
                    found = True
                    price = SELL_PRICES[item_key]
                    text += f"▫️ {get_item_name(item_key)}: {count} шт. (по 🍉{price})\n"
                    builder.button(text=f"Здати {get_item_name(item_key)}", callback_data=f"b_sell:{item_key}")
        if not found: text += "\nТвій рюкзак порожній. Нічого здати..."
        builder.button(text="⬅️ Назад", callback_data="open_bazaar")
        builder.adjust(1)
        await callback.message.edit_caption(caption=text, reply_markup=builder.as_markup(), parse_mode="HTML")
    finally: await conn.close()

@router.callback_query(F.data.startswith("b_sell:"))
async def bazaar_process_sell(callback: types.CallbackQuery):
    item_key = callback.data.split(":")[1]
    price = SELL_PRICES.get(item_key, 0)
    user_id = callback.from_user.id
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", user_id)
        meta = json.loads(row['meta'])
        inv = meta.get("inventory", {})
        cat = "plants" if item_key in ["mint", "thyme", "rosemary", "chamomile", "lavender", "tulip", "lotus"] else "materials"
        if inv.get(cat, {}).get(item_key, 0) <= 0:
            return await callback.answer("❌ У тебе цього немає!", show_alert=True)
        inv[cat][item_key] -= 1
        food = inv.setdefault("food", {})
        food["watermelon_slices"] = food.get("watermelon_slices", 0) + price
        await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(meta, ensure_ascii=False), user_id)
        await callback.answer(f"✅ Продано! Отримано 🍉{price}")
        await bazaar_sell_list(callback)
    finally: await conn.close()

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
        meta = json.loads(row['meta'])
        inv = meta.get("inventory", {})
        if inv.get("food", {}).get(food_id, 0) < amount:
            return await callback.answer("❌ Бракує їжі!", show_alert=True)
        inv["food"][food_id] -= amount
        cat = stock[item_key].get("cat", "materials")
        inv.setdefault(cat, {})[item_key] = inv[cat].get(item_key, 0) + 1
        await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(meta, ensure_ascii=False), user_id)
        await callback.answer("✅ Придбано!")
        await bazaar_shop(callback)
    finally: await conn.close()
