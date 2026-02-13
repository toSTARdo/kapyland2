import json
import random
from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.postgres_db import get_db_connection

router = Router()

with open("data/quests_narrative.json", "r", encoding="utf-8") as f:
    DATA = json.load(f)
    QUEST_PLOTS = DATA["QUEST_PLOTS"]
    RUMOR_COMPONENTS = DATA["RUMOR_COMPONENTS"]

@router.message(F.text.contains("📜"))
async def cmd_quests_board(message: types.Message):
    intro = random.choice(RUMOR_COMPONENTS["intros"])
    hint = random.choice(RUMOR_COMPONENTS["hints"])
    mood = random.choice(RUMOR_COMPONENTS["mood"])
    
    available_quests = list(QUEST_PLOTS.keys())
    q_id = random.choice(available_quests)
    q_name = QUEST_PLOTS[q_id]['name']

    builder = InlineKeyboardBuilder()
    builder.button(text=f"✅ {q_name}", callback_data=f"q_start:{q_id}")
    builder.button(text="🗺 Купити карту (50 🍉)", callback_data="buy_treasure_map")
    builder.adjust(1)

    await message.answer(
        f"📌 <b>ДОШКА ОГОЛОШЕНЬ ТАВЕРНИ</b>\n"
        f"--------------------------------\n"
        f"<i>{intro}</i>\n\n"
        f"📜 «...{hint} {mood}»",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
@router.callback_query(F.data == "buy_treasure_map")
async def handle_buy_map(callback: types.CallbackQuery):
    uid = callback.from_user.id
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
        if not row: return
        
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        inventory = meta.get('inventory', {})
        food = inventory.get('food', {})
        current_slices = food.get('watermelon_slices', 0)

        if current_slices < 50:
            return await callback.answer(f"❌ Тобі бракує кавунів! (Є: {current_slices}/50)", show_alert=True)

        food['watermelon_slices'] = current_slices - 50
        map_num = random.randint(100, 999)
        coords = f"{random.randint(10, 200)},{random.randint(10, 200)}"
        meta.setdefault('discovered', []).append(coords)
        inventory.get('loot', {}).setdefault('treasure_maps', []).append({
            "id": f"#{map_num}", 
            "pos": coords
        })

        await conn.execute(
            "UPDATE capybaras SET meta = $1 WHERE owner_id = $2", 
            json.dumps(meta, ensure_ascii=False), uid
        )
        
        await callback.message.answer(
            f"🗺 <b>Обмін завершено!</b>\n"
            f"Ви віддали 50 🍉 за карту #{map_num}.\n"
            f"Координати: <code>{coords}</code>", 
            parse_mode="HTML"
        )
    finally: await conn.close()

 Gemini said

Here is the corrected and fully integrated code. I have fixed the callback data mismatch (q_start: vs accept_q:), ensured the pearl_of_ehwaz is properly saved via the flags system, and cleaned up the database logic.
Integrated handlers/quests.py
Python

import json
import random
from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.postgres_db import get_db_connection

router = Router()

with open("data/quests_narrative.json", "r", encoding="utf-8") as f:
    DATA = json.load(f)
    QUEST_PLOTS = DATA["QUEST_PLOTS"]
    RUMOR_COMPONENTS = DATA["RUMOR_COMPONENTS"]

@router.message(F.text.contains("📜"))
async def cmd_quests_board(message: types.Message):
    intro = random.choice(RUMOR_COMPONENTS["intros"])
    hint = random.choice(RUMOR_COMPONENTS["hints"])
    mood = random.choice(RUMOR_COMPONENTS["mood"])
    
    available_quests = list(QUEST_PLOTS.keys())
    q_id = random.choice(available_quests)
    q_name = QUEST_PLOTS[q_id]['name']

    builder = InlineKeyboardBuilder()
    # Fixed prefix to match the handler below
    builder.button(text=f"✅ {q_name}", callback_data=f"q_start:{q_id}")
    builder.button(text="🗺 Купити карту (50 🍉)", callback_data="buy_treasure_map")
    builder.adjust(1)

    await message.answer(
        f"📌 <b>ДОШКА ОГОЛОШЕНЬ ТАВЕРНИ</b>\n"
        f"--------------------------------\n"
        f"<i>{intro}</i>\n\n"
        f"📜 «...{hint} {mood}»",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "buy_treasure_map")
async def handle_buy_map(callback: types.CallbackQuery):
    uid = callback.from_user.id
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
        if not row: return
        
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        inventory = meta.get('inventory', {})
        food = inventory.get('food', {})
        current_slices = food.get('watermelon_slices', 0)

        if current_slices < 50:
            return await callback.answer(f"❌ Тобі бракує кавунів! (Є: {current_slices}/50)", show_alert=True)

        food['watermelon_slices'] = current_slices - 50
        map_num = random.randint(100, 999)
        coords = f"{random.randint(10, 200)},{random.randint(10, 200)}"
        meta.setdefault('discovered', []).append(coords)
        inventory.setdefault('loot', {}).setdefault('treasure_maps', []).append({
            "id": f"#{map_num}", 
            "pos": coords
        })

        await conn.execute(
            "UPDATE capybaras SET meta = $1 WHERE owner_id = $2", 
            json.dumps(meta, ensure_ascii=False), uid
        )
        
        await callback.message.answer(
            f"🗺 <b>Обмін завершено!</b>\n"
            f"Ви віддали 50 🍉 за карту #{map_num}.\n"
            f"Координати: <code>{coords}</code>", 
            parse_mode="HTML"
        )
    finally: await conn.close()

@router.callback_query(F.data.startswith("q_start:"))
async def handle_accept(callback: types.CallbackQuery):
    uid = callback.from_user.id
    q_id = callback.data.split(":")[1]
    
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT current_quest FROM capybaras WHERE owner_id = $1", uid)
        if row and row['current_quest']:
            return await callback.answer("❌ Ви вже у пригоді!", show_alert=True)
        
        state = {
            "id": q_id,
            "stage": "0",
            "loot": {"exp": 0, "watermelon_slices": 0, "key": 0, "chest": 0},
            "flags": []
        }
        
        await conn.execute("UPDATE capybaras SET current_quest = $1 WHERE owner_id = $2", json.dumps(state), uid)
        await render_quest_stage(callback, state)
    finally: await conn.close()

async def render_quest_stage(event, state):
    quest = QUEST_PLOTS[state['id']]
    stage = quest['stages'][str(state['stage'])]
    
    builder = InlineKeyboardBuilder()
    for i, opt in enumerate(stage['options']):
        builder.button(text=opt['text'], callback_data=f"q_step:{i}")
    builder.adjust(1)
    
    l = state['loot']
    loot_view = f"✨{l['exp']} 🍉{l['watermelon_slices']} 🗝{l['key']} 🗃{l['chest']}"

    text = (
        f"📖 <b>{quest['name']}</b>\n"
        f"--------------------------------\n"
        f"{stage['text']}\n\n"
        f"🎒 <b>Здобич:</b> {loot_view}"
    )

    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    else:
        await event.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.startswith("q_step:"))
