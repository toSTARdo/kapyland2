import asyncio, json
from aiogram import Router, types, html, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from core.combat_engine import CombatEngine
from core.models import Fighter
from database.postgres_db import get_user_inventory
from config import BASE_HITPOINTS

router = Router()

from database.postgres_db import get_db_connection

@router.message(F.text == "⚔️ Бій")
@router.message(Command("fight"))
async def cmd_fight_lobby(message: types.Message):
    uid = message.from_user.id
    conn = await get_db_connection()
    
    try:
        players = await conn.fetch(
            "SELECT tg_id, username FROM users WHERE tg_id != $1 LIMIT 10", 
            uid
        )
    finally:
        await conn.close()

    if not players:
        await message.answer("🏝 На архіпелазі дивно пусто і одиноко...")

    builder = InlineKeyboardBuilder()
    for p in players:
        builder.button(
            text=f"🥊 {p['username']}", 
            callback_data=f"challenge_{p['tg_id']}"
        )
    
    builder.button(text="🤖 Побитися з ботом", callback_data="fight_bot")
    builder.adjust(1)

    await message.answer(
        "⚔️ <b>Арена</b>\nОбери суперника для дуелі або потренуйся на боті:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("challenge_"))
async def send_challenge(callback: types.CallbackQuery):
    opponent_id = int(callback.data.split("_")[1])
    challenger_id = callback.from_user.id
    challenger_name = callback.from_user.first_name

    builder = InlineKeyboardBuilder()
    builder.button(text="🤝 ПРИЙНЯТИ", callback_data=f"accept_{challenger_id}")
    builder.button(text="🏳️ ВІДМОВИТИСЯ", callback_data=f"decline_{challenger_id}")
    builder.adjust(2)

    try:
        await callback.bot.send_message(
            opponent_id,
            f"⚔️ <b>ВИКЛИК НА БІЙ!</b>\n"
            f"Пірабара <b>{challenger_name}</b> викликає на дуель?",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    except Exception:
        await callback.answer("❌ Не вдалося надіслати виклик (можливо, бот заблокований).", show_alert=True)

@router.callback_query(F.data.startswith("accept_"))
async def battle_accepted(callback: types.CallbackQuery):
    challenger_id = int(callback.data.split("_")[1])
    opponent_name = callback.from_user.first_name
    opponent_id = callback.from_user.id

    await callback.message.edit_text("🚀 Бій починається!")
    await run_battle_logic(callback, challenger_id, opponent_id)

@router.callback_query(F.data.startswith("decline_"))
async def battle_declined(callback: types.CallbackQuery):
    challenger_id = int(callback.data.split("_")[1])
    await callback.message.edit_text("🏳️ Ти відхилив бій.")
    await callback.bot.send_message(challenger_id, f"❌ Суперник відмовився від бою.")

@router.callback_query(F.data == "fight_bot")
async def start_bot_battle(callback: types.CallbackQuery):
    uid = callback.from_user.id
    await callback.message.edit_text("🤖 Папуга Павло гострить дзьоб...")
    asyncio.create_task(run_battle_logic(callback, uid, 0))
    await callback.answer()

async def get_fighter_data(tg_id: int, color: str, default_name: str = "Пірат") -> Fighter:
    if tg_id == 0:
        return Fighter(name="Папуга Павло (Бот)", weight=5.0, color="🔴")
    
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT name, meta FROM capybaras WHERE owner_id = $1", tg_id)
        if not row:
            return Fighter(name=default_name, weight=25.0, color=color)
        
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        return Fighter(name=row['name'], weight=meta.get("weight", 25.0), color=color)
    finally:
        await conn.close()

@router.callback_query(F.data == "fight_bot")
async def start_bot_battle(callback: types.CallbackQuery):
    await callback.message.delete()
    await cmd_fight(callback.message, is_bot=True)
    await callback.answer()

@router.callback_query(F.data.startswith("accept_"))
async def start_pvp_battle(callback: types.CallbackQuery):
    challenger_id = int(callback.data.split("_")[1])
    await callback.message.delete()
    asyncio.create_task(cmd_fight(callback.message, opponent_id=challenger_id))
    await callback.answer("Бій розпочато!")

async def run_battle_logic(callback: types.CallbackQuery, opponent_id: int = None, is_bot: bool = False):
    bot = callback.bot
    message = callback.message
    uid = callback.from_user.id
    chat_id = message.chat.id
    user_name = callback.from_user.first_name

    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT name, meta FROM capybaras WHERE owner_id = $1", uid)
        p1_name = row['name'] if row else user_name
        meta = json.loads(row['meta']) if row and row['meta'] else {}
        p1_weight = meta.get("weight", 25.0)
    finally:
        await conn.close()

    p1 = Fighter(name=p1_name, weight=p1_weight, color="🟢")

    if is_bot or opponent_id is None:
        p2 = Fighter(name="Папуга Павло (Бот)", weight=5.0, color="🔴")
        p2_id = None
    else:
        conn = await get_db_connection()
        try:
            opp_row = await conn.fetchrow("SELECT name, meta FROM capybaras WHERE owner_id = $1", opponent_id)
            p2_name = opp_row['name'] if opp_row else "Пірат"
            opp_meta = json.loads(opp_row['meta']) if opp_row and opp_row['meta'] else {}
            p2_weight = opp_meta.get("weight", 25.0)
            p2 = Fighter(name=p2_name, weight=p2_weight, color="🔴")
            p2_id = opponent_id
        finally:
            await conn.close()

    battle_msg = await message.answer(f"🔍 <b>{p1.name}</b> готується до битви...", parse_mode="HTML")
    await asyncio.sleep(1)
    
    start_text = (
        f"🏴‍☠️ Суперника знайдено!\n"
        f"{p1.color} <b>{p1.name}</b> VS {p2.color} <b>{p2.name}</b>"
    )
    await battle_msg.edit_text(start_text, parse_mode="HTML")
    if p2_id: await bot.send_message(p2_id, start_text, parse_mode="HTML")
    
    await asyncio.sleep(1.5)

    round_num = 1
    while p1.hp > 0 and p2.hp > 0 and round_num <= 20:
        attacker, defender = (p1, p2) if round_num % 2 != 0 else (p2, p1)
        
        report, damage = CombatEngine.resolve_turn(attacker, defender)
        
        full_report = (
            f"🏟 <b>Раунд {round_num}</b>\n"
            f"{p1.color} {p1.name}: {p1.hp} HP\n"
            f"{p2.color} {p2.name}: {p2.hp} HP\n"
            f"━━━━━━━━━━━━━━\n\n"
            f"{report}"
        )
        
        try:
            await battle_msg.edit_text(full_report, parse_mode="HTML")
            if p2_id: await bot.edit_message_text(full_report, p2_id, battle_msg.message_id + 1, parse_mode="HTML")
        except Exception: 
            pass
            
        await asyncio.sleep(2)
        round_num += 1

    if p1.hp > p2.hp:
        res = f"🏆 <b>ПЕРЕМОГА!</b>\n{p1.name} здолав суперника!"
    elif p2.hp > p1.hp:
        res = f"💀 <b>ПОРАЗКА...</b>\n{p1.name} був розбитий вщент."
    else:
        res = "🤝 <b>НІЧИЯ!</b> Обидва пірати втомилися."

    await message.answer(res, parse_mode="HTML")
    if p2_id: await bot.send_message(p2_id, res, parse_mode="HTML")

@router.message(F.text == "🎒 Інвентар")
async def show_inventory_buttons(message: types.Message):
    uid = message.from_user.id
    meta_data = await get_user_inventory(uid)
    
    if not meta_data:
        await message.answer("❌ Твій профіль не знайдено.")
        return

    meta = json.loads(meta_data) if isinstance(meta_data, str) else meta_data
    
    inv = meta.get("inventory", {})
    food = inv.get("food", {})
    loot = inv.get("loot", {})
    
    builder = InlineKeyboardBuilder()

    for item_key, count in food.items():
        if count > 0:
            item_names = {
                "tangerines": "🍊 Мандаринки",
                "melon": "🍈 Кавун",
                "watermelon_slices": "🍉 Шматочки кавуна",
                "mango": "🥭 Манго",
                "kiwi": "🥝 Ківі"
            }
            
            name = item_names.get(item_key, item_key.replace("_", " ").capitalize())
            
            builder.button(
                text=f"{name} ({count})", 
                callback_data=f"use_food:{item_key}"
            )

    if loot.get("chest", 0) > 0:
        builder.button(text=f"🗃 Скриня ({loot['chest']})", callback_data="open_chest")
    
    if loot.get("key", 0) > 0:
        builder.button(text=f"🔑 Ключ ({loot['key']})", callback_data="inspect_key")

    builder.adjust(1)

    await message.answer(
        f"<b>🎒 Твій рюкзак</b>\n\n"
        f"Обери предмет, щоб використати його або подивитися опис:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )