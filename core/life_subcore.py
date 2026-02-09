from aiogram import types, Router
from aiogram.filters import Command

router = Router()

@router.message(Command("feed"))
async def cmd_feed(message: types.Message):
    await message.answer("Капібара поїла та набрала +5кг!")

@router.message(Command("wash"))
async def cmd_wash(message: types.Message):
    await message.answer("Капібара скупалася та позбулася бліх!")

@router.message(Command("sleep"))
async def cmd_sleep(message: types.Message):
    await message.answer("Капібара гарненько відіспалася і готова покоряти моря!")

import json
from aiogram import Router, types, F
from database.postgres_db import get_user_profile

router = Router()

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
        f"🆙 Рівень: <b>{lvl}</b> ({data['exp']} exp)\n"
        f"⚖️ Вага: <b>{weight:.2f} кг</b>\n\n"
        f"Здоров'я: {create_scale(hp, 3, '❤️', '🖤')}\n"
        f"Ситість:  {create_scale(hunger, 3, '🍏', '▫️')}\n"
        f"Гігієна:  {create_scale(clean, 3, '🧼', '▫️')}\n\n"
        f"⚡ Енергія: <b>{data['energy']}/100</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 Гравець: <i>{data['username']}</i>"
    )

    await message.answer(profile_text, parse_mode="HTML")