import asyncio, json, random
from aiogram import Router, types, html, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.models import Fighter, CombatEngine
from core.capybara_mechanics import get_user_inventory
from database.postgres_db import get_db_connection
from config import BASE_HITPOINTS, ARTIFACTS, RARITY_META, WEAPON, ARMOR
GACHA_ITEMS = ARTIFACTS

router = Router()

#ВИКЛИКИ

@router.message(F.text.startswith("⚔️"))
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
    await callback.message.edit_text("🚀 Бій прийнято! Починаємо (-5 ⚡)...")
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
    
    battle_config = {
        "WEAPONS": WEAPON,
        "ARMOR": ARMOR
    }

    async def get_full_capy_data(target_id, is_bot_flag=False):
        if is_bot_flag:
            return {
                "kapy_name": "Папуга Павло (Бот)",
                "weight": 5.0,
                "stats": {"attack": 1, "defense": 1, "agility": 3, "luck": 1},
                "equipped_weapon": "Зуби акули",
                "equipped_armor": "",
                "artifacts": []
            }
        
        conn = await get_db_connection()
        try:
            row = await conn.fetchrow("SELECT name, meta FROM capybaras WHERE owner_id = $1", target_id)
            if not row: return None
            
            meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
            equip = meta.get("equipment", {})
            
            return {
                "kapy_name": row['name'],
                "weight": meta.get("weight", 25.0),
                "stats": meta.get("stats", {"attack": 0, "defense": 0, "agility": 0, "luck": 0}),
                "equipped_weapon": equip.get("weapon", "Лапки"),
                "equipped_armor": equip.get("armor", ""),
                "artifacts": meta.get("artifacts", [])
            }
        finally: await conn.close()

    p1_data = await get_full_capy_data(uid)
    p2_data = await get_full_capy_data(opponent_id, is_bot)

    if not p1_data or not p2_data:
        return await callback.message.answer("❌ Помилка: Дані капібари не знайдено.")

    p1 = Fighter(p1_data, battle_config, color="🟢")
    p2 = Fighter(p2_data, battle_config, color="🔴")

    start_info = f"🏟 <b>БІЙ: {p1.name} VS {p2.name}</b>"
    msg1 = await callback.message.answer(start_info, parse_mode="HTML")
    msg2 = None
    if opponent_id and not is_bot:
        try: msg2 = await bot.send_message(opponent_id, start_info, parse_mode="HTML")
        except: pass

    await asyncio.sleep(1.5)

    if p1.agi > p2.agi:
        attacker, defender = p1, p2
        init_msg = f"⚡ {html.bold(p1.name)} виявився спритнішим і атакує першим!"
    elif p2.agi > p1.agi:
        attacker, defender = p2, p1
        init_msg = f"⚡ {html.bold(p2.name)} швидше зорієнтувався і вистрибує вперед!"
    else:
        attacker, defender = random.sample([p1, p2], 2)
        init_msg = f"⚡ Спритність рівна! Але першим вдається ударити {html.bold(attacker.name)}."

    await msg1.answer(init_msg, parse_mode="HTML")
    if msg2:
        try: await msg2.answer(init_msg, parse_mode="HTML")
        except: pass

    round_num = 1
    while p1.hp > 0 and p2.hp > 0 and round_num <= 30:
        report = CombatEngine.resolve_turn(attacker, defender)
        
        full_report = (
            f"🏟 <b>Раунд {round_num}</b>\n"
            f"{p1.color} {p1.name}: {p1.get_hp_display()}\n"
            f"{p2.color} {p2.name}: {p2.get_hp_display()}\n"
            f"━━━━━━━━━━━━━━\n\n{report}"
        )
        
        try:
            await msg1.edit_text(full_report, parse_mode="HTML")
            if msg2: await msg2.edit_text(full_report, parse_mode="HTML")
        except: pass
            
        attacker, defender = defender, attacker
        await asyncio.sleep(2.3)
        round_num += 1

    winner, loser = None, None
    if p1.hp > 0 and p2.hp <= 0:
        winner, loser = p1, p2
        winner_id, loser_id = uid, opponent_id
        res = f"🏆 <b>ПЕРЕМОГА {p1.color}!</b>\n{html.bold(p1.name)} розгромив суперника {html.bold(p2.name)}!"
    elif p2.hp > 0 and p1.hp <= 0:
        winner, loser = p2, p1
        winner_id, loser_id = opponent_id, uid
        res = f"👑 <b>ПЕРЕМОГА {p2.color}!</b>\n{html.bold(p2.name)} виявився сильнішим за {html.bold(p1.name)}!"
    else: 
        res = "🤝 <b>НІЧИЯ! Капі обезсилені впали на травичку...</b>"

    await msg1.answer(res, parse_mode="HTML")
    if msg2:
        try: await msg2.answer(res, parse_mode="HTML")
        except: pass

    if winner and loser:
        conn = await get_db_connection()
        try:
            await conn.execute("""
                UPDATE capybaras SET meta = meta || 
                jsonb_build_object(
                    'weight', (meta->>'weight')::float + 3.0,
                    'stamina', GREATEST((meta->>'stamina')::int - 5, 0),
                    'exp', (meta->>'exp')::int + 3
                ) WHERE owner_id = $1
            """, winner_id)

            if not (is_bot and loser_id == opponent_id):
                await conn.execute("""
                    UPDATE capybaras SET meta = meta || 
                    jsonb_build_object(
                        'weight', LEAST(GREATEST((meta->>'weight')::float - 3.0, 1.0), 500.0),
                        'stamina', GREATEST((meta->>'stamina')::int - 5, 0)
                    ) WHERE owner_id = $1
                """, loser_id)
            
            reward_msg = f"📈 <b>Підсумки бою:</b>\n🥇 {winner.name}: +3 кг, +3 EXP\n🥈 {loser.name}: -3 кг"
            await msg1.answer(reward_msg, parse_mode="HTML")
            if msg2: await msg2.answer(reward_msg, parse_mode="HTML")

        finally:
            await conn.close()

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
        title = "⚔️ <b>Амуніція</b>"
        curr_equip = meta.get("equipment", {})
        curr_weapon = curr_equip.get("weapon", "Лапки")
        curr_armor = curr_equip.get("armor", "")
        
        all_items = inv.get("equipment", [])
        
        if not all_items:
            content = "<i>Твій трюм порожній...</i>"
        else:
            unique_items = {}
            for item in all_items:
                name = item['name']
                if name not in unique_items: unique_items[name] = item
            
            content_lines = []
            for name, item in unique_items.items():
                rarity = item.get('rarity', 'Common')
                
                item_type = "artifact"
                for g_item in GACHA_ITEMS.get(rarity, []):
                    if g_item["name"] == name:
                        item_type = g_item["type"]
                        break
                
                is_equipped = (name == curr_weapon or name == curr_armor)
                
                r_icon = RARITY_META.get(rarity, {}).get('emoji', '⚪')
                t_icon = TYPE_ICONS.get(item_type, "🧿")
                status = " ✅" if is_equipped else ""
                
                content_lines.append(f"{r_icon}{t_icon} <b>{name}</b>{status}")
                
                if item_type in ["weapon", "armor"] and not is_equipped:
                    builder.button(
                        text=f"Взяти {name}", 
                        callback_data=f"equip:{item_type}:{name}"
                    )
            content = "\n".join(content_lines)
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

