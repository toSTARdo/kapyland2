from aiogram import Router, types, F
from database.postgres_db import get_db_connection
from handlers.main_buttons import get_settings_kb, get_main_kb

router = Router()

@router.message(F.text == "⚙️ Налаштування")
async def show_settings(message: types.Message):
    await message.answer(
        "⚙️ <b>Налаштування інтерфейсу</b>\n\n"
        "Тут ти можеш змінити вигляд головного меню. "
        "Компактний режим краще підходить для маленьких екранів.",
        reply_markup=get_settings_kb(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "toggle_layout")
async def toggle_layout_callback(callback: types.CallbackQuery):
    uid = callback.from_user.id
    conn = await get_db_connection()
    
    try:
        user = await conn.fetchrow("SELECT kb_layout FROM users WHERE tg_id = $1", uid)
        new_layout = 1 if user['kb_layout'] == 0 else 0
        
        await conn.execute(
            "UPDATE users SET kb_layout = $1 WHERE tg_id = $2", 
            new_layout, uid
        )
    finally:
        await conn.close()

    layout_name = "Компактне" if new_layout == 1 else "Стандартне"
    
    await callback.answer(f"✅ Встановлено {layout_name} меню!")
    
    await callback.message.answer(
        f"🎮 Твоє меню оновлено до: <b>{layout_name}</b>",
        reply_markup=get_main_kb(layout_type=new_layout),
        parse_mode="HTML"
    )