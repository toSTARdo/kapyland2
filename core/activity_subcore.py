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
    builder.button(text="🧤 Красти", callback_data="steal")
    builder.button(text="🪵 Таран", callback_data="ram")
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

@router.callback_query(F.data == "steal")
async def handle_steal_search(callback: types.CallbackQuery):
    uid = callback.from_user.id
    conn = await get_db_connection()
    try:
        target = await conn.fetchrow(
            "SELECT owner_id, name FROM capybaras WHERE owner_id != $1 ORDER BY RANDOM() LIMIT 1", 
            uid
        )
        if not target:
            return await callback.answer("🏝 На архіпелазі нікого грабувати...")

        builder = InlineKeyboardBuilder()
        builder.button(text=f"🧤 Обікрасти {target['name']}", callback_data=f"do_steal:{target['owner_id']}")
        builder.button(text="🔙 Назад", callback_data="back_to_fight")
        builder.adjust(1)

        await callback.message.edit_text(
            f"<b>Ти підкрадаєшся до {target['name']}...</b>\n\n"
            f"• 5% — вкрасти випадкову річ\n"
            f"• 5% — розбудити ціль і получити в баняк\n"
            f"• 90% — втекти ні з чим",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    finally: await conn.close()

@router.callback_query(F.data.startswith("do_steal:"))
async def execute_steal_logic(callback: types.CallbackQuery):
    target_id = int(callback.data.split(":")[1])
    uid = callback.from_user.id
    chance = random.random()

    if chance < 0.05:
        conn = await get_db_connection()
        try:
            target_row = await conn.fetchrow("SELECT meta, name FROM capybaras WHERE owner_id = $1", target_id)
            actor_row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
            
            t_meta = json.loads(target_row['meta'])
            a_meta = json.loads(actor_row['meta'])
            
            t_items = t_meta.get("inventory", {}).get("equipment", [])
            
            if t_items:
                stolen_item = random.choice(t_items)
                t_meta["inventory"]["equipment"] = [i for i in t_items if i != stolen_item]
                a_meta.setdefault("inventory", {}).setdefault("equipment", []).append(stolen_item)
                
                await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(t_meta), target_id)
                await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(a_meta), uid)
                
                await callback.message.edit_text(f"🥷 <b>НАЙШВИДШІ ЛАПКИ НА АРХІПЕЛАЗІ!</b>\nВи непомітно витягли <b>{stolen_item['name']}</b> у {target_row['name']}!")
            else:
                await callback.message.edit_text("У цієї капібари в торбі тільки висохла шкірка мандаринки...")
        finally: await conn.close()

    elif chance < 0.10:
        await callback.message.edit_text(f"😱 <b>ЧОРТ! ВАС ПІЙМАЛИ!</b>\nКапі прокинулась і схопила тебе за вухо! Починається бій...")
        asyncio.create_task(run_battle_logic(callback, opponent_id=target_id))
    
    else:
        await callback.message.edit_text("💨 Ти злякався шурхоту і втік ні з чим. Буває...")

