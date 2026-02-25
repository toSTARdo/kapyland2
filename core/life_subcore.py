import json
import random
import datetime
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.capybara_mechanics import get_user_profile, calculate_dynamic_stats, feed_capybara_logic, wash_db_operation, sleep_db_operation, wakeup_db_operation
from utils.helpers import format_time, calculate_lvl_data
from database.postgres_db import get_db_connection
from config import MOODS, IMAGES_URLS, STAT_WEIGHTS, BASE_HIT_CHANCE, BASE_BLOCK_CHANCE

router = Router()

@router.callback_query(F.data == "feed_capy")
@router.message(Command("feed"))
async def cmd_feed(event: types.Message | types.CallbackQuery):
    uid = event.from_user.id
    message = event.message if isinstance(event, types.CallbackQuery) else event
    
    if isinstance(event, types.CallbackQuery):
        await event.answer()

    raw_random_weight = round(random.uniform(0.1, 5.0), 2)
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

def get_general_profile_text(data, meta):
    MAX_STAMINA = 100
    mood = "ദ്ദി₍ᐢ•(ܫ)•ᐢ₎"
    stamina_val = meta.get('stamina', MAX_STAMINA)
    _, lvl = calculate_lvl_data(data['exp'], 0)
    
    return (
        f"<b>{mood} {data['name']}</b>\n"
        f"________________________________\n\n"
        f"🌟 Рівень: <b>{lvl}</b>\n"
        f"✳️ Капі-дзен: <b>{data['zen']}</b>\n"
        f"✴️ Капі-карма: <b>{data['karma']}</b>\n"
        f"⚖️ Вага: <b>{meta.get('weight', 20.0):.2f} кг</b>\n\n"
        f"ХП: {create_scale(meta.get('stats', {}).get('hp', 3), 3, '♥️', '🖤')}\n"
        f"Ситість: {create_scale(meta.get('hunger', 3), 3, '🍏', '●')}\n"
        f"Гігієна: {create_scale(meta.get('cleanness', 3), 3, '🧼', '🦠')}\n"
        f"Енергія: <b>{get_stamina_icons(stamina_val)} ({stamina_val}/{MAX_STAMINA})</b>"
    )

def get_fight_stats_text(data, meta):
    stats = meta.get('stats', {})
    equip = meta.get('equipment', {})
    win_rate = (data['wins'] / data['total_fights']) * 100 if data['total_fights'] != 0 else 0
    
    return (
        f"<b>⚔️ БОЙОВІ ХАРАКТЕРИСТИКИ</b>\n"
        f"<b>{data['name']}</b>\n"
        f"________________________________\n\n"
        f"🏆 Відсоток перемог: <b>{win_rate:.1f}%</b>\n"
        f"⚔️ Зброя: <b>{equip.get('weapon', 'Лапки')}</b>\n"
        f"🔰 Броня: <b>{equip.get('armor', 'Хутро')}</b>\n\n"
        f"✨ Благословення: <i>---</i>\n"
        f"💀 Прокляття: <i>---</i>\n"
        f"________________________________\n\n"
        f"<b>Показники:</b>\n"
        f"🔥 ATK: <b>{BASE_HIT_CHANCE + STAT_WEIGHTS["atk_to_hit"] * stats.get('attack', 1)}%</b>  |  "
        f"🛡️ DEF: <b>{BASE_BLOCK_CHANCE + STAT_WEIGHTS["def_to_block"] * stats.get('defense', 1)}%</b>\n"
        f"💨 AGI: <b>{STAT_WEIGHTS["agi_to_dodge"] * stats.get('agility', 1)}%</b>  |  "
        f"🍀 LCK: <b>+{STAT_WEIGHTS["luck_to_crit"] * stats.get('luck', 1)}%</b>\n"
        f"♥️ HP: <b>{stats.get('hp', 3)*2}</b>"
    )

@router.callback_query(F.data == "show_fight_stats")
async def show_fight_stats(callback: types.CallbackQuery):
    uid = callback.from_user.id
    data = await get_user_profile(uid)
    
    if not data:
        return await callback.answer("❌ Дані не знайдено")

    meta = json.loads(data['meta']) if isinstance(data['meta'], str) else data['meta']
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="profile_back")
    
    await callback.message.edit_caption(
        caption=get_fight_stats_text(data, meta),
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "wakeup_now")
async def cmd_wakeup(callback: types.CallbackQuery):
    uid = callback.from_user.id
    status, gained = await wakeup_db_operation(uid)
    
    if status == "success":
        await callback.answer(
            f"🥥 Капібара проснулася від будильника! Отримано {gained} ⚡", 
            show_alert=True
        )
    elif status == "overslept":
        await callback.answer(
            "🐾 Капібара проспала, але вже бігає по архіпелагу! (100 ⚡)", 
            show_alert=True
        )
    elif status == "not_sleeping":
        await callback.answer("❌ Капібара вже активна!")
    else:
        await callback.answer("❌ Щось пішло не так...")

    return await profile_back_callback(callback)

@router.message(F.text.startswith("🐾"))
async def show_profile(message: types.Message):
    uid = message.from_user.id
    data = await get_user_profile(uid)
    if not data: 
        return await message.answer("❌ Капібару не знайдено.")

    meta = json.loads(data['meta']) if isinstance(data['meta'], str) else data['meta']
    is_sleeping = meta.get("status") == "sleep"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🍎 Годувати", callback_data="feed_capy")
    builder.button(text="🧼 Мити", callback_data="wash_capy")
    
    if is_sleeping:
        builder.button(text="☀️ Прокинутися", callback_data="wakeup_now")
    else:
        builder.button(text="💤 Сон (2 год)", callback_data="sleep_capy")
        
    builder.button(text="⚔️ Бойові характеристики", callback_data="show_fight_stats")
    builder.button(text="🪷 Медитація", callback_data="zen_upgrade")
    
    builder.adjust(3, 1, 1)

    await message.answer_photo(
        photo=IMAGES_URLS["profile"],
        caption=get_general_profile_text(data, meta),
        reply_markup=builder.as_markup(), 
        parse_mode="HTML"
    )

@router.callback_query(F.data == "profile_back")
async def profile_back_callback(callback: types.CallbackQuery):
    uid = callback.from_user.id
    data = await get_user_profile(uid)
    meta = json.loads(data['meta']) if isinstance(data['meta'], str) else data['meta']
    is_sleeping = meta.get("status") == "sleep"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🍎 Годувати", callback_data="feed_capy")
    builder.button(text="🧼 Мити", callback_data="wash_capy")
    
    if is_sleeping:
        builder.button(text="☀️ Прокинутися", callback_data="wakeup_now")
    else:
        builder.button(text="💤 Сон (2 год)", callback_data="sleep_capy")
        
    builder.button(text="⚔️ Бойові характеристики", callback_data="show_fight_stats")
    builder.button(text="🪷 Медитація", callback_data="zen_upgrade")
    
    builder.adjust(3, 1, 1)

    try:
        await callback.message.edit_caption(
            caption=get_general_profile_text(data, meta),
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    except Exception:
        await callback.answer()

@router.callback_query(F.data == "sleep_capy")
async def cmd_sleep_callback(callback: types.CallbackQuery):
    uid = callback.from_user.id
    status, result_data = await sleep_db_operation(uid) 
    
    if status == "success":
        await callback.answer("💤 На добраніч!")
        return await profile_back_callback(callback)
    
    elif status == "already_sleeping":
        await callback.answer("💤 Вже спить")
    else:
        await callback.answer("❌ Помилка")
