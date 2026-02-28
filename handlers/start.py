import json
import logging
from aiogram import Router, F, types, html
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.postgres_db import get_db_connection

router = Router()

def load_story():
    try:
        with open('data/start_narrative_tree.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            nodes = {str(node['id']): node for node in data['nodes']}
            logging.info(f"✅ Story Engine: Завантажено {len(nodes)} вузлів сюжету.")
            return nodes
    except Exception as e:
        logging.error(f"❌ Story Engine Error: Не вдалося завантажити JSON: {e}")
        return {}

STORY_NODES = load_story()

async def render_story_node(message: types.Message, node_id: str):
    node = STORY_NODES.get(str(node_id))
    if not node: return

    builder = InlineKeyboardBuilder()
    display_text = node["text"]
    
    if node.get("status") in ["dead", "win"]:
        title = node.get("title", "Невідома доля")
        display_text += f"\n\n🏆 Отримано нову зав'язку: <b>{title}</b>"
        display_text += (
            f"\n\n✨ {html.bold('Богиня Капібар зʼявляється перед тобою і промовляє через свої розкішні локони:')}\n"
            f"«Твоє життя у цьому світі завершене, але на планеті Мофу ти можеш стати ким завгодно. "
            f"Який дар ти візьмеш із собою?»"
        )
        
        builder.button(text="⚔️ Сила", callback_data="godgift_atk")
        builder.button(text="💨 Спритність", callback_data="godgift_agi")
        builder.button(text="🛡 Захист", callback_data="godgift_def")
        builder.button(text="🍀 Удача", callback_data="godgift_luck")
    
    elif "options" in node:
        for opt in node["options"]:
            builder.button(text=opt["text"], callback_data=f"story_{opt['next_id']}")

    builder.adjust(1 if "options" in node else 2)
    
    try:
        await message.edit_text(display_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception:
        await message.answer(display_text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.startswith("godgift_"))
async def handle_goddess_gift(callback: types.CallbackQuery):
    stat_map = {
        "godgift_atk": "atk",
        "godgift_agi": "agi",
        "godgift_def": "def",
        "godgift_luck": "luck"
    }
    chosen_col = stat_map.get(callback.data)
    if not chosen_col: return
    
    uid = callback.from_user.id
    conn = await get_db_connection()
    
    try:
        await conn.execute(f"""
            UPDATE capybaras 
            SET {chosen_col} = {chosen_col} + 1 
            WHERE owner_id = $1
        """, uid)
    finally:
        await conn.close()

    gift_names = {"atk": "Силу", "agi": "Спритність", "def": "Захист", "luck": "Удачу"}
    
    new_text = (
        f"✨ Богиня посміхнулася: «Ти обрав {html.bold(gift_names[chosen_col])}. "
        f"Тепер я назад спати в хмарках...»"
    )
    
    confirm_kb = InlineKeyboardBuilder()
    confirm_kb.button(text="✨ Переродитися на землях Мофу", callback_data="finish_prologue")
    
    await callback.message.edit_text(new_text, reply_markup=confirm_kb.as_markup(), parse_mode="HTML")
    await callback.answer(f"Ви отримали +1 до {chosen_col}!")

@router.callback_query(F.data.startswith('story_'))
async def process_story_step(callback: types.CallbackQuery):
    next_node_id = callback.data.replace("story_", "")
    await render_story_node(callback.message, next_node_id)
    await callback.answer()