@router.callback_query(F.data == "ram")
async def handle_ram_search(callback: types.CallbackQuery):
    uid = callback.from_user.id
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
        meta = json.loads(row['meta'])
        items = [i['name'] for i in meta.get("inventory", {}).get("equipment", [])]
        
        if "Таран" not in items and "Бур Лаганна" not in items:
            return await callback.answer("❌ Тобі потрібен 'Таран' або 'Бур Лаганна'!", show_alert=True)

        target = await conn.fetchrow(
            "SELECT owner_id, name FROM capybaras WHERE owner_id != $1 ORDER BY RANDOM() LIMIT 1", 
            uid
        )
        if not target: return await callback.answer("Нікого тарантити...")

        builder = InlineKeyboardBuilder()
        builder.button(text=f"💥 Вдарити {target['name']}", callback_data=f"do_ram:{target['owner_id']}")
        builder.button(text="🔙 Назад", callback_data="back_to_fight")
        builder.adjust(1)

        await callback.message.edit_text(
            f"🚜 <b>Повний вперед!</b>\nТаран ініціює миттєвий бій без згоди цілі.",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    finally: await conn.close()

@router.callback_query(F.data.startswith("do_ram:"))
async def execute_ram_logic(callback: types.CallbackQuery):
    target_id = int(callback.data.split(":")[1])
    await callback.message.edit_text("💥 <b>БА-БАХ!</b>\nТаран таранить таранобеззахисну капібару.")
    asyncio.create_task(run_battle_logic(callback, opponent_id=target_id))

@router.callback_query(F.data == "back_to_fight")
async def back_to_fight(callback: types.CallbackQuery):
    await callback.message.delete()
    await cmd_fight_lobby(callback.message)

async def run_battle_logic(callback: types.CallbackQuery, opponent_id: int = None, bot_type: str = None):
    bot = callback.bot
    uid = callback.from_user.id
    
    battle_config = {
        "WEAPONS": WEAPON,
        "ARMOR": ARMOR
    }

    async def get_full_capy_data(target_id: int, b_type: str = None):
        NPC_REGISTRY = {
            "parrotbot": {
                "kapy_name": "Папуга Павло",
                "color": "🦜",
                "stats": {"attack": 1, "defense": 1, "agility": 3, "luck": 1},
                "equipped_weapon": "Весло",
                "hp_bonus": 0
            },
            "mimic": {
                "kapy_name": "Мімік",
                "color": "🗃",
                "stats": {"attack": 4, "defense": 20, "agility": 1, "luck": 2},
                "equipped_weapon": "Зуби акули",
                "hp_bonus": 7
            },
            "boss_pelican": {
                "kapy_name": "Пелікан Петро",
                "color": "🦢",
                "stats": {"attack": 15, "defense": 8, "agility": 5, "luck": 5},
                "equipped_weapon": "",
                "hp_bonus": 7,
                "is_boss": True
            }
        }

        if b_type in NPC_REGISTRY:
            return NPC_REGISTRY[b_type]

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
                "artifacts": meta.get("artifacts", []),
                "color": "🔴"
            }
        finally: await conn.close()

    p1_data = await get_full_capy_data(uid)
    p2_data = await get_full_capy_data(opponent_id, b_type=bot_type)

    if not p1_data or not p2_data:
        return await callback.message.answer("❌ Помилка: Дані капібари не знайдено.")

    p1 = Fighter(p1_data, battle_config, color="🟢")
    p2 = Fighter(p2_data, battle_config, color=p2_data.get("color", "🔴"))

    if p2_data.get("hp_bonus"):
        p2.max_hp += p2_data["hp_bonus"]
        p2.hp = p2.max_hp

    start_info = f"🏟 <b>БІЙ: {p1.name} VS {p2.name}</b>"
    msg1 = await callback.message.answer(start_info, parse_mode="HTML")
    msg2 = None
    if opponent_id and not bot_type:
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
        report = CombatEngine.resolve_turn(attacker, defender, round_num)

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
    winner_id, loser_id = None, None

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
            if winner_id:
                await conn.execute("""
                    UPDATE capybaras 
                    SET 
                        wins = wins + 1,
                        total_fights = total_fights + 1,
                        exp = exp + 3,
                        meta = meta || jsonb_build_object(
                            'weight', (meta->>'weight')::float + 3.0,
                            'stamina', GREATEST((meta->>'stamina')::int - 5, 0)
                        ) 
                    WHERE owner_id = $1
                """, winner_id)

            if loser_id and not bot_type:
                await conn.execute("""
                    UPDATE capybaras 
                    SET 
                        total_fights = total_fights + 1,
                        meta = meta || jsonb_build_object(
                            'weight', LEAST(GREATEST((meta->>'weight')::float - 3.0, 1.0), 500.0),
                            'stamina', GREATEST((meta->>'stamina')::int - 5, 0)
                        ) 
                    WHERE owner_id = $1
                """, loser_id)
            
            reward_msg = f"📈 <b>Підсумки бою:</b>\n🥇 {winner.name}: +3 кг, +3 EXP\n🥈 {loser.name}: -3 кг"
            await msg1.answer(reward_msg, parse_mode="HTML")
            if msg2:
                try: await msg2.answer(reward_msg, parse_mode="HTML")
                except: pass

        finally:
            await conn.close()
            
    elif not winner: 
        conn = await get_db_connection()
        try:
            await conn.execute("UPDATE capybaras SET total_fights = total_fights + 1 WHERE owner_id = $1", uid)
            if opponent_id and not bot_type:
                await conn.execute("UPDATE capybaras SET total_fights = total_fights + 1 WHERE owner_id = $1", opponent_id)
        finally:
            await conn.close()

