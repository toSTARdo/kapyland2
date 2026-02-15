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
        
        stats = meta.get("stats", {"atk": 0, "def": 0, "agi": 0, "luck": 0})
        
        text = (
            f"🧘 <b>Медитація капібари</b>\n\n"
            f"Тут ти можеш використати свою духовну енергію для самовдосконалення.\n\n"
            f"💠 Доступно Zen-очок: <b>{zen}</b>\n\n"
            f"⚔️ Атака (ATK): <b>{stats.get('atk', 0)}</b>\n"
            f"🛡️ Захист (DEF): <b>{stats.get('def', 0)}</b>\n"
            f"💨 Спритність (AGI): <b>{stats.get('agi', 0)}</b>\n"
            f"🍀 Удача (LUCK): <b>{stats.get('luck', 0)}</b>"
        )
        
        builder = InlineKeyboardBuilder()
        builder.button(text="⚔️ +1 Атака", callback_data="upgrade_stat:atk")
        builder.button(text="🛡️ +1 Захист", callback_data="upgrade_stat:def")
        builder.button(text="💨 +1 Спритність", callback_data="upgrade_stat:agi")
        builder.button(text="🍀 +1 Удача", callback_data="upgrade_stat:luck")
        builder.button(text="🔙 Назад", callback_data="profile_back") 
        builder.adjust(2, 2, 1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    finally:
        await conn.close()