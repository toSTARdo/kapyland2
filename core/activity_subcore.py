import asyncio, json, random
from aiogram import Router, types, html, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.helpers import check_daily_limit
from handlers.emotes import send_victory_celebration
from core.models import Fighter, CombatEngine
from core.capybara_mechanics import get_user_inventory, grant_exp_and_lvl
from database.postgres_db import get_db_connection
from config import BASE_HITPOINTS, ARTIFACTS, RARITY_META, WEAPON, ARMOR
GACHA_ITEMS = ARTIFACTS

router = Router()

#ВИКЛИКИ

@router.message(F.text.startswith("🍻"))
@router.callback_query(F.data == "social")
async def cmd_arena_hub(event: types.Message | types.CallbackQuery):
    is_callback = isinstance(event, types.CallbackQuery)
    uid = event.from_user.id
    message = event.message if is_callback else event

    conn = await get_db_connection()
    try:
        players = await conn.fetch("""
            SELECT u.tg_id, u.username, c.lvl 
            FROM users u
            JOIN capybaras c ON u.tg_id = c.owner_id
            WHERE u.tg_id != $1 
            ORDER BY c.lvl DESC LIMIT 8
        """, uid)
    finally:
        await conn.close()

    builder = InlineKeyboardBuilder()

    if players:
        for p in players:
            name = p['username'][:15]
            builder.row(types.InlineKeyboardButton(
                text=f"🐾 {name} (Lvl {p['lvl']})", 
                callback_data=f"user_menu:{p['tg_id']}")
            )
    
    builder.row(
        types.InlineKeyboardButton(text="🤖 Бій з ботом", callback_data="fight_bot"),
        types.InlineKeyboardButton(text="🏆 Топ", callback_data="leaderboard")
    )
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад до Порту", callback_data="open_port"))

    text = (
        "⚔️ <b>Таверна «Гнилий Апельсин»</b>\n"
        "━━━━━━━━━━━━━━━\n"
    )

    if is_callback:
        try:
            await event.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        except:
            pass
        await event.answer()
    else:
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.startswith("user_menu:"))
async def user_menu_handler(callback: types.CallbackQuery):
    target_id = int(callback.data.split(":")[1])
    uid = callback.from_user.id
    
    conn = await get_db_connection()
    try:
        players = await conn.fetch("""
            SELECT u.tg_id, u.username, c.lvl 
            FROM users u
            JOIN capybaras c ON u.tg_id = c.owner_id
            WHERE u.tg_id != $1 
            ORDER BY c.lvl DESC LIMIT 8
        """, uid)
    finally:
        await conn.close()

    builder = InlineKeyboardBuilder()

    for p in players:
        builder.button(
            text=f"🐾 {p['username']} (Lvl {p['lvl']})", 
            callback_data=f"user_menu:{p['tg_id']}"
        )
        
        if p['tg_id'] == target_id:
            builder.button(text="⚔️", callback_data=f"challenge_{target_id}")
            builder.button(text="💞", callback_data=f"date_request:{target_id}")
            builder.button(text="🎁", callback_data=f"gift_to:{target_id}")
            builder.button(text="🧤", callback_data=f"steal_from:{target_id}")
            builder.button(text="🪵", callback_data=f"ram:{target_id}")
            builder.button(text="🔍", callback_data=f"inspect:{target_id}")

    builder.button(text="🤖 Побитися з ботом", callback_data="fight_bot")
    builder.button(text="🏆 Таблиця лідерів", callback_data="leaderboard")

    layout = []
    for p in players:
        layout.append(1)
        if p['tg_id'] == target_id:
            layout.append(6)
    layout.append(1)
    layout.append(1)
    
    builder.adjust(*layout)

    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("challenge_"))
