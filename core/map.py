import json
from aiogram import types, F, Router
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.postgres_db import get_db_connection # Додай свій імпорт БД

from config import FULL_MAP, PLAYER_ICON, SHIP_ICON

router = Router()

MAP_HEIGHT = len(FULL_MAP)
MAP_WIDTH = len(FULL_MAP[0])
WATER_TILES = {"~", "༄", "꩜", "~~"}

def get_stamina_icons(stamina):
    if stamina > 66: return "⚡⚡⚡"
    if stamina > 33: return "⚡⚡"
    if stamina > 0: return "⚡"
    return "🪫"

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
        rows.append(f"║{''.join(display_row)}║")
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
    builder.row(types.InlineKeyboardButton(text="😴 Залягти в сплячку (2 год)", callback_data="sleep_start"))
    return builder.as_markup()

@router.message(F.text.startswith("🗺️"))
async def cmd_map(message: types.Message):
    uid = message.from_user.id
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
        meta = json.loads(row['meta']) if row else {}
        px = meta.get("x", 76)
        py = meta.get("y", 140)
        stamina = meta.get("stamina", 100)
        mode = meta.get("mode", "capy")
    finally: await conn.close()

    st_icons = get_stamina_icons(stamina)
    biome = get_biome_name(py, MAP_HEIGHT)
    map_display = render_pov(px, py, mode)
    
    text = (f"📍 <b>Карта ({px}, {py})</b> | {st_icons}\n"
            f"🧭 Біом: {biome}\n"
            f"🔋 Енергія: {stamina}/100\n\n"
            f"{map_display}")
    
    await message.answer(text, reply_markup=get_map_keyboard(px, py, mode), parse_mode="HTML")

@router.callback_query(F.data.startswith("mv:"))
async def handle_move(callback: types.CallbackQuery):
    _, direction, x, y, mode = callback.data.split(":")
    x, y, uid = int(x), int(y), callback.from_user.id
    
    nx, ny = x, y
    if direction == "up": ny -= 1
    elif direction == "down": ny += 1
    elif direction == "left": nx -= 1
    elif direction == "right": nx += 1

    if not (0 <= ny < MAP_HEIGHT and 0 <= nx < MAP_WIDTH):
        await callback.answer("Край світу! ⛔", show_alert=True)
        return

    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
        meta = json.loads(row['meta'])
        stamina = meta.get("energy", 100)

        if stamina < 1:
            await callback.answer("🪫 Енергія на нулі! Твоя капібара ледь переставляє лапки. Треба поспати. 😴", show_alert=True)
            return

        target_tile = FULL_MAP[ny][nx]
        new_mode = mode

        if mode == "ship":
            if target_tile in WATER_TILES: x, y = nx, ny
            else: x, y, new_mode = nx, ny, "capy"; await callback.answer(f"Висадка! {PLAYER_ICON}")
        else:
            if target_tile not in WATER_TILES: x, y = nx, ny
            else: x, y, new_mode = nx, ny, "ship"; await callback.answer("На борт! ⚓")

        new_stamina = stamina - 1
        meta.update({"x": x, "y": y, "stamina": new_stamina, "mode": new_mode})
        await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(meta), uid)

    finally: await conn.close()

    st_icons = get_stamina_icons(new_stamina)
    biome = get_biome_name(y, MAP_HEIGHT)
    map_display = render_pov(x, y, new_mode)
    
    text = (f"📍 <b>Карта ({x}, {y})</b> | {st_icons}\n"
            f"🧭 Біом: {biome}\n"
            f"🔋 Енергія: {new_stamina}/100\n\n"
            f"{map_display}")

    try:
        await callback.message.edit_text(text, reply_markup=get_map_keyboard(x, y, new_mode), parse_mode="HTML")
    except: await callback.answer()