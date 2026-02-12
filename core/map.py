import json
from aiogram import types, F, Router
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import FULL_MAP, PLAYER_ICON, SHIP_ICON

router = Router()

MAP_HEIGHT = len(FULL_MAP)
MAP_WIDTH = len(FULL_MAP[0])
WATER_TILES = {"~", "༄", "꩜"}

def get_biome_name(py, map_height):
    progress = py / map_height
    if progress < 0.35: return "❄️ Зорефьорди Ехвазу"
    elif 0.35 <= progress < 0.65: return "🌊 Уроборострім"
    else: return "🏝️ Архіпелаг Джуа"

def render_pov(px, py, mode="ship"):
    win_w, win_h = 13, 7
    icon = SHIP_ICON if mode == "ship" else PLAYER_ICON
    
    start_x = max(0, min(MAP_WIDTH - win_w, px - win_w // 2))
    start_y = max(0, min(MAP_HEIGHT - win_h, py - win_h // 2))
    
    rows = ["<code>╔" + "═" * (win_w) + "╗"]
    
    for y in range(start_y, start_y + win_h):
        row_slice = FULL_MAP[y][start_x : start_x + win_w]
        display_row = list(row_slice)
        
        if y == py:
            rel_x = px - start_x
            if 0 <= rel_x < len(display_row):
                display_row[rel_x] = icon
        
        rows.append(f"{''.join(display_row)}")
    
    rows.append("╚" + "═" * (win_w) + "╝</code>")
    return "\n".join(rows)
    
def get_map_keyboard(px, py, mode):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="⬆️", callback_data=f"mv:up:{px}:{py}:{mode}"))
    builder.row(
        types.InlineKeyboardButton(text="⬅️", callback_data=f"mv:left:{px}:{py}:{mode}"),
        types.InlineKeyboardButton(text="⬇️", callback_data=f"mv:down:{px}:{py}:{mode}"),
        types.InlineKeyboardButton(text="➡️", callback_data=f"mv:right:{px}:{py}:{mode}")
    )
    return builder.as_markup()

@router.message(F.text.startswith("🗺️"))
async def cmd_map(message: types.Message):
    px, py = 76, 140 
    mode = "capy"
    
    biome = get_biome_name(py, MAP_HEIGHT)
    map_display = render_pov(px, py, mode)
    
    text = (f"📍 <b>Карта ({px}, {py})</b>\n"
            f"🧭 Біом: {biome}\n\n"
            f"{map_display}")
    
    await message.answer(text, reply_markup=get_map_keyboard(px, py, mode), parse_mode="HTML")

@router.callback_query(F.data.startswith("mv:"))
async def handle_move(callback: types.CallbackQuery):
    _, direction, x, y, mode = callback.data.split(":")
    x, y = int(x), int(y)
    
    nx, ny = x, y
    if direction == "up": ny -= 1
    elif direction == "down": ny += 1
    elif direction == "left": nx -= 1
    elif direction == "right": nx += 1

    if not (0 <= ny < MAP_HEIGHT and 0 <= nx < MAP_WIDTH):
        await callback.answer("Край світу! Далі лише безодня. ⛔", show_alert=True)
        return

    target_tile = FULL_MAP[ny][nx]
    new_mode = mode

    if mode == "ship":
        if target_tile in WATER_TILES:
            x, y = nx, ny
        else:
            x, y = nx, ny
            new_mode = "capy"
            await callback.answer(f"Висадка на берег! {PLAYER_ICON}")
    else:
        if target_tile not in WATER_TILES:
            x, y = nx, ny
        else:
            x, y = nx, ny
            new_mode = "ship"
            await callback.answer("Всі на борт! ⚓")

    biome = get_biome_name(y, MAP_HEIGHT)
    map_display = render_pov(x, y, new_mode)
    
    text = (f"📍 <b>Карта ({x}, {y})</b>\n"
            f"🧭 Біом: {biome}\n\n"
            f"{map_display}")

    try:
        await callback.message.edit_text(
            text, 
            reply_markup=get_map_keyboard(x, y, new_mode), 
            parse_mode="HTML"
        )
    except Exception:
        await callback.answer()