async def send_challenge(callback: types.CallbackQuery):
    data = callback.data.split("_")
    opponent_id = int(data[1])
    challenger_id = callback.from_user.id
    challenger_name = callback.from_user.first_name

    if opponent_id == challenger_id:
        return await callback.answer("Ви не можете викликати самого себе!", show_alert=True)

    builder = InlineKeyboardBuilder()
    builder.button(text="🤝 ПРИЙНЯТИ", callback_data=f"accept_{challenger_id}_{opponent_id}")
    builder.button(text="🏳️ ВІДМОВИТИСЯ", callback_data=f"decline_{challenger_id}_{opponent_id}")
    builder.adjust(2)

    await callback.message.answer(
        f"⚔️ <b>ПУБЛІЧНИЙ ВИКЛИК!</b>\n"
        f"Пірабара {html.bold(challenger_name)} кидає рукавичку <a href='tg://user?id={opponent_id}'>опоненту</a>!\n\n"
        f"<i>Тільки викликаний гравець може прийняти бій.</i>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer("Виклик кинуто в чат!")

@router.callback_query(F.data.startswith("decline_"))
async def battle_declined(callback: types.CallbackQuery):
    data = callback.data.split("_")
    opponent_id = int(data[2])

    if callback.from_user.id != opponent_id:
        return await callback.answer("Ти не можеш відмовитися за іншого!", show_alert=True)

    await callback.message.edit_text(f"🏳️ Опонент злякався і втік у кущі.", parse_mode="HTML")

#ЗАПУСК БОЮ

@router.callback_query(F.data.startswith("accept_"))
async def handle_accept(callback: types.CallbackQuery):
    data = callback.data.split("_")
    challenger_id = int(data[1])
    opponent_id = int(data[2])
    
    if callback.from_user.id != opponent_id:
        return await callback.answer("Це виклик не для тебе! ⛔", show_alert=True)

    await callback.message.edit_text("🚀 Бій прийнято! Капібари виходять на дуель... (-5 ⚡)")
    
    asyncio.create_task(run_battle_logic(callback, opponent_id=challenger_id))
    await callback.answer()

@router.callback_query(F.data == "fight_bot")
async def handle_fight_bot(callback: types.CallbackQuery):
    await callback.message.edit_text("🤖 Папуга Павло гострить дзьоб...")
    asyncio.create_task(run_battle_logic(callback, bot_type="parrotbot"))
    await callback.answer()

@router.callback_query(F.data.startswith("steal_from:"))
async def execute_steal_logic(callback: types.CallbackQuery):
    target_id = int(callback.data.split(":")[1])
    uid = callback.from_user.id
    
    conn = await get_db_connection()
    try:
        actor_row = await conn.fetchrow("SELECT meta, name FROM capybaras WHERE owner_id = $1", uid)
        target_row = await conn.fetchrow("SELECT meta, name FROM capybaras WHERE owner_id = $1", target_id)
        
        if not actor_row or not target_row: return
        
        a_meta = json.loads(actor_row['meta']) if isinstance(actor_row['meta'], str) else actor_row['meta']
        t_meta = json.loads(target_row['meta']) if isinstance(target_row['meta'], str) else target_row['meta']
        
        can_steal, _ = check_daily_limit(a_meta, "steal")
        if not can_steal:
            return await callback.answer("🥷 Ти вже сьогодні виходив на полювання. Спробуй завтра!", show_alert=True)

        base_success_chance = 0.05
        base_catch_chance = 0.10

        luck_stat = a_meta.get("stats", {}).get("luck", 1)
        luck_bonus = luck_stat * 0.01
        
        sleep_bonus = 0.10 if t_meta.get("status") == "sleep" else 0.0
        
        equipped_items = a_meta.get("equipment", [])
        has_steal_item = any("steal" in str(item).lower() for item in equipped_items)

        if has_steal_item:
            final_success_chance = 0.75
            final_catch_chance = 0.85
        else:
            final_success_chance = base_success_chance + luck_bonus + sleep_bonus
            final_catch_chance = final_success_chance + base_catch_chance

        roll = random.random()

        if roll < final_success_chance:
            t_items = t_meta.get("inventory", {}).get("equipment", [])
            
            if t_items:
                stolen_item = random.choice(t_items)
                t_meta["inventory"]["equipment"] = [i for i in t_items if i != stolen_item]
                a_meta.setdefault("inventory", {}).setdefault("equipment", []).append(stolen_item)

                await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(t_meta, ensure_ascii=False), target_id)
                await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(a_meta, ensure_ascii=False), uid)
                
                await callback.message.edit_text(
                    f"🥷 <b>НАЙШВИДШІ ЛАПКИ!</b>\n"
                    f"Ви непомітно витягли <b>{stolen_item['name']}</b> у {target_row['name']}!\n"
                    f"🍀 Твій успіх: {int(final_success_chance*100)}%",
                    parse_mode="HTML"
                )
            else:
                await callback.message.edit_text(f"🧤 Ти обшукав {target_row['name']}, але в кишенях порожньо...")

        elif roll < final_catch_chance:
            if t_meta.get("status") == "sleep":
                start_time_str = t_meta.get("sleep_start")
                gained_stamina = 0
                
                if start_time_str:
                    start_time = datetime.datetime.fromisoformat(start_time_str)
                    now = datetime.datetime.now()
                    duration_mins = (now - start_time).total_seconds() / 60
                    gained_stamina = int(duration_mins * (100 / 120))
                    
                t_meta["status"] = "active"
                t_meta["stamina"] = min(100, t_meta.get("stamina", 0) + gained_stamina)
                t_meta.pop("wake_up", None)
                t_meta.pop("sleep_start", None)
                
                await conn.execute(
                    "UPDATE capybaras SET meta = $1 WHERE owner_id = $2", 
                    json.dumps(t_meta, ensure_ascii=False), target_id
                )
                
                wake_msg = f"\n🔔 Ціль миттєво прокинулась! (+{gained_stamina}⚡)"
            else:
                wake_msg = ""

            await callback.message.edit_text(
                f"😱 <b>ЧОРТ! ВАС ПІЙМАЛИ!</b>{wake_msg}\n"
                f"Починається бій за життя!", parse_mode="HTML"
            )
            asyncio.create_task(run_battle_logic(callback, opponent_id=target_id))

        else:
            await callback.answer("💨 Ти злякався шурхоту і втік ні з чим. Буває...", show_alert=True)

    except Exception as e:
        print(f"Steal Error: {e}")
        await callback.answer("🚨 Злодійська удача сьогодні не на твоїм боці...")
    finally: await conn.close()

