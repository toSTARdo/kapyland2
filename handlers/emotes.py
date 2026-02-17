import json
import random
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.postgres_db import get_db_connection

router = Router()

class SettingsStates(StatesGroup):
    waiting_for_victory_gif = State()

def get_finish_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✅ Завершити", callback_data="finish_media_setup"))
    builder.row(types.InlineKeyboardButton(text="🗑️ Очистити все", callback_data="clear_victory_media"))
    builder.row(types.InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_settings"))
    return builder.as_markup()

@router.callback_query(F.data == "setup_victory_gif", StateFilter(None, SettingsStates.waiting_for_victory_gif))
async def start_gif_setting(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(SettingsStates.waiting_for_victory_gif)
    await callback.message.edit_text(
        "🎬 <b>Налаштування переможних реакцій</b>\n\n"
        "Кидай сюди GIF, стікери або фото (до 5 штук).\n"
        "Вони будуть з'являтися після твоїх перемог.",
        reply_markup=get_finish_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(SettingsStates.waiting_for_victory_gif, F.animation | F.photo | F.sticker)
async def process_victory_media_bulk(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    
    # Визначаємо медіа
    if message.animation:
        new_item = {"id": message.animation.file_id, "type": "gif"}
    elif message.photo:
        new_item = {"id": message.photo[-1].file_id, "type": "photo"}
    elif message.sticker:
        new_item = {"id": message.sticker.file_id, "type": "sticker"}

    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
        meta = row['meta'] if row and row['meta'] else {}
        if isinstance(meta, str): meta = json.loads(meta)
        
        victory_media = meta.get("victory_media", [])
        victory_media.append(new_item)
        victory_media = victory_media[-5:] 
        
        meta["victory_media"] = victory_media
        
        await conn.execute(
            "UPDATE capybaras SET meta = $1 WHERE owner_id = $2",
            json.dumps(meta, ensure_ascii=False), uid
        )
        
        await message.answer(
            f"📥 Додано! ({len(victory_media)}/5)\n"
            "Можеш кинути ще або натисни кнопку нижче.",
            reply_markup=get_finish_keyboard()
        )
    finally:
        await conn.close()

@router.callback_query(F.data == "clear_victory_media", SettingsStates.waiting_for_victory_gif)
async def clear_victory_media(callback: types.CallbackQuery):
    uid = callback.from_user.id
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
        meta = row['meta'] if row and row['meta'] else {}
        if isinstance(meta, str): meta = json.loads(meta)
        
        meta["victory_media"] = []
        
        await conn.execute(
            "UPDATE capybaras SET meta = $1 WHERE owner_id = $2",
            json.dumps(meta, ensure_ascii=False), uid
        )
        
        await callback.message.edit_text(
            "🗑️ <b>Список очищено!</b>",
            reply_markup=get_finish_keyboard(),
            parse_mode="HTML"
        )
    finally:
        await conn.close()
    await callback.answer("Очищено")

@router.callback_query(F.data == "finish_media_setup", SettingsStates.waiting_for_victory_gif)
async def finish_media(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("✅ <b>Налаштування збережено!</b>", parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "cancel_settings", SettingsStates.waiting_for_victory_gif)
async def cancel_media(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ <b>Зміни скасовано.</b>", parse_mode="HTML")
    await callback.answer()

async def send_victory_celebration(message: types.Message, user_id: int):
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", user_id)
        if not row or not row['meta']: return
        
        meta = row['meta']
        if isinstance(meta, str): meta = json.loads(meta)
        
        media_list = meta.get("victory_media", [])
        if not media_list: return
        
        item = random.choice(media_list)
        f_id, m_type = item["id"], item["type"]

        if m_type == "gif":
            await message.answer_animation(f_id, caption="✨ Твоя перемога!")
        elif m_type == "photo":
            await message.answer_photo(f_id, caption="✨ Твоя перемога!")
        elif m_type == "sticker":
            await message.answer_sticker(f_id)
            
    except Exception as e:
        print(f"Celebration Error: {e}")
    finally:
        await conn.close()