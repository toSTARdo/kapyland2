import json
import random
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.postgres_db import get_db_connection

router = Router()

with open("data/quests_narratives.json", "r", encoding="utf-8") as f:
    DATA = json.load(f)
    QUEST_PLOTS = DATA["QUEST_PLOTS"]
    RUMOR_COMPONENTS = DATA["RUMOR_COMPONENTS"]

@router.message(F.text.contains("📜") | Command("quests"))
async def cmd_quests_board(message: types.Message):
    intro = random.choice(RUMOR_COMPONENTS["intros"])
    hint = random.choice(RUMOR_COMPONENTS["hints"])
    mood = random.choice(RUMOR_COMPONENTS["mood"])

    board_text = (
        "📌 <b>ДОШКА ОГОЛОШЕНЬ ТАВЕРНИ</b>\n"
        "--------------------------------\n"
        f"<i>{intro}</i>\n\n"
        f"📜 «...{hint} {mood}»\n\n"
        "🧭 <b>Завдання:</b> Орієнтуйся за символами на карті. Якщо знайдеш потрібне місце — пригода почнеться автоматично."
    )
    await message.answer(board_text, parse_mode="HTML")

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

async def render_quest_stage(event, state):
    quest = QUEST_PLOTS[state['id']]
    stage = quest['stages'][str(state['stage'])]
    
    builder = InlineKeyboardBuilder()
    for i, opt in enumerate(stage['options']):
        builder.button(text=opt['text'], callback_data=f"q_step:{i}")
    builder.adjust(1)
    
    loot_text = ""
    icons = {"exp": "✨", "watermelon_slices": "🍉", "key": "🗝️", "chest": "🗃"}
    for k, v in state['loot'].items():
        if v > 0: loot_text += f"{icons.get(k, '')}{v} "

    text = (
        f"<b>{quest['name']}</b>\n"
        f"--------------------------------\n"
        f"{stage['text']}\n\n"
        f"🎒 <b>Торба:</b> {loot_text if loot_text else 'ніц тут немає'}"
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
        if not row or not row['current_quest']:
            return await callback.answer("Мольфар каже, що цей час минув.")

        state = json.loads(row['current_quest'])
        quest = QUEST_PLOTS[state['id']]
        current_stage = quest['stages'][str(state['stage'])]
        option = current_stage['options'][opt_idx]

        if random.random() < option.get('risk', 0):
            await conn.execute("UPDATE capybaras SET current_quest = NULL WHERE owner_id = $1", uid)
            return await callback.message.edit_text(f"💀 <b>УПС!</b>\n{quest['fail_text']}", parse_mode="HTML")

        if "reward" in option:
            for r in option['reward'].split(","):
                key, val = r.split(":")
                if key in state['loot']:
                    state['loot'][key] += int(val)
                elif key == "item": # Спеціальна обробка артефактів
                    state['loot'][val] = state['loot'].get(val, 0) + 1

        if option.get("action") == "exit" or option.get("next") == "win":
            await apply_quest_rewards(uid, state['loot'])
            await conn.execute("UPDATE capybaras SET current_quest = NULL WHERE owner_id = $1", uid)
            
            final_msg = "🌟 <b>ВИ СТАЛИ ЛЕГЕНДОЮ ГІР!</b>" if option.get("next") == "win" else "✅ <b>Ви повернулися до колиби живим!</b>"
            return await callback.message.edit_text(f"{final_msg}\nЗдобич додана до сховку.", parse_mode="HTML")

        state['stage'] = str(option['next'])
        await conn.execute("UPDATE capybaras SET current_quest = $1 WHERE owner_id = $2", json.dumps(state), uid)
        await render_quest_stage(callback, state)

    finally: await conn.close()

async def apply_quest_rewards(uid, loot):
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
        meta = json.loads(row['meta'])
        
        meta['exp'] = meta.get('exp', 0) + loot.pop('exp', 0)
        
        inv = meta.setdefault('inventory', {})
        for item, count in loot.items():
            inv[item] = inv.get(item, 0) + count

        await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(meta, ensure_ascii=False), uid)
    finally: await conn.close()