@router.callback_query(F.data.startswith("ram:"))
async def execute_ram_logic(callback: types.CallbackQuery):
    target_id = int(callback.data.split(":")[1])
    uid = callback.from_user.id
    
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        
        can_ram, _ = check_daily_limit(meta, "ram")
        if not can_ram:
            return await callback.answer("💥 Твій корабель ще лагодять після минулого тарану. Спробуй завтра!", show_alert=True)

        inv_items = [i['name'].lower() for i in meta.get("inventory", {}).get("equipment", [])]
        has_ram = any("таран" in item or "бур лаганна" in item for item in inv_items)
        
        if not has_ram:
            return await callback.answer("❌ Тобі потрібен 'Таран' або 'Бур Лаганна' в інвентарі!", show_alert=True)

        await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(meta), uid)

        await callback.message.edit_text("💥 <b>БА-БАХ!</b>\nТи влетів у суперника на повному ходу! Бій починається негайно!", parse_mode="HTML")
        
        asyncio.create_task(run_battle_logic(callback, opponent_id=target_id))
        
    finally: await conn.close()

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
            res_winner = await grant_exp_and_lvl(winner_id, exp_gain=3, weight_gain=3.0)
            
            if winner_id and res_winner:
                await conn.execute("""
                    UPDATE capybaras 
                    SET 
                        wins = wins + 1,
                        total_fights = total_fights + 1,
                        meta = jsonb_set(meta, '{stamina}', (GREATEST((meta->>'stamina')::int - 5, 0))::text::jsonb)
                    WHERE owner_id = $1
                """, winner_id)

            res_loser = None
            if loser_id and not bot_type:
                res_loser = await grant_exp_and_lvl(loser_id, exp_gain=0, weight_gain=-3.0)
                
                await conn.execute("""
                    UPDATE capybaras 
                    SET 
                        total_fights = total_fights + 1,
                        meta = jsonb_set(meta, '{stamina}', (GREATEST((meta->>'stamina')::int - 5, 0))::text::jsonb)
                    WHERE owner_id = $1
                """, loser_id)
            
            reward_msg = (
                f"📈 <b>Підсумки бою:</b>\n"
                f"🥇 {winner.name}: +3 кг, +3 EXP (Lvl: {res_winner['new_lvl']})\n"
                f"🥈 {loser.name}: -3 кг"
            )

            await msg1.answer(reward_msg, parse_mode="HTML")
            if msg2:
                try: await msg2.answer(reward_msg, parse_mode="HTML")
                except: pass

            if winner_id:
                await send_victory_celebration(msg1, winner_id)

        finally:
            await conn.close()

