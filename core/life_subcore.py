from aiogram import types, Router
from aiogram.filters import Command
import random
from database.postgres_db import feed_capybara_logic
import json
from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.postgres_db import get_user_profile, calculate_dynamic_stats, get_db_connection
import datetime

router = Router()

@router.callback_query(F.data == "feed_capy")
@router.message(Command("feed"))
async def cmd_feed(message: types.Message):
    uid = message.from_user.id
    message = event.message if isinstance(event, types.CallbackQuery) else event
    raw_random_weight = random.uniform(0, 5)
    result = await feed_capybara_logic(uid, raw_random_weight)

    if result == "no_capy":
        return await message.answer("❌ У тебе немає капібари! Натисніть /start")

    if isinstance(result, dict) and result.get("status") == "cooldown":
        rem = result["remaining"]
        hours = rem.seconds // 3600
        minutes = (rem.seconds // 60) % 60
        return await message.answer(
            f"⏳ Капібара ще не зголодніла!\n"
            f"Зачекай ще <b>{hours}г {minutes}хв</b>.",
            parse_mode="HTML"
        )

    gain = result["gain"]
    total = result["total"]
    hunger_icons = "🍏" * result["hunger"] + "▫️" * (3 - result["hunger"])

    await message.answer(
        f"⚖️ Набрала: <b>+{gain} кг</b>\n"
        f"Вага: <b>{total} кг</b>\n"
        f"🍏 Ситість: {hunger_icons}\n"
        f"━━━━━━━━━━━━━━\n"
        f"🕒 Наступне годування через 8 годин",
        parse_mode="HTML"
    )

async def wash_db_operation(tg_id: int):
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", tg_id)
        if not row: return "no_capy"
        
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        
        last_wash_str = meta.get("last_wash")
        if last_wash_str:
            last_wash = datetime.datetime.fromisoformat(last_wash_str)
            if datetime.datetime.now() - last_wash < datetime.timedelta(hours=1):
                return "cooldown"

        meta["cleanness"] = 3
        meta["last_wash"] = datetime.datetime.now().isoformat()
        
        await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(meta), tg_id)
        return True
    finally:
        await conn.close()

async def sleep_db_operation(tg_id: int):
    conn = await get_db_connection()
    try:
        exists = await conn.fetchval("SELECT 1 FROM capybaras WHERE owner_id = $1", tg_id)
        if not exists: return "no_capy"
        
        await conn.execute("UPDATE capybaras SET energy = 100 WHERE owner_id = $1", tg_id)
        return True
    finally:
        await conn.close()

@router.callback_query(Command("wash"))
@router.message(F.data == "wash_capy")
async def cmd_wash(message: types.Message):
    uid = message.from_user.id
    message = event.message if isinstance(event, types.CallbackQuery) else event
    result = await wash_db_operation(uid) 
    
    if result == "no_capy":
        await message.answer("❌ У тебе немає капібари!")
    elif result == "cooldown":
        await message.answer("🧼 Капібара ще чиста! Приходь пізніше.")
    else:
        await message.answer("🧼 Капібара скупалася та сяє!")

@router.callback_query(Command("sleep"))
@router.message(F.data == "sleep_capy")
async def cmd_sleep(message: types.Message):
    uid = message.from_user.id
    message = event.message if isinstance(event, types.CallbackQuery) else event
    result = await sleep_db_operation(uid) 
    
    if result == "no_capy":
        await message.answer("❌ У тебе немає капібари!")
    else:
        await message.answer("💤 Капібара відпочила, енергія: 100%")
def create_scale(current, max_val, emoji, empty_emoji='▫️'):
    current = max(0, min(int(current), max_val))
    empty = max_val - current
    return f"{emoji * current}{empty_emoji * empty} ({current}/{max_val})"

@router.message(F.text == "🐾 Профіль")
async def show_profile(message: types.Message):
    uid = message.from_user.id
    data = await get_user_profile(uid)
    
    if not data:
        await message.answer("❌ Капібару не знайдено.")
        return

    meta = data['meta']
    if isinstance(meta, str):
        meta = json.loads(meta)

    name = data['name']
    lvl = data['lvl']
    weight = meta.get('weight', 20.0)
    
    title = "Новачок"
    if data['reincarnation_count'] > 0:
        title = f"Фенікс {data['reincarnation_count']} покоління"
    elif lvl >= 5:
        title = "Матрос"

    meta = calculate_dynamic_stats(meta)

    hp = meta.get('stats', {}).get('hp', 3) 
    hunger = meta.get('hunger', 3)         
    clean = meta.get('cleanness', 3)  
    mood = meta.get("mood", "Chill")    

    profile_text = (
        f"<b>₍ᐢ-(ェ)-ᐢ₎ {name}</b> [{title}]\n"
        f"Current mood: {mood}\n"
        f"━━━━━━━━━━━━━━\n"
        f"🌟 Рівень: <b>{lvl}</b> ({data['exp']} exp)\n"
        f"⚖️ Вага: <b>{weight:.2f} кг</b>\n\n"
        f"1️⃣ Здоров'я: {create_scale(hp, 3, '❤️', '🖤')}\n"
        f"2️⃣ Ситість:    {create_scale(hunger, 3, '🍏', '●')}\n"
        f"3️⃣ Гігієна:      {create_scale(clean, 3, '🧼', '🦠')}\n\n"
        f"⚡ Енергія: <b>{data['energy']}/100</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 Гравець: <i>{data['username']}</i>"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="🍎 Годувати", callback_data="feed_capy")
    builder.button(text="🧼 Мити", callback_data="wash_capy")
    builder.button(text="💤 Спати", callback_data="sleep_capy")
    builder.adjust(3)

    await message.answer(profile_text, reply_markup=builder.as_markup(), parse_mode="HTML")