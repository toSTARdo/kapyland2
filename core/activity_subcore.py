import asyncio
from aiogram import Router, types, html
from aiogram.filters import Command
from core.combat_engine import CombatEngine
from config import BASE_HITPOINTS

router = Router()

@router.message(Command("fight"))
async def cmd_fight(message: types.Message):
    uid = message.from_user.id
    user_name = message.from_user.first_name
    
    battle_msg = await message.answer(f"🔍 <b>{user_name}</b> шукає суперника...")
    await asyncio.sleep(1)
    
    p1 = {"name": user_name, "hp": BASE_HITPOINTS}
    p2 = {"name": "🦜 Папуга Павло (Бот)", "hp": BASE_HITPOINTS}
    
    await battle_msg.edit_text(f"🏴‍☠️ Суперника знайдено! <b>{p1['name']}</b> VS <b>{p2['name']}</b>")
    await asyncio.sleep(1.5)

    round_num = 1
    while p1['hp'] > 0 and p2['hp'] > 0 and round_num <= 10:
        attacker, defender = (p1, p2) if round_num % 2 != 0 else (p2, p1)
        
        action_text, damage = CombatEngine.resolve_turn(attacker['name'], defender['name'])
        defender['hp'] -= damage
        if defender['hp'] < 0: defender['hp'] = 0

        report = (
            f"🏟 <b>Раунд {round_num}</b>\n\n"
            f"{action_text}\n\n"
            f"🟢 <b>{p1['name']}</b>: {p1['hp']} HP\n"
            f"🔴 <b>{p2['name']}</b>: {p2['hp']} HP"
        )
        
        await battle_msg.edit_text(report, parse_mode="HTML")
        await asyncio.sleep(2)
        round_num += 1

    # 3. Фінал
    if p1['hp'] > p2['hp']:
        res = f"🏆 <b>ПЕРЕМОГА!</b>\n{p1['name']} обсмикав все пір'я!"
    else:
        res = f"💀 <b>ПОРАЗКА...</b>\n{p1['name']} був закльований."

    await message.answer(res, parse_mode="HTML")