@router.callback_query(F.data.startswith("inspect:"))
async def handle_inspect_player(callback: types.CallbackQuery):
    target_id = int(callback.data.split(":")[1])
    
    conn = await get_db_connection()
    try:
        target = await conn.fetchrow("""
            SELECT u.username, c.name as capy_name, c.lvl, c.karma, c.zen, c.meta, s.name as ship_name
            FROM users u 
            JOIN capybaras c ON u.tg_id = c.owner_id 
            LEFT JOIN ships s ON c.ship_id = s.id
            WHERE u.tg_id = $1
        """, target_id)
        
        if not target:
            return await callback.answer("Капібара зникла у тумані...")

        meta = json.loads(target['meta']) if isinstance(target['meta'], str) else target['meta']
        
        weight = meta.get("weight", 0.0)
        status = meta.get("status", "active")
        mood = meta.get("mood", "Normal")
        equip = meta.get("equipment", {})
        
        status_text = "💤 Спить" if status == "sleep" else "🐾 Гуляє архіпелагом"
        karma_title = "😇 Свята булочка" if target['karma'] > 50 else "😈 Мародерна капі" if target['karma'] < -50 else "😐 Нейтральна капі"
        
        text = (
            f"📜 <b>Детальне досьє: {target['capy_name']}</b>\n"
            f"👤 Власник: {target['username']}\n"
            f"🚢 Човен: <b>{target['ship_name'] or 'Самотній плавець'}</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🔹 <b>Статус:</b> {status_text}\n"
            f"🔹 <b>Карма:</b> {karma_title} ({target['karma']})\n"
            f"🔹 <b>Настрій:</b> {mood}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🎖 <b>Рівень:</b> {target['lvl']}\n"
            f"⚖️ <b>Вага:</b> {weight} кг\n"
            f"━━━━━━━━━━━━━━━\n"
            f"⚔️ <b>Арсенал:</b>\n"
            f"└ Снаряда: <b>{equip.get('weapon', 'Лапки')}</b>\n"
            f"└ Захист: <b>{equip.get('armor', 'Хутро')}</b>\n"
            f"└ Реліквія: <b>{equip.get('artifact') or 'Порожньо'}</b>\n\n"
            f"<i>Капібара виглядає {mood.lower()}, здається, вона готова до пригод.</i>"
        )

        builder = InlineKeyboardBuilder()
        builder.button(text="⚔️ Виклик", callback_data=f"challenge_{target_id}")
        builder.button(text="🎁 Подарунок", callback_data=f"gift_to:{target_id}")
        builder.button(text="🔙 Назад", callback_data="social")
        builder.adjust(2, 1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        
    finally:
        await conn.close()

ITEM_DISPLAY_NAMES = {
    "watermelon_slices": "🍉 Скибочка кавуна",
    "tangerines": "🍊 Мандарин",
    "melon": "🍈 Диня",
    "kiwi": "🥝 Ківі",
    "mango": "🥭 Манго"
}

@router.callback_query(F.data.startswith("gift_to:"))
async def gift_category_select(callback: types.CallbackQuery):
    target_id = int(callback.data.split(":")[1])
    uid = callback.from_user.id
    
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        
        can_gift, _ = check_daily_limit(meta, "gift")
        if not can_gift:
            return await callback.answer("🎁 Ти вже сьогодні надсилав подарунок. Спробуй завтра!", show_alert=True)
        
        await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(meta), uid)
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🍎 Їжа", callback_data=f"send_cat:food:{target_id}")
        builder.button(text="💎 Ресурси", callback_data=f"send_cat:materials:{target_id}")
        builder.button(text="⚔️ Спорядження", callback_data=f"send_cat:equipment:{target_id}")
        builder.button(text="🔙 Назад", callback_data=f"social")
        builder.adjust(2, 1, 1)

        await callback.message.edit_text(
            "🎁 <b>Меню подарунків</b>\nОберіть категорію предметів для передачі:",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    finally:
        await conn.close()

@router.callback_query(F.data.startswith("send_cat:"))
async def gift_item_select(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    category = parts[1]
    target_id = int(parts[2])
    uid = callback.from_user.id
    
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        
        can_gift, _ = check_daily_limit(meta, "gift")
        if not can_gift:
            return await callback.answer("🎁 Ти вже сьогодні надсилав подарунок. Спробуй завтра!", show_alert=True)

        builder = InlineKeyboardBuilder()
        has_items = False
        
        if category == "equipment":
            equipment_list = meta.get("inventory", {}).get("equipment", [])
            current_equip = meta.get("equipment", {}).values()
            
            for idx, item in enumerate(equipment_list):
                rarity = item.get("rarity", "Common").capitalize()
                
                if rarity in ["Common", "Rare"] and item['name'] not in current_equip:
                    builder.button(
                        text=f"🎁 {item['name']}", 
                        callback_data=f"gift_exec:equip:{idx}:{target_id}"
                    )
                    has_items = True
        else:
            items = meta.get("inventory", {}).get(category, {})
            for item_key, count in items.items():
                if count > 0:
                    builder.button(
                        text=f"{item_key} ({count})", 
                        callback_data=f"gift_exec:stack:{category}:{item_key}:{target_id}"
                    )
                    has_items = True
        
        if not has_items:
            return await callback.answer("У вас немає доступних предметів у цій категорії", show_alert=True)
            
        builder.button(text="🔙 Назад", callback_data=f"gift_to:{target_id}")
        builder.adjust(1)

        await callback.message.edit_text(
            f"🎁 <b>Ваш інвентар ({category}):</b>",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    finally:
        await conn.close()

@router.callback_query(F.data.startswith("gift_exec:"))
async def execute_gift_transfer(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    gift_type = parts[1]
    uid = callback.from_user.id
    
    conn = await get_db_connection()
    try:
        if gift_type == "equip":
            item_idx = int(parts[2])
            target_id = int(parts[3])
            
            a_data = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
            t_data = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", target_id)
            
            a_meta = json.loads(a_data['meta']) if isinstance(a_data['meta'], str) else a_data['meta']
            t_meta = json.loads(t_data['meta']) if isinstance(t_data['meta'], str) else t_data['meta']
            
            inv = a_meta.get("inventory", {}).get("equipment", [])
            if item_idx >= len(inv): return await callback.answer("Помилка індексу")
            
            gift_item = inv.pop(item_idx)
            t_meta.setdefault("inventory", {}).setdefault("equipment", []).append(gift_item)
            
            await conn.execute("UPDATE capybaras SET meta = $1, karma = karma + 5 WHERE owner_id = $2", json.dumps(a_meta), uid)
            await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(t_meta), target_id)
            item_name = gift_item['name']

        else:
            category = parts[2]
            item_key = parts[3]
            target_id = int(parts[4])
            
            res = await conn.execute(f"""
                UPDATE capybaras SET meta = jsonb_set(meta, '{{inventory, {category}, {item_key}}}', 
                (GREATEST((meta->'inventory'->'{category}'->>'{item_key}')::int - 1, 0))::text::jsonb)
                WHERE owner_id = $1 AND (meta->'inventory'->'{category}'->>'{item_key}')::int > 0
            """, uid)

            if res == "UPDATE 0": return await callback.answer("Предмет закінчився")

            await conn.execute(f"""
                UPDATE capybaras SET meta = jsonb_set(meta, '{{inventory, {category}, {item_key}}}', 
                (COALESCE(meta->'inventory'->'{category}'->>'{item_key}', '0')::int + 1)::text::jsonb)
                WHERE owner_id = $1
            """, target_id)
            
            await conn.execute("UPDATE capybaras SET karma = karma + 1 WHERE owner_id = $1", uid)
            item_name = item_key

        await callback.message.edit_text(f"✨ Успіх!\nВи подарували {ITEM_DISPLAY_NAMES[item_name]} та покращили свою карму.", parse_mode="HTML")
        
        try:
            await callback.bot.send_message(target_id, f"🎁 Гей! Тобі прийшов подарунок: {ITEM_DISPLAY_NAMES[item_name]}!")
        except: pass

    finally:
        await conn.close()

@router.callback_query(F.data.startswith("leaderboard"))
async def show_leaderboard(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    criteria = parts[1] if len(parts) > 1 else "mass"
    page = int(parts[2]) if len(parts) > 2 else 0
    offset = page * 5

    conn = await get_db_connection()
    try:
        if criteria == "mass":
            title = "⚖️ Топ Найважчих"
            label = "кг"
            query = """
                SELECT u.username, (c.meta->>'weight')::float as val 
                FROM users u JOIN capybaras c ON u.tg_id = c.owner_id 
                ORDER BY val DESC LIMIT 5 OFFSET $1
            """
        elif criteria == "lvl":
            title = "🎖 Топ Наймудріших"
            label = "Lvl"
            query = """
                SELECT u.username, c.lvl as val 
                FROM users u JOIN capybaras c ON u.tg_id = c.owner_id 
                ORDER BY val DESC LIMIT 5 OFFSET $1
            """
        else: # winrate
            title = "⚔️ Топ Найсильніших"
            label = "%"
            query = """
                SELECT u.username, 
                ROUND((c.wins::float / GREATEST(c.total_fights, 1)) * 100) as val
                FROM users u JOIN capybaras c ON u.tg_id = c.owner_id 
                WHERE c.total_fights > 0
                ORDER BY val DESC, c.wins DESC LIMIT 5 OFFSET $1
            """

        rows = await conn.fetch(query, offset)
        
        text = f"<b>{title}</b>\n━━━━━━━━━━━━━━━\n"
        for i, row in enumerate(rows):
            pos = i + offset + 1
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(pos, "🐾")
            text += f"{medal} {pos}. <b>{row['username']}</b> — {row['val']}{label}\n"

        if not rows:
            text += "<i>На цій сторінці порожньо...</i>"

        builder = InlineKeyboardBuilder()
        
        builder.button(text="⚖️ Вага", callback_data=f"leaderboard:mass:0")
        builder.button(text="🎖 Рівень", callback_data=f"leaderboard:lvl:0")
        builder.button(text="⚔️ Бій", callback_data=f"leaderboard:winrate:0")
        
        nav_btns = []
        if page > 0:
            nav_btns.append(types.InlineKeyboardButton(text="⬅️", callback_data=f"leaderboard:{criteria}:{page-1}"))
        nav_btns.append(types.InlineKeyboardButton(text="➡️", callback_data=f"leaderboard:{criteria}:{page+1}"))
        
        if nav_btns:
            builder.row(*nav_btns)
            
        builder.row(types.InlineKeyboardButton(text="🔙 Назад", callback_data="social"))
        builder.adjust(3, len(nav_btns), 1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    finally:
        await conn.close()

@router.callback_query(F.data.startswith("date_request:"))
async def send_date_request(callback: types.CallbackQuery):
    target_id = int(callback.data.split(":")[1])
    sender_id = callback.from_user.id
    sender_name = callback.from_user.full_name

    if target_id == sender_id:
        return await callback.answer("Ти не можеш піти на побачення сам із собою (хоча це теж чіл).", show_alert=True)

    invite_kb = InlineKeyboardBuilder()
    invite_kb.button(text="🥂 Погодитись", callback_data=f"date_accept:{sender_id}")
    invite_kb.button(text="💔 Відхилити", callback_data="date_reject")
    
    try:
        await callback.bot.send_message(
            target_id,
            f"💌 <b>Романтика!</b>\n\nКапібара <b>{sender_name}</b> запрошує тебе на романтичне побачення до озера!",
            reply_markup=invite_kb.as_markup(),
            parse_mode="HTML"
        )
        await callback.answer("💌 Запит на побачення надіслано!", show_alert=True)
    except:
        await callback.answer("🚨 Не вдалося надіслати запит.", show_alert=True)

import random

@router.callback_query(F.data.startswith("date_accept:"))
async def accept_date(callback: types.CallbackQuery):
    partner_id = int(callback.data.split(":")[1])
    my_id = callback.from_user.id
    
    date_plots = [
        "🏴‍☠️ Ви пробралися на ворожий фрегат і вкрали бочку кавунового рому!",
        "🏜️ Ви знайшли захований на березі скарб, але там були лише стиглі манго. Ви з'їли їх разом.",
        "🌊 Ви влаштували перегони на дельфінах вздовж узбережжя Ліворн-Бей!",
        "🃏 Ви обіграли старого пірата в карти в таверні, але вигране спустили в газино.",
        "🔥 Ви розпалили величезне багаття на скелях, щоб заманити та розграбувати торгові судна, і просто чілили разом.",
        "🍻 Ви випили стільки елю в таверні, що почали бачити морських зміїв.",
        "⚓ Ви разом начищали якір корабля до блиску, поки не почали бачити в ньому своє відображення."
    ]
    current_plot = random.choice(date_plots)

    conn = await get_db_connection()
    try:
        users_data = await conn.fetch("SELECT owner_id, meta FROM capybaras WHERE owner_id IN ($1, $2)", my_id, partner_id)
        if len(users_data) < 2: return await callback.answer("Партнер десь зник...")

        metas = {u['owner_id']: (json.loads(u['meta']) if isinstance(u['meta'], str) else u['meta']) for u in users_data}

        for uid, p_id in [(my_id, partner_id), (partner_id, my_id)]:
            rel = metas[uid].get("relationships", {})
            p_stats = rel.get(str(p_id), {"dates": 0, "status": "знайомі"})
            
            p_stats["dates"] += 1
            
            if p_stats["dates"] >= 50:
                p_stats["status"] = "💍 у шлюбі"
            elif p_stats["dates"] >= 10:
                p_stats["status"] = "❤️ пара"
            
            rel[str(p_id)] = p_stats
            metas[uid]["relationships"] = rel
            
            metas[uid]["stamina"] = min(100, metas[uid].get("stamina", 0) + 15)

            await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", 
                               json.dumps(metas[uid], ensure_ascii=False), uid)

        current_status = metas[my_id]["relationships"][str(partner_id)]["status"]
        date_count = metas[my_id]["relationships"][str(partner_id)]["dates"]

        res_text = (
            f"💖 <b>Романтичне побачення!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"<i>{current_plot}</i>\n\n"
            f"📊 Результат:\n"
            f"• Побачення №<b>{date_count}</b>\n"
            f"• Ваш статус: <b>{current_status}</b>\n"
            f"• Енергія: <b>+15%</b> ✨"
        )

        if date_count == 10:
            res_text += "\n\n🎉 <b>ОГО! Тепер ви офіційно ПАРА!</b> ❤️"
        elif date_count == 50:
            res_text += "\n\n🎊 <b>НЕЙМОВІРНО! Ви ПОВІНЧАЛИСЯ!</b> 💍🔔"

        await callback.message.edit_text(res_text, parse_mode="HTML")
        
        try:
            await callback.bot.send_message(partner_id, res_text, parse_mode="HTML")
        except:
            pass

    finally:
        await conn.close()