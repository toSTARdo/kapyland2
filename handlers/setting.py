from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database.postgres_db import get_db_connection
from handlers.main_buttons import get_settings_kb, get_main_kb

router = Router()

class RenameStates(StatesGroup):
    waiting_for_new_name = State()

@router.message(F.text == "⚙️ Налаштування")
async def show_settings(message: types.Message):
    await message.answer(
        "⚙️ <b>Центр керування капібарою</b>\n\n"
        "• Змінюй макет меню для зручності\n"
        "• Дай своїй булочці нове ім'я",
        reply_markup=get_settings_kb(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "change_name_start")
async def rename_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(RenameStates.waiting_for_new_name)
    await callback.message.answer("📝 Введи нове ім'я для своєї капібари (до 30 символів):")
    await callback.answer()

@router.message(RenameStates.waiting_for_new_name)
async def rename_finish(message: types.Message, state: FSMContext):
    new_name = message.text.strip()
    
    if len(new_name) > 30:
        return await message.answer("❌ Надто довге ім'я! Спробуй коротше.")

    uid = message.from_user.id
    conn = await get_db_connection()
    try:
        await conn.execute(
            "UPDATE capybaras SET name = $1 WHERE owner_id = $2", 
            new_name, uid
        )
    finally:
        await conn.close()

    await state.clear()
    await message.answer(f"✅ Готово! Тепер твою капібару звати <b>{new_name}</b>", parse_mode="HTML")

@router.callback_query(F.data.startswith("set_layout_"))
async def set_layout_callback(callback: types.CallbackQuery):
    layout_id = int(callback.data.split("_")[-1])
    uid = callback.from_user.id
    
    conn = await get_db_connection()
    try:
        await conn.execute("UPDATE users SET kb_layout = $1 WHERE tg_id = $2", layout_id, uid)
    finally:
        await conn.close()

    layouts = {0: "Стандартне", 1: "Компактне", 2: "Тільки іконки", 3:"Тамагочі-центрична", 4:"РПГ-центрична", 5:"Пригодницько-центрична", 6:"Кастомна"}
    
    await callback.answer(f"✅ Встановлено: {layouts[layout_id]}")
    await callback.message.answer(
        f"🎮 Макет змінено на: <b>{layouts[layout_id]}</b>",
        reply_markup=get_main_kb(layout_type=layout_id),
        parse_mode="HTML"
    )