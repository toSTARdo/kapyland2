import json
import random
import datetime
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.postgres_db import (
    get_user_profile, 
    calculate_dynamic_stats, 
    get_db_connection, 
    feed_capybara_logic
)

router = Router()

async def wash_db_operation(tg_id: int):
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", tg_id)
        if not row: return "no_capy", None
        
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        
        last_wash_str = meta.get("last_wash")
        if last_wash_str:
            last_wash = datetime.datetime.fromisoformat(last_wash_str)
            diff = datetime.datetime.now() - last_wash
            if diff < datetime.timedelta(hours=1):
                remaining = datetime.timedelta(hours=1) - diff
                return "cooldown", remaining

        meta["cleanness"] = 3
        meta["last_wash"] = datetime.datetime.now().isoformat()
        
        await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(meta), tg_id)
        return "success", None
    finally:
        await conn.close()

@router.callback_query(F.data == "feed_capy")
@router.message(Command("feed"))
async def cmd_feed(event: types.Message | types.CallbackQuery):
    uid = event.from_user.id
    message = event.message if isinstance(event, types.CallbackQuery) else event
    
    if isinstance(event, types.CallbackQuery):
        await event.answer()

    raw_random_weight = round(random.uniform(0.1, 0.5), 2)
    result = await feed_capybara_logic(uid, raw_random_weight)

    if result == "no_capy":
        return await message.answer("❌ У тебе немає капібари! Натисни /start")

    if isinstance(result, dict) and result.get("status") == "cooldown":
        rem = result["remaining"]
        return await message.answer(f"⏳ Капібара сита! Зачекай ще {rem.seconds // 60} хв.")

    await message.answer(
        f"🍎 <b>Смакота!</b>\nНабрала: <b>+{result['gain']} кг</b>\n"
        f"Вага: <b>{result['total']} кг</b>\n"
        f"🍏 Ситість: {'🍏' * result['hunger']}",
        parse_mode="HTML"
    )

@router.callback_query(F.data == "wash_capy")
@router.message(Command("wash"))
async def cmd_wash(event: types.Message | types.CallbackQuery):
    uid = event.from_user.id
    message = event.message if isinstance(event, types.CallbackQuery) else event
    
    if isinstance(event, types.CallbackQuery):
        await event.answer()

    status, remaining = await wash_db_operation(uid) 
    
    if status == "no_capy":
        await message.answer("❌ У тебе немає капібари!")
    elif status == "cooldown":
        await message.answer(f"🧼 Вона ще чиста! Зачекай {remaining.seconds // 60} хв.")
    else:
        await message.answer("🧼 Капібара скупалася та сяє!")

@router.callback_query(F.data == "sleep_capy")
@router.message(Command("sleep"))
async def cmd_sleep(event: types.Message | types.CallbackQuery):
    uid = event.from_user.id
    message = event.message if isinstance(event, types.CallbackQuery) else event
    
    if isinstance(event, types.CallbackQuery):
        await event.answer()

    result = await sleep_db_operation(uid) 
    if result == "no_capy":
        await message.answer("❌ У тебе немає капібари!")
    else:
        await message.answer("💤 Капібара відпочила, енергія: 100%")

def create_scale(current, max_val, emoji, empty_emoji='▫️'):
    current = max(0, min(int(current), max_val))
    return f"{emoji * current}{empty_emoji * (max_val - current)} ({current}/{max_val})"

@router.message(F.text == "🐾 Профіль")
async def show_profile(message: types.Message):
    uid = message.from_user.id
    data = await get_user_profile(uid)
    
    if not data:
        return await message.answer("❌ Капібару не знайдено.")

    meta = data['meta']
    if isinstance(meta, str): meta = json.loads(meta)
    meta = calculate_dynamic_stats(meta)

    profile_text = (
        f"<b>₍ᐢ-(ェ)-ᐢ₎ {data['name']}</b>\n"
        f"🌟 Рівень: <b>{data['lvl']}</b>\n"
        f"⚖️ Вага: <b>{meta.get('weight', 20.0):.2f} кг</b>\n\n"
        f"❤️ ХП: {create_scale(meta.get('stats', {}).get('hp', 3), 3, '❤️', '🖤')}\n"
        f"🍏 Ситість: {create_scale(meta.get('hunger', 3), 3, '🍏', '●')}\n"
        f"🧼 Гігієна: {create_scale(meta.get('cleanness', 3), 3, '🧼', '🦠')}\n"
        f"⚡ Енергія: <b>{data['energy']}/100</b>"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="🍎 Годувати", callback_data="feed_capy")
    builder.button(text="🧼 Мити", callback_data="wash_capy")
    builder.button(text="💤 Спати", callback_data="sleep_capy")
    builder.adjust(3)

    await message.answer(profile_text, reply_markup=builder.as_markup(), parse_mode="HTML")