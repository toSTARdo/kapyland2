import json
import random
import datetime
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.capybara_mechanics import get_user_profile, calculate_dynamic_stats, feed_capybara_logic, wash_db_operation, sleep_db_operation
from utils.helpers import format_time
from database.postgres_db import get_db_connection

router = Router()

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
        time_str = format_time(result["remaining"])
        return await message.answer(f"⏳ Капібара сита! Зачекай ще {time_str}")

    await message.answer(
        f"🍎 <b>Смакота!</b>\n"
        f"Набрала: <b>+{result['gain']} кг</b> (✨ +{result['exp_gain']} EXP)\n"
        f"Вага: <b>{result['total_weight']} кг</b> | Рівень: <b>{result['lvl']}</b>\n"
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

    status, result_data = await wash_db_operation(uid) 
    
    if status == "no_capy":
        return await message.answer("❌ У тебе немає капібари!")
        
    elif status == "cooldown":
        time_str = format_time(result_data) 
        return await message.answer(f"🧼 Вона ще чиста! Зачекай {time_str}")
        
    elif status == "success":
        await message.answer(
            f"🧼 <b>Капібара скупалася та сяє!</b>\n"
            f"Отримано: ✨ <b>+{result_data['exp_gain']} EXP</b>\n"
            f"Поточний рівень: <b>{result_data['lvl']}</b>",
            parse_mode="HTML"
        )

@router.callback_query(F.data == "sleep_capy")
@router.message(Command("sleep"))
async def cmd_sleep(event: types.Message | types.CallbackQuery):
    uid = event.from_user.id
    message = event.message if isinstance(event, types.CallbackQuery) else event
    
    if isinstance(event, types.CallbackQuery):
        await event.answer()

    status, result_data = await sleep_db_operation(uid) 
    
    if status == "no_capy":
        return await message.answer("❌ У тебе немає капібари!")
    
    if status == "already_sleeping":
        time_str = format_time(result_data)
        return await message.answer(f"💤 Капібара вже бачить сни. Прокинеться через: <b>{time_str}</b>", parse_mode="HTML")

    if status == "success":
        await message.answer(
            "💤 <b>Капібара згорнулася калачиком...</b>\n"
            "Вона буде спати 2 години, щоб повністю відновити 100% ⚡.\n\n"
            "<i>У цей час вона не зможе битися або подорожувати.</i>",
            parse_mode="HTML"
        )
def create_scale(current, max_val, emoji, empty_emoji='▫️'):
    current = max(0, min(int(current), max_val))
    return f"{emoji * current}{empty_emoji * (max_val - current)} ({current}/{max_val})"

def get_stamina_icons(current_stamina):
    current_stamina = int(current_stamina)
    if current_stamina > 66:
        return "⚡⚡⚡"
    elif current_stamina > 33:
        return "⚡⚡ ●"
    elif current_stamina > 0:
        return "⚡ ● ●"
    else:
        return "● ● ●"

@router.message(F.text.startswith("🐾"))
async def show_profile(message: types.Message):
    uid = message.from_user.id
    data = await get_user_profile(uid)
    
    if not data:
        return await message.answer("❌ Капібару не знайдено.")

    meta = data['meta']
    if isinstance(meta, str): meta = json.loads(meta)
    meta = calculate_dynamic_stats(meta)

    stamina_val = meta.get('stamina', 100)

    profile_text = (
        f"<b>₍ᐢ-(ェ)-ᐢ₎ {data['name']}</b>\n"
        f"🌟 Рівень: <b>{data['lvl']}</b>\n"
        f"⚖️ Вага: <b>{meta.get('weight', 20.0):.2f} кг</b>\n\n"
        f"❤️ ХП: {create_scale(meta.get('stats', {}).get('hp', 3), 3, '❤️', '🖤')}\n"
        f"🍏 Ситість: {create_scale(meta.get('hunger', 3), 3, '🍏', '●')}\n"
        f"🧼 Гігієна: {create_scale(meta.get('cleanness', 3), 3, '🧼', '🦠')}\n"
        f"⚡ Енергія: <b>{get_stamina_icons(stamina_val)}</b>"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="🍎 Годувати", callback_data="feed_capy")
    builder.button(text="🧼 Мити", callback_data="wash_capy")
    builder.button(text="💤 Спати", callback_data="sleep_capy")
    builder.adjust(3)

    await message.answer(profile_text, reply_markup=builder.as_markup(), parse_mode="HTML")