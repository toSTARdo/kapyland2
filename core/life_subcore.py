from aiogram import types, Router
from aiogram.filters import Command
import random
from database.postgres_db import feed_capybara_logic
import json
from aiogram import Router, types, F
from database.postgres_db import get_user_profile

router = Router()

@router.message(Command("feed"))
async def cmd_feed(message: types.Message):
    uid = message.from_user.id
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

@router.message(Command("wash"))
async def cmd_wash(message: types.Message):
    await message.answer("Капібара скупалася та позбулася бліх!")

@router.message(Command("sleep"))
async def cmd_sleep(message: types.Message):
    await message.answer("Капібара гарненько відіспалася і готова покоряти моря!")

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

    hp = meta.get('stats', {}).get('hp', 3) 
    hunger = meta.get('hunger', 3)         
    clean = meta.get('cleanness', 3)      

    profile_text = (
        f"<b>₍ᐢ-(ェ)-ᐢ₎ {name}</b> [{title}]\n"
        f"━━━━━━━━━━━━━━\n"
        f"🌟 Рівень: <b>{lvl}</b> ({data['exp']} exp)\n"
        f"⚖️ Вага: <b>{weight:.2f} кг</b>\n\n"
        f"1️⃣ Здоров'я: {create_scale(hp, 3, '❤️', '🖤')}\n"
        f"2️⃣ Ситість:   {create_scale(hunger, 3, '🍏', '▫️')}\n"
        f"3️⃣ Гігієна:    {create_scale(clean, 3, '🧼', '▫️')}\n\n"
        f"⚡ Енергія: <b>{data['energy']}/100</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 Гравець: <i>{data['username']}</i>"
    )

    await message.answer(profile_text, parse_mode="HTML")