async def render_inventory_page(message, user_id, page="food", is_callback=False):
    meta_data = await get_user_inventory(user_id)
    if not meta_data:
        return await message.answer("❌ Профіль не знайдено.")

    meta = json.loads(meta_data) if isinstance(meta_data, str) else meta_data
    inv = meta.get("inventory", {})
    builder = InlineKeyboardBuilder()

    ITEMS_PER_PAGE = 5

    TYPE_ICONS = {
        "weapon": "🗡️",
        "armor": "🔰",
        "artifact": "🧿"
    }

    if page == "food":
        title = "🍎 <b>Провізія</b>"
        food = inv.get("food", {})
        food_names = {"tangerines": "🍊", "melon": "🍈", "watermelon_slices": "🍉", "mango": "🥭", "kiwi": "🥝"}
        
        has_food = any(v > 0 for v in food.values())
        
        if not has_food:
            content = "<i>Твій кошик порожній... Пошукай щось на мапі!</i>"
        else:
            content = "<i>Обери їжу:</i>"
            for k, v in food.items():
                if v > 0:
                    icon = food_names.get(k, "🍱")
                    builder.button(text=f"{icon} ({v})", callback_data=f"food_choice:{k}")
        
        builder.adjust(2)

    elif page == "loot":
        title = "🧳 <b>Скарби та ресурси</b>"
        loot = inv.get("loot", {})
        
        chests = loot.get('chest', 0)
        keys = loot.get('key', 0)
        
        loot_lines = []
        if loot.get('lottery_ticket', 0) > 0: loot_lines.append(f"🎟️ Квитки: <b>{loot['lottery_ticket']}</b>")
        if keys > 0: loot_lines.append(f"🗝️ Ключі: <b>{keys}</b>")
        if chests > 0: loot_lines.append(f"🗃 Скрині: <b>{chests}</b>")
        
        content = "\n".join(loot_lines) if loot_lines else "<i>Твій сейф порожній...</i>"
        
        if chests > 0 and keys > 0:
            builder.button(text="🔓 Відкрити скриню", callback_data="open_chest")
        
        builder.adjust(1)

    elif page == "maps":
        title = "🗺 <b>Карти скарбів</b>"
        maps = inv.get("loot", {}).get("treasure_maps", [])
        
        if not maps:
            content = "<i>У тебе немає жодної карти. Купи їх у таверні!</i>"
        else:
            content = "<i>Твої замітки:</i>\n\n"
            map_lines = []
            for m in maps:
                map_lines.append(f"📍 <b>Карта {m['id']}</b>\n╰ Координати: <code>{m['pos']}</code>")
            content += "\n\n".join(map_lines)
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
            unique_list = []
            seen = {}
            for item in all_items:
                name = item['name']
                if name not in seen:
                    seen[name] = len(unique_list)
                    unique_list.append({"data": item, "count": 1})
                else:
                    unique_list[seen[name]]["count"] += 1
            
            total_items = len(unique_list)
            max_pages = (total_items - 1) // ITEMS_PER_PAGE
            start_idx = current_page * ITEMS_PER_PAGE
            end_idx = start_idx + ITEMS_PER_PAGE
            items_slice = unique_list[start_idx:end_idx]

            SELL_PRICES = {"Common": 1, "Rare": 2, "Epic": 3, "Legendary": 5}

            for info in items_slice:
                item = info["data"]
                name = item['name']
                count = info["count"]
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
                
                builder.button(
                    text=f"{r_icon}{t_icon} {name} x{count}{status}", 
                    callback_data=f"equip:{item_type}:{name}"
                )
                price = SELL_PRICES.get(rarity, 1)
                builder.button(
                    text=f"💰 {price}", 
                    callback_data=f"sell_item:{rarity}:{name}"
                )

            builder.adjust(*(2 for _ in range(len(items_slice))))
            
            if total_items > ITEMS_PER_PAGE:
                control_row = []
                if current_page > 0:
                    control_row.append(types.InlineKeyboardButton(
                        text="⬅️ Назад", callback_data=f"inv_pagination:{page}:{current_page-1}"))
                
                control_row.append(types.InlineKeyboardButton(
                    text=f"📄 {current_page + 1}/{max_pages + 1}", callback_data="none"))
                
                if current_page < max_pages:
                    control_row.append(types.InlineKeyboardButton(
                        text="Вперед ➡️", callback_data=f"inv_pagination:{page}:{current_page+1}"))
                
                builder.row(*control_row)

            content = f"Обери предмет (Сторінка {current_page + 1}):"

    nav_row = []
    pages_meta = {"food": "🍎 Їжа", "loot": "🧳 Лут", "maps": "🗺 Мапи", "items": "⚔️ Речі"}
    
    for p_key, p_text in pages_meta.items():
        if page != p_key:
            nav_row.append(types.InlineKeyboardButton(text=p_text, callback_data=f"inv_page:{p_key}:0"))
    
    builder.row(*nav_row)

    text = f"{title}\n━━━━━━━━━━━━━━━\n{content}"
    
    markup = builder.as_markup()
    if is_callback:
        await message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=markup, parse_mode="HTML")