async def handle_quest_step(callback: types.CallbackQuery):
    uid = callback.from_user.id
    opt_idx = int(callback.data.split(":")[1])
    
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT current_quest FROM capybaras WHERE owner_id = $1", uid)
        if not row or not row['current_quest']: return

        state = row['current_quest']
        quest = QUEST_PLOTS[state['id']]
        stage = quest['stages'][str(state['stage'])]
        option = stage['options'][opt_idx]

        if random.random() < option.get('risk', 0):
            await conn.execute("UPDATE capybaras SET current_quest = NULL WHERE owner_id = $1", uid)
            return await callback.message.edit_text(f"💀 <b>Провал</b>\n{quest['fail_text']}", parse_mode="HTML")

        if "reward" in option:
            for r in option['reward'].split(","):
                k, v = r.split(":")
                if k == "item": state['flags'].append(v)
                elif k in state['loot']: state['loot'][k] += int(v)

        if option.get("action") == "exit" or option.get("next") == "win":
            await apply_rewards(uid, state)
            await conn.execute("UPDATE capybaras SET current_quest = NULL WHERE owner_id = $1", uid)
            res = "🌟 <b>КВЕСТ УСПІШНО ЗАВЕРШЕНИЙ!</b>" if option.get("next") == "win" else "✅ <b>Ви повернулися.</b>"
            return await callback.message.edit_text(res, parse_mode="HTML")

        state['stage'] = str(option['next'])
        await conn.execute("UPDATE capybaras SET current_quest = $1 WHERE owner_id = $2", json.dumps(state), uid)
        await render_quest_stage(callback, state)
    finally: await conn.close()

async def apply_rewards(uid, state):
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
        meta = json.loads(row['meta'])
        loot = state['loot']
        flags = state.get('flags', [])
        
        inv = meta['inventory']
        
        inv['food']['watermelon_slices'] += loot['watermelon_slices']
        inv['loot']['key'] += loot['key']
        inv['loot']['chest'] += loot['chest']

        for item in flags:
            inv['loot'][item] = inv['loot'].get(item, 0) + 1

        await conn.execute(
            "UPDATE capybaras SET exp = exp + $1, meta = $2 WHERE owner_id = $3", 
            loot['exp'], json.dumps(meta, ensure_ascii=False), uid
        )
    finally: await conn.close()

async def start_branching_quest(event: types.Message | types.CallbackQuery, quest_id: str):
    uid = event.from_user.id
    quest = QUEST_PLOTS.get(quest_id)
    if not quest: return

    quest_state = {
        "id": quest_id,
        "stage": "0",
        "loot": {"exp": 0, "watermelon_slices": 0, "key": 0, "chest": 0}
    }

    conn = await get_db_connection()
    try:
        await conn.execute(
            "UPDATE capybaras SET current_quest = $1 WHERE owner_id = $2",
            json.dumps(quest_state), uid
        )
    finally: await conn.close()

    await render_quest_stage(event, quest_state)
