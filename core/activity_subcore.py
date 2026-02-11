import asyncio, json
from aiogram import Router, types, html, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.combat_engine import CombatEngine
from core.models import Fighter
from database.postgres_db import get_user_inventory, get_db_connection
from config import BASE_HITPOINTS

router = Router()

#ВИКЛИКИ

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

    builder = InlineKeyboardBuilder()
    if players:
        for p in players:
            builder.button(text=f"🥊 {p['username']}", callback_data=f"challenge_{p['tg_id']}")
    
    builder.button(text="🤖 Побитися з ботом", callback_data="fight_bot")
    builder.adjust(1)

    text = "⚔️ <b>Арена</b>\nОбери суперника для дуелі або потренуйся на боті:"
    if not players:
        text = "🏝 На архіпелазі пусто..."

    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

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
            f"⚔️ <b>ВИКЛИК!</b>\nПірабара <b>{challenger_name}</b> викликає тебе на дуель!",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        await callback.answer("✅ Виклик надіслано!")
    except Exception:
        await callback.answer("❌ Не вдалося надіслати виклик.", show_alert=True)

@router.callback_query(F.data.startswith("decline_"))
async def battle_declined(callback: types.CallbackQuery):
    challenger_id = int(callback.data.split("_")[1])
    await callback.message.edit_text("🏳️ Ти відхилив бій.")
    try:
        await callback.bot.send_message(challenger_id, "❌ Суперник відмовився від бою.")
    except: pass

#ЗАПУСК БОЮ

@router.callback_query(F.data.startswith("accept_"))
async def handle_accept(callback: types.CallbackQuery):
    challenger_id = int(callback.data.split("_")[1])
    await callback.message.edit_text("🚀 Бій прийнято! Починаємо...")
    asyncio.create_task(run_battle_logic(callback, opponent_id=challenger_id))
    await callback.answer()

@router.callback_query(F.data == "fight_bot")
async def handle_fight_bot(callback: types.CallbackQuery):
    await callback.message.edit_text("🤖 Папуга Павло гострить дзьоб...")
    asyncio.create_task(run_battle_logic(callback, is_bot=True))
    await callback.answer()

#ОСНОВНИЙ ЦИКЛ

async def run_battle_logic(callback: types.CallbackQuery, opponent_id: int = None, is_bot: bool = False):
    bot = callback.bot
    uid = callback.from_user.id
    user_name = callback.from_user.first_name

    async def get_data(target_id):
        conn = await get_db_connection()
        try:
            row = await conn.fetchrow("SELECT name, meta FROM capybaras WHERE owner_id = $1", target_id)
            if not row: return "Пірат", 25.0
            meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
            return row['name'], meta.get("weight", 25.0)
        finally: await conn.close()

    p1_name, p1_weight = await get_data(uid)
    p1 = Fighter(name=p1_name, weight=p1_weight, color="🟢")

    p2_id = None
    if is_bot:
        p2 = Fighter(name="Папуга Павло (Бот)", weight=5.0, color="🔴")
    else:
        p2_id = opponent_id
        p2_name, p2_weight = await get_data(p2_id)
        p2 = Fighter(name=p2_name, weight=p2_weight, color="🔴")

    start_info = f"🏟 <b>БІЙ: {p1.name} VS {p2.name}</b>"
    msg1 = await callback.message.answer(start_info, parse_mode="HTML")
    msg2 = None
    if p2_id:
        try: msg2 = await bot.send_message(p2_id, start_info, parse_mode="HTML")
        except: pass

    await asyncio.sleep(1.5)

    round_num = 1
    while p1.hp > 0 and p2.hp > 0 and round_num <= 20:
        attacker, defender = (p1, p2) if round_num % 2 != 0 else (p2, p1)
        report, _ = CombatEngine.resolve_turn(attacker, defender)
        
        full_report = (
            f"🏟 <b>Раунд {round_num}</b>\n"
            f"{p1.color} {p1.name}: {p1.hp} HP\n"
            f"{p2.color} {p2.name}: {p2.hp} HP\n"
            f"━━━━━━━━━━━━━━\n\n{report}"
        )
        
        try:
            await msg1.edit_text(full_report, parse_mode="HTML")
            if msg2: await msg2.edit_text(full_report, parse_mode="HTML")
        except: pass
            
        await asyncio.sleep(2)
        round_num += 1

    if p1.hp > p2.hp: res = f"🏆 <b>ПЕРЕМОГА!</b>\n{p1.name} розніс ворога!"
    elif p2.hp > p1.hp: res = f"💀 <b>ПОРАЗКА...</b>\n{p1.name} програв дуель."
    else: res = "🤝 <b>НІЧИЯ!</b>"

    await msg1.answer(res, parse_mode="HTML")
    if msg2:
        try: await msg2.answer(res, parse_mode="HTML")
        except: pass