@router.callback_query(F.data.startswith("sell_item:"))
async def handle_sell_equipment(callback: types.CallbackQuery):
    _, rarity, item_name = callback.data.split(":")
    uid = callback.from_user.id
    
    prices = {"Common": 1, "Rare": 2, "Epic": 3, "Legendary": 5}
    reward = prices.get(rarity, 1)
    
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
        if not row: return
        
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        
        curr_eq = meta.get("equipment", {})
        if item_name in [curr_eq.get("weapon"), curr_eq.get("armor"), curr_eq.get("artifact")]:
            return await callback.answer("❌ Спочатку зніми цей предмет!", show_alert=True)

        inventory_eq = meta.get("inventory", {}).get("equipment", [])
        
        found_index = -1
        for i, it in enumerate(inventory_eq):
            if it.get("name") == item_name:
                found_index = i
                break
        
        if found_index == -1:
            return await callback.answer("❌ Предмет не знайдено в інвентарі.")

        inventory_eq.pop(found_index)
        
        food_dict = meta.get("inventory", {}).get("food", {})
        current_slices = food_dict.get("watermelon_slices", 0)
        
        food_dict["watermelon_slices"] = current_slices + reward
        meta["inventory"]["food"] = food_dict
        meta["inventory"]["equipment"] = inventory_eq

        await conn.execute(
            "UPDATE capybaras SET meta = $1 WHERE owner_id = $2", 
            json.dumps(meta), uid
        )

        await callback.answer(f"🍉 Продано! Отримано {reward} скибочок кавуна.")

    finally:
        await conn.close()

