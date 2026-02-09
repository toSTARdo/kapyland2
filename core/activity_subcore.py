import asyncio, json
from aiogram import Router, types, html, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from core.combat_engine import CombatEngine
from core.models import Fighter
from database.postgres_db import get_user_inventory
from config import BASE_HITPOINTS

router = Router()

@router.message(F.text == "⚔️ Бій")
@router.message(Command("fight"))
async def cmd_fight(message: types.Message):
    user_name = message.from_user.first_name
    
    # 1. Підготовка
    battle_msg = await message.answer(f"🔍 <b>{user_name}</b> шукає суперника...", parse_mode="HTML")
    await asyncio.sleep(1)
    
    p1 = Fighter(name=user_name, weight=25.0, color="🟢")
    p2 = Fighter(name="Папуга Павло (Бот)", weight=5.0, color="🔴")
    
    await battle_msg.edit_text(
        f"🏴‍☠️ Суперника знайдено!\n"
        f"{p1.color} <b>{p1.name}</b> VS {p2.color} <b>{p2.name}</b>", 
        parse_mode="HTML"
    )
    await asyncio.sleep(1.5)

    round_num = 1
    while p1.hp > 0 and p2.hp > 0 and round_num <= 20:
        attacker, defender = (p1, p2) if round_num % 2 != 0 else (p2, p1)
        
        report, damage = CombatEngine.resolve_turn(attacker, defender)
        
        full_report = (
            f"🏟 <b>Раунд {round_num}</b>\n\n"
            f"{report}"
        )
        
        try:
            await battle_msg.edit_text(full_report, parse_mode="HTML")
        except Exception: 
            pass
            
        await asyncio.sleep(2)
        round_num += 1

    if p1.hp > p2.hp:
        res = f"🏆 <b>ПЕРЕМОГА!</b>\n{p1.name} обсмикав все пір'я!"
    elif p2.hp > p1.hp:
        res = f"💀 <b>ПОРАЗКА...</b>\n{p1.name} був закльований ботом."
    else:
        res = "🤝 <b>НІЧИЯ!</b> Обидва пірати втомилися і пішли їсти травичку."

    await message.answer(res, parse_mode="HTML")

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