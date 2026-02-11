import json
import logging
from aiogram import Router, F, types
from aiogram.utils.keyboard import InlineKeyboardBuilder

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
    
    if not node:
        logging.warning(f"⚠️ Node {node_id} не знайдено!")
        return

    builder = InlineKeyboardBuilder()
    
    if "options" in node:
        for opt in node["options"]:
            builder.button(text=opt["text"], callback_data=f"story_{opt['next_id']}")
    
    elif node.get("status") in ["dead", "win"]:
        builder.button(text="✨ Переродитися на Мофу", callback_data="finish_prologue")

    builder.adjust(1)
    
    try:
        await message.edit_text(node["text"], reply_markup=builder.as_markup())
    except Exception:
        await message.answer(node["text"], reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith('story_'))
async def process_story_step(callback: types.CallbackQuery):
    next_node_id = callback.data.replace("story_", "")
    
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except:
        pass

    await render_story_node(callback.message, next_node_id)
    await callback.answer()