async def render_inventory_page(message, user_id, page="food", is_callback=False):
    meta_data = await get_user_inventory(user_id)
    if not meta_data:
        return await message.answer("❌ Профіль не знайдено.")

    meta = json.loads(meta_data) if isinstance(meta_data, str) else meta_data
    inv = meta.get("inventory", {})
    builder = InlineKeyboardBuilder()

    TYPE_ICONS = {
        "weapon": "🗡️",
        "armor": "🔰",
        "artifact": "🧿"
    }

    if page == "food":
        title = "🍎 <b>Провізія</b>"
        food = inv.get("food", {})
        food_names = {"tangerines": "🍊", "melon": "🍈", "watermelon_slices": "🍉", "mango": "🥭", "kiwi": "🥝"}
        
        content_lines = []
        for k, v in food.items():
            if v > 0:
                name = food_names.get(k, "🍱")
                builder.button(text=f"{name} ({v})", callback_data=f"use_food:{k}")
        
        content = "<i>Натисни на кнопку, щоб поїсти:</i>"
        builder.adjust(2)

    elif page == "loot":
        title = "🧳 <b>Скарби та ресурси</b>"
        loot = inv.get("loot", {})
        
        loot_lines = []
        if loot.get('lottery_ticket', 0) > 0: loot_lines.append(f"🎟️ Квитки: <b>{loot['lottery_ticket']}</b>")
        if loot.get('key', 0) > 0: loot_lines.append(f"🗝️ Ключі: <b>{loot['key']}</b>")
        if loot.get('chest', 0) > 0: loot_lines.append(f"🗃 Скрині: <b>{loot['chest']}</b>")
        
        content = "\n".join(loot_lines) if loot_lines else "<i>Твій сейф порожній...</i>"
        builder.adjust(1)

    elif page == "items":
        title = "⚔️ <b>Колекція амуніції та артефактів</b>"
        equipment = inv.get("equipment", [])
        
        if not equipment:
            content = "<i>Тут поки порожньо...</i>"
        else:
            counts = {}
            for item in equipment:
                item_name = item.get('name')
                rarity = item.get('rarity', 'Common')

                item_type = "artifact" 
                category_list = GACHA_ITEMS.get(rarity, [])
                
                for gacha_item in category_list:
                    if gacha_item["name"] == item_name:
                        item_type = gacha_item["type"]
                        break
                
                r_icon = RARITY_META.get(rarity, {}).get('emoji', '⚪')
                t_icon = TYPE_ICONS.get(item_type, "🧿")
                
                key = f"{r_icon}{t_icon} {item_name}"
                counts[key] = counts.get(key, 0) + 1
            
            content = "\n".join([f"{k} (x{v})" if v > 1 else k for k, v in counts.items()])
        builder.adjust(1)

    nav_buttons = []
    if page != "food": nav_buttons.append(types.InlineKeyboardButton(text="🍎 Їжа", callback_data="inv_page:food"))
    if page != "loot": nav_buttons.append(types.InlineKeyboardButton(text="🧳 Лут", callback_data="inv_page:loot"))
    if page != "items": nav_buttons.append(types.InlineKeyboardButton(text="⚔️ Речі", callback_data="inv_page:items"))
    builder.row(*nav_buttons)

    text = f"{title}\n━━━━━━━━━━━━━━━\n{content}"

    if is_callback:
        await message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.message(F.text == "🎒 Інвентар")
async def show_inventory_start(message: types.Message):
    await render_inventory_page(message, message.from_user.id, page="food")

@router.callback_query(F.data.startswith("inv_page:"))
async def handle_inventory_pagination(callback: types.CallbackQuery):
    page = callback.data.split(":")[1]
    await render_inventory_page(callback.message, callback.from_user.id, page=page, is_callback=True)
    await callback.answer()