@router.message(F.text.startswith("🎒"))
async def show_inventory_start(message: types.Message):
    await render_inventory_page(message, message.from_user.id, page="food")

@router.callback_query(F.data.startswith("equip:"))
async def handle_equip_item(callback: types.CallbackQuery):
    _, itype, iname = callback.data.split(":")
    user_id = callback.from_user.id
    
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", user_id)
        if not row: return await callback.answer("Де твоя капібара?")
            
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        
        if "equipment" not in meta:
            meta["equipment"] = {"weapon": "Лапки", "armor": ""}
            
        current_item = meta["equipment"].get(itype)
        
        if current_item == iname:
            default_val = "Лапки" if itype == "weapon" else ""
            meta["equipment"][itype] = default_val
            msg = f"❌ Знято: {iname}"
        else:
            meta["equipment"][itype] = iname
            msg = f"✅ Одягнено: {iname}"
            
        await conn.execute(
            "UPDATE capybaras SET meta = $1 WHERE owner_id = $2",
            json.dumps(meta, ensure_ascii=False), user_id
        )
        
        await callback.answer(msg)
        await render_inventory_page(callback.message, user_id, page="items", is_callback=True)
        
    finally:
        await conn.close()

@router.callback_query(F.data.startswith("inv_page:"))
async def handle_inventory_pagination(callback: types.CallbackQuery):
    page = callback.data.split(":")[1]
    await render_inventory_page(callback.message, callback.from_user.id, page=page, is_callback=True)
    await callback.answer()