@router.callback_query(F.data.startswith("food_choice:"))
async def handle_food_choice(callback: types.CallbackQuery):
    food_type = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    meta_data = await get_user_inventory(user_id)
    meta = json.loads(meta_data) if isinstance(meta_data, str) else meta_data
    count = meta.get("inventory", {}).get("food", {}).get(food_type, 0)
    
    if count <= 0:
        return await callback.answer("Нічого немає! Ти бідний, ти жебрак...")

    food_names = {"tangerines": "🍊", "melon": "🍈", "watermelon_slices": "🍉", "mango": "🥭", "kiwi": "🥝"}
    icon = food_names.get(food_type, "🍱")

    builder = InlineKeyboardBuilder()
    builder.button(text=f"🍴 З'їсти 1", callback_data=f"eat:one:{food_type}")
    
    if count > 1:
        builder.button(text=f"🍴 З'їсти все ({count})", callback_data=f"eat:all:{food_type}")
    
    builder.button(text="🔙 Назад", callback_data="inv_page:food")
    builder.adjust(1)

    await callback.message.edit_text(
        f"🍎 <b>Твій вибір: {icon}</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("eat:"))
async def handle_eat(callback: types.CallbackQuery):
    _, amount_type, food_type = callback.data.split(":")
    user_id = callback.from_user.id
    
    WEIGHT_TABLE = {
        "tangerines": 0.5,
        "watermelon_slices": 1.0,
        "melon": 5.0,
        "mango": 0.5,
        "kiwi": 0.5
    }
    
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow(
            "SELECT meta, exp, lvl FROM capybaras WHERE owner_id = $1", 
            user_id
        )
        if not row: return
        
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        current_exp = row['exp'] or 0
        
        current_count = meta.get("inventory", {}).get("food", {}).get(food_type, 0)
        
        if current_count <= 0:
            await callback.answer("Нічого не залишилося! Ти бідний, ти жебрак...")
            return await render_inventory_page(callback.message, user_id, page="food", is_callback=True)

        to_eat = 1 if amount_type == "one" else current_count
        
        unit_weight = WEIGHT_TABLE.get(food_type, 0.5)
        total_bonus = to_eat * unit_weight
        
        meta["inventory"]["food"][food_type] -= to_eat
        meta["weight"] = round(min(meta.get("weight", 20.0) + total_bonus, 500.0), 2)
        
        new_exp = current_exp + int(total_bonus) 
        if total_bonus < 1 and random.random() < total_bonus:
            new_exp += 1

        await conn.execute("""
            UPDATE capybaras 
            SET meta = $1, exp = $2 
            WHERE owner_id = $3
        """, json.dumps(meta, ensure_ascii=False), new_exp, user_id)
        
        await callback.answer(
            f"Капі-ням!\n"
            f"Вага: +{total_bonus} кг\n"
            f"Досвід: +{int(total_bonus) if total_bonus >= 1 else '✨'} EXP"
        )
        
        await render_inventory_page(callback.message, user_id, page="food", is_callback=True)

    finally:
        await conn.close()

@router.callback_query(F.data == "open_chest")
async def handle_open_chest(callback: types.CallbackQuery):
    uid = callback.from_user.id
    conn = await get_db_connection()
    
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
        if not row: return
        
        meta = row['meta']
        loot = meta.get("equipment", {}).get("loot", {})
        
        if loot.get('chest', 0) < 1 or loot.get('key', 0) < 1:
            return await callback.answer("❌ Тобі потрібен і ключ, і скриня!", show_alert=True)

        await conn.execute("""
            UPDATE capybaras 
            SET meta = jsonb_set(
                jsonb_set(
                    jsonb_set(meta, '{equipment, loot, chest}', ((meta->'equipment'->'loot'->>'chest')::int - 1)::text::jsonb),
                    '{equipment, loot, key}', ((meta->'equipment'->'loot'->>'key')::int - 1)::text::jsonb
                ),
                '{watermelon_slices}', ((COALESCE(meta->>'watermelon_slices', '0')::int) + 50)::text::jsonb
            )
            WHERE owner_id = $1
        """, uid)
        
        await callback.answer("🎊 Бум! Скриня піддалася!", show_alert=True)
        await callback.message.edit_text(
            "🔓 <b>Скриня відкрита!</b>\n\n"
            "В середині виявилося <b>50 скибочок кавуна</b> 🍉",
            parse_mode="HTML",
            reply_markup=None
        )
        
    finally:
        await conn.close()

@router.callback_query(F.data == "fish")
async def handle_fishing(callback: types.CallbackQuery):
    uid = callback.from_user.id
    conn = await get_db_connection()
    
    try:
        row = await conn.fetchrow("SELECT name, meta FROM capybaras WHERE owner_id = $1", uid)
        if not row: return
        
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        stamina = meta.get("stamina", 0)
        
        if "вудочка" not in meta.get("equipment", {}).get("weapon", "").lower():
            return await callback.answer("❌ Тобі потрібна вудочка!", show_alert=True)
        
        if stamina < 10:
            return await callback.answer("🪫 Мало енергії (треба 10)", show_alert=True)

        loot_pool = [
            {"name": "🦴 Стара кістка", "min_w": 0.1, "max_w": 0.4, "chance": 12, "type": "trash"},
            {"name": "📰 Промокла газета", "min_w": 0.05, "max_w": 0.1, "chance": 12, "type": "trash"},
            {"name": "🥫 Іржава бляшанка", "min_w": 0.1, "max_w": 0.3, "chance": 10, "type": "trash"},

            {"name": "🐟 Океанічний карась", "min_w": 0.3, "max_w": 1.5, "chance": 15, "type": "loot"},
            {"name": "🐠 Уробороокеанський Окунь", "min_w": 0.2, "max_w": 0.8, "chance": 10, "type": "loot"},
            {"name": "🐡 Риба-пупупу", "min_w": 0.5, "max_w": 2.0, "chance": 5, "type": "loot"},
            {"name": "🐙 Восьмирук", "min_w": 1.0, "max_w": 5.0, "chance": 4, "type": "loot"},
            {"name": "🦀 Бокохід", "min_w": 0.2, "max_w": 1.2, "chance": 5, "type": "loot"},
            {"name": "🦈 Маленька акула", "min_w": 10.0, "max_w": 40.0, "chance": 1, "type": "loot"},
            
            {"name": "🍉 Скибочка кавуна", "min_w": 0.3, "max_w": 0.6, "chance": 20, "type": "food", "key": "watermelon_slices"},
            {"name": "🍊 Мандарин", "min_w": 0.1, "max_w": 0.2, "chance": 8, "type": "food", "key": "tangerines"},
            {"name": "🥭 Манго", "min_w": 0.4, "max_w": 0.7, "chance": 2, "type": "food", "key": "mango"},
            {"name": "🥝 Ківі", "min_w": 0.1, "max_w": 0.15, "chance": 2, "type": "food", "key": "kiwi"},
            {"name": "🍈 Диня", "min_w": 2.0, "max_w": 4.0, "chance": 4, "type": "food", "key": "melons"},
            
            {"name": "🗃 Скриня", "min_w": 5.0, "max_w": 10.0, "chance": 2, "type": "special", "key": "chest"},
            {"name": "🗝️ Ключ", "min_w": 0.1, "max_w": 0.2, "chance": 2, "type": "special", "key": "key"},
            {"name": "🎟️ Лотерейний квиток", "min_w": 0.01, "max_w": 0.01, "chance": 1, "type": "special", "key": "lottery_ticket"}
        ]
        
        item = random.choices(loot_pool, weights=[i['chance'] for i in loot_pool])[0]
        item_name = item['name']
        item_type = item['type']
        fish_weight = round(random.uniform(item['min_w'], item['max_w']), 2)

        if item_type == "trash":
            sql = "UPDATE capybaras SET meta = jsonb_set(meta, '{stamina}', (GREATEST((meta->>'stamina')::int - 10, 0))::text::jsonb) WHERE owner_id = $1"
            args = [uid]
        else:
            if item_type == "food":
                path = ['inventory', 'food', item['key']]
                current_val = f"COALESCE(meta->'inventory'->'food'->>'{item['key']}', '0')::int"
            else:
                target_key = item.get('key', item_name)
                path = ['inventory', 'loot', target_key]
                current_val = f"COALESCE(meta->'inventory'->'loot'->>'{target_key}', '0')::int"

            sql = f"""
                UPDATE capybaras 
                SET meta = jsonb_set(
                    jsonb_set(meta, '{{stamina}}', (GREATEST((meta->>'stamina')::int - 10, 0))::text::jsonb),
                    $2, ({current_val} + 1)::text::jsonb
                ) WHERE owner_id = $1
            """
            args = [uid, path]
        inventory_note = "📦 <i>Предмет додано в інвентар!</i>"

        await callback.message.edit_text(
            f"Чілимо... Раптом поплавок смикнувся!\n"
            f"Ііііі... Твій улов: <b>{item_name} ({fish_weight} кг)</b>\n"
            f"{inventory_note}\n"
            f"🔋 Залишок енергії: {max(0, stamina - 10)}%",
            parse_mode="HTML"
        )
        await callback.answer(f"Зловлено: {item_name}!")

    finally:
        await conn.close()

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