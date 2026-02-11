import json
from aiogram import Router, F, types
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

def load_story():
    try:
        with open('start_narrative.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {str(node['id']): node for node in data['nodes']}
    except Exception:
        return {}

STORY_NODES = load_story()

async def render_story_node(message: types.Message, node_id: str):
    node = STORY_NODES.get(str(node_id))
    if not node: return

    builder = InlineKeyboardBuilder()
    
    if "options" in node:
        for opt in node["options"]:
            builder.button(text=opt["text"], callback_data=f"story_{opt['next_id']}")
    elif node.get("status") in ["dead", "next_level"]:
        builder.button(text="✨✨✨✨✨", callback_data="finish_prologue")

    builder.adjust(1)
    
    try:
        await message.edit_text(node["text"], reply_markup=builder.as_markup())
    except Exception:
        await message.answer(node["text"], reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith('story_'))
async def process_story_step(callback: types.CallbackQuery):
    next_node_id = callback.data.split("_")[1]
    await render_story_node(callback.message, next_node_id)
    await callback.answer()