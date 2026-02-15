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
