import asyncio, json
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from core.capybara_mechanics import get_user_inventory
from database.postgres_db import get_db_connection

router = Router()

@router.callback_query(F.data == "zen_upgrade")
async def meditation_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT zen, meta FROM capybaras WHERE owner_id = $1", user_id)
        if not row: return
        
        zen = row['zen'] or 0
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        
        stats = meta.get("stats", {"attack": 0, "defense": 0, "agility": 0, "luck": 0})
        
        text = (
            f"🧘 <b>Медитація капібари</b>\n\n"
            f"Тут ти можеш використати свою духовну енергію для самовдосконалення.\n\n"
            f"💠 Доступно капі-дзен очок: <b>{zen}</b>\n\n"
            f"⚔️ Атака (ATK): <b>{stats.get('attack', 0)}</b>\n"
            f"🛡️ Захист (DEF): <b>{stats.get('defense', 0)}</b>\n"
            f"💨 Спритність (AGI): <b>{stats.get('agility', 0)}</b>\n"
            f"🍀 Удача (LCK): <b>{stats.get('luck', 0)}</b>"
            f"⚡ Витривалість (END): <b>{stats.get('endurance', 0)}</b>"
        )
        
        builder = InlineKeyboardBuilder()
        builder.button(text="⚔️ +1 Атака", callback_data="upgrade_stat:attack")
        builder.button(text="🛡️ +1 Захист", callback_data="upgrade_stat:defense")
        builder.button(text="💨 +1 Спритність", callback_data="upgrade_stat:agility")
        builder.button(text="🍀 +1 Удача", callback_data="upgrade_stat:luck")
        builder.button(text="⚡ +1 Витривалість", callback_data="upgrade_stat:endurance")
        builder.button(text="🔙 Назад", callback_data="profile_back") 
        builder.adjust(2, 2, 1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    finally:
        await conn.close()

@router.callback_query(F.data.startswith("upgrade_stat:"))
async def process_stat_upgrade(callback: types.CallbackQuery):
    stat_to_boost = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT zen, meta FROM capybaras WHERE owner_id = $1", user_id)
        if not row or (row['zen'] or 0) < 1:
            return await callback.answer("Твоя чакра порожня... (Треба хоча б 1 капі-дзен)", show_alert=True)

        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        
        if "stats" not in meta:
            meta["stats"] = {"attack": 0, "defense": 0, "agility": 0, "luck": 0, "endurance": 0}
        
        meta["stats"][stat_to_boost] = meta["stats"].get(stat_to_boost, 0) + 1
        
        await conn.execute("""
            UPDATE capybaras 
            SET zen = zen - 1, meta = $1 
            WHERE owner_id = $2
        """, json.dumps(meta, ensure_ascii=False), user_id)
        
        await callback.answer(f"✨ Характеристика {stat_to_boost.upper()} покращена!")
        
        await meditation_menu(callback)
        
    finally:
        await conn.close()