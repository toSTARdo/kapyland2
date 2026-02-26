import json
import datetime
import random
import asyncio
from aiogram import types, F, Router
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.postgres_db import get_db_connection
from handlers.quests import start_branching_quest
from utils.helpers import consume_stamina
from config import FULL_MAP, PLAYER_ICON, SHIP_ICON

router = Router()

PLANTS_LOOT = {
    "herbs": [
        {"id": "mint", "name": "🌿 М'ята", "chance": 40},
        {"id": "thyme", "name": "🌱 Чебрець", "chance": 30},
        {"id": "rosemary", "name": "🌿 Розмарин", "chance": 10}
    ],
    "flowers": [
        {"id": "chamomile", "name": "🌼 Ромашка", "chance": 35},
        {"id": "lavender", "name": "🪻 Лаванда", "chance": 25},
        {"id": "tulip", "name": "🌷 Тюльпан", "chance": 15},
        {"id": "lotus", "name": "🪷 Лотос", "chance": 5} 
    ]
}

MUSHROOMS_LOOT = [
    {"id": "fly_agaric", "name": "🍄 Мухомор", "chance": 10},
    {"id": "mushroom", "name": "🍄‍🟫 Гриб", "chance": 90},
]

COORD_QUESTS = {
    "15,129": "carpathian_pearl",
    "75,145": "carpathian_pearl"
}

MAP_HEIGHT = len(FULL_MAP)
MAP_WIDTH = len(FULL_MAP[0])
WATER_TILES = {"~", "༄", "꩜"}
FOREST_TILES = {"𖠰", "𖣂"}
FOG_ICON = "░"

def get_random_plant():
    all_plants = PLANTS_LOOT["herbs"] + PLANTS_LOOT["flowers"]
    
    weights = [p['chance'] for p in all_plants]
    selected = random.choices(all_plants, weights=weights, k=1)[0]
    
    return selected

def get_random_mushroom():
    weights = [m['chance'] for m in MUSHROOMS_LOOT]
    return random.choices(MUSHROOMS_LOOT, weights=weights, k=1)[0]

def check_daily_limit(meta, action_key):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    if meta.get("cooldowns", {}).get(action_key) == today:
        return False, today
    if "cooldowns" not in meta:
        meta["cooldowns"] = {}
    meta["cooldowns"][action_key] = today
    return True, today

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

def render_pov(px, py, discovered_list, mode="ship", treasure_maps=None, flowers=None, trees=None):
    win_w, win_h = 15, 8
    icon = SHIP_ICON if mode == "ship" else PLAYER_ICON
    start_x = max(0, min(MAP_WIDTH - win_w, px - win_w // 2))
    start_y = max(0, min(MAP_HEIGHT - win_h, py - win_h // 2))
    
    discovered_set = set(discovered_list)
    treasure_coords = {m['pos'] for m in treasure_maps} if treasure_maps else set()
    flower_coords = flowers if flowers else {}
    tree_coords = trees if trees else {}
    
    rows = ["═" * (win_w)]
    for y in range(start_y, start_y + win_h):
        display_row = []
        for x in range(start_x, start_x + win_w):
            c_str = f"{x},{y}"
            
            if x == px and y == py:
                display_row.append(icon)
            elif c_str in flower_coords and c_str in discovered_set:
                display_row.append("✽")
            elif c_str in tree_coords and c_str in discovered_set:
                display_row.append(tree_coords[c_str])
            elif c_str in treasure_coords and c_str in discovered_set:
                display_row.append("X")
            elif c_str in discovered_set:
                tile = FULL_MAP[y][x]
                if tile in FOREST_TILES and c_str not in tree_coords:
                    display_row.append("𖧧")
                else:
                    display_row.append(tile)
            else:
                display_row.append(FOG_ICON)
        rows.append(f"{''.join(display_row)}")
    rows.append("═" * (win_w))
    return "\n".join(rows)

def get_map_keyboard(px, py, mode, meta):
    builder = InlineKeyboardBuilder()
    
    personal_trees = meta.get("trees", {})
    if f"{px},{py}" in personal_trees:
        builder.row(types.InlineKeyboardButton(
            text="🪓 Зрубати дерево (-5 ⚡)", 
            callback_data=f"chop:{px}:{py}")
        )

    builder.row(types.InlineKeyboardButton(text="⬆️", callback_data=f"mv:up:{px}:{py}:{mode}"))
    builder.row(
        types.InlineKeyboardButton(text="⬅️", callback_data=f"mv:left:{px}:{py}:{mode}"),
        types.InlineKeyboardButton(text="⬇️", callback_data=f"mv:down:{px}:{py}:{mode}"),
        types.InlineKeyboardButton(text="➡️", callback_data=f"mv:right:{px}:{py}:{mode}")
    )
    builder.row(types.InlineKeyboardButton(text="🔭 Огляд розвіданих зон", callback_data=f"view:{px}:{py}"))
    builder.row(types.InlineKeyboardButton(text="🔙 Назад", callback_data="open_adventure"))
    return builder.as_markup()

@router.callback_query(F.data == "open_map")
async def map_mediator(callback: types.CallbackQuery):
    is_group = callback.message.chat.type in ["group", "supergroup"]
    if not is_group:
        return await render_map(callback)
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🗺️ Відкрити в особистих", url=f"https://t.me/{(await callback.bot.get_me()).username}?start=map"))
    builder.row(types.InlineKeyboardButton(text="⚓ Відкрити тут", callback_data="force_map_group"))
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="open_adventure"))
    text = "⚠️ <b>Попередження про трафік</b>\n━━━━━━━━━━━━━━━\nМапа — це важкий об'єкт. Рекомендуємо грати в особистих повідомленнях бота."
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data == "force_map_group")
async def handle_force_map(callback: types.CallbackQuery):
    await render_map(callback)

async def render_map(callback: types.CallbackQuery):
    uid = callback.from_user.id
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
        meta = json.loads(row['meta']) if row else {}
        can_refresh, _ = check_daily_limit(meta, "flowers_refresh")
        if can_refresh:
            new_flowers = {}
            for _ in range(120):
                if len(new_flowers) >= 100: break
                rx, ry = random.randint(0, MAP_WIDTH-1), random.randint(0, MAP_HEIGHT-1)
                tile = FULL_MAP[ry][rx]
                
                if tile not in WATER_TILES:
                    is_forest = tile in FOREST_TILES
                    choices = ["✽", "𓋼"]
                    weights = [20, 80] if is_forest else [80, 20]
                    
                    new_flowers[f"{rx},{ry}"] = random.choices(choices, weights=weights, k=1)[0]
            meta["flowers"] = new_flowers
            new_trees = {}
            for ry in range(MAP_HEIGHT):
                for rx in range(MAP_WIDTH):
                    if FULL_MAP[ry][rx] in FOREST_TILES:
                        new_trees[f"{rx},{ry}"] = FULL_MAP[ry][rx]
            meta["trees"] = new_trees
            
            await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(meta, ensure_ascii=False), uid)
        px, py = meta.get("x", 77), meta.get("y", 144)
        stamina, mode = meta.get("stamina", 100), meta.get("mode", "capy")
        discovered = meta.get("discovered", [f"{px},{py}"])
        map_display = render_pov(px, py, discovered, mode, flowers=meta.get("flowers"), trees=meta.get("trees"))
        text = f"📍 <b>Карта ({px}, {py})</b> | {get_stamina_icons(stamina)}\n🧭 Біом: {get_biome_name(py, MAP_HEIGHT)}\n🔋 Енергія: {stamina}/100\n\n{map_display}"
        await callback.message.edit_text(text, reply_markup = get_map_keyboard(px, py, mode, meta), parse_mode="HTML")
    finally: await conn.close()

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
        return await callback.answer("Край світу! ⛔", show_alert=True)
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta, zen FROM capybaras WHERE owner_id = $1", uid)
        meta = json.loads(row['meta'])
        stamina, zen = meta.get("stamina", 100), row['zen']
        if stamina < 1: return await callback.answer("Енергія на нулі!", show_alert=True)
        target_tile, new_mode = FULL_MAP[ny][nx], mode
        if mode == "ship":
            if target_tile in WATER_TILES: x, y = nx, ny
            else: x, y, new_mode = nx, ny, "capy"; await callback.answer(f"Висадка! {PLAYER_ICON}")
        else:
            if target_tile not in WATER_TILES: x, y = nx, ny
            else: x, y, new_mode = nx, ny, "ship"; await callback.answer("На борт! ⚓")
        coord_key = f"{x},{y}"
        can_refresh, _ = check_daily_limit(meta, "flowers_refresh")
        if can_refresh:
            nf = {}
            for _ in range(200):
                if len(nf) >= 80: break
                rx, ry = random.randint(0, MAP_WIDTH-1), random.randint(0, MAP_HEIGHT-1)
                if FULL_MAP[ry][rx] not in WATER_TILES: nf[f"{rx},{ry}"] = random.choice(["🌸", "🌷", "🌻", "🌺", "🪻༘"])
            meta["flowers"] = nf
        personal_flowers = meta.get("flowers", {})
        if coord_key in personal_flowers:
            f_icon = personal_flowers.pop(coord_key)
            
            if f_icon == "𓋼":
                item = get_random_mushroom()
            else:
                item = get_random_plant()

            item_id, item_name = item['id'], item['name']
            
            if await consume_stamina(conn, uid, "move"):
                inv_mats = meta.setdefault("inventory", {}).setdefault("materials", {})
                inv_mats[item_id] = inv_mats.get(item_id, 0) + 1
                
                await callback.answer(f"✨ Знайдено: {item_name}!", show_alert=False)
        loot = meta.setdefault("inventory", {}).setdefault("loot", {})
        tmaps = loot.get("treasure_maps", [])
        found_map = next((m for m in tmaps if m["pos"] == coord_key), None)
        if found_map:
            loot["treasure_maps"] = [m for m in tmaps if m["pos"] != coord_key]
            loot["chest"] = loot.get("chest", 0) + 1
            await callback.answer("🏴‍☠️ Скарб знайдено!", show_alert=True)
        if coord_key in COORD_QUESTS:
            curr_q = await conn.fetchrow("SELECT current_quest FROM capybaras WHERE owner_id = $1", uid)
            if not curr_q or not curr_q['current_quest']:
                meta.update({"x": x, "y": y, "stamina": stamina - 1, "mode": new_mode})
                await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(meta, ensure_ascii=False), uid)
                return await start_branching_quest(callback, COORD_QUESTS[coord_key])
        disc_set = set(meta.get("discovered", []))
        for dy in range(-1, 2):
            for dx in range(-2, 3):
                sx, sy = x + dx, y + dy
                if 0 <= sx < MAP_WIDTH and 0 <= sy < MAP_HEIGHT: disc_set.add(f"{sx},{sy}")
        new_disc = list(disc_set)
        if (len(new_disc) // 800) > (len(meta.get("discovered", [])) // 800): zen += 1
        new_stamina = stamina - 1
        meta.update({"x": x, "y": y, "stamina": new_stamina, "mode": new_mode, "discovered": new_disc})
        await conn.execute(
            "UPDATE capybaras SET meta = $1, zen = $2 WHERE owner_id = $3", 
            json.dumps(meta, ensure_ascii=False), zen, uid
        )

        map_display = render_pov(
            x, y, new_disc, new_mode, 
            treasure_maps=tmaps, 
            flowers=meta.get("flowers"), 
            trees=meta.get("trees")
        )
        
        text = (f"📍 <b>Карта ({x}, {y})</b> | {get_stamina_icons(new_stamina)}\n"
                f"🧭 Біом: {get_biome_name(y, MAP_HEIGHT)} | ✨ Дзен: {zen}\n"
                f"🔋 Енергія: {new_stamina}/100\n\n"
                f"{map_display}")

        await callback.message.edit_text(
            text, 
            reply_markup=get_map_keyboard(x, y, new_mode, meta),
            parse_mode="HTML"
        )
    finally: await conn.close()

@router.callback_query(F.data.startswith("chop:"))
async def handle_chop(callback: types.CallbackQuery):
    _, x, y = callback.data.split(":")
    x, y, uid = int(x), int(y), callback.from_user.id
    coord_key = f"{x},{y}"

    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
        meta = json.loads(row['meta'])
        stamina = meta.get("stamina", 100)

        if stamina < 5:
            return await callback.answer("❌ Недостатньо енергії (треба 5 ⚡)", show_alert=True)

        trees = meta.get("trees", {})
        if coord_key in trees:
            trees.pop(coord_key)
            
            inv = meta.setdefault("inventory", {})
            mats = inv.setdefault("materials", {})
            gain = 1
            mats["wood"] = mats.get("wood", 0) + gain
            
            meta["stamina"] = stamina - 5
            
            await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(meta, ensure_ascii=False), uid)
            await callback.answer(f"Отримано {gain} деревини!")
            
            await render_map(callback)
        else:
            await callback.answer("Тут уже немає що рубати...")
    finally: await conn.close()

def render_world_viewer(view_x, view_y, discovered_list):
    win_size = 15
    half = win_size // 2
    start_x = max(0, min(MAP_WIDTH - win_size, view_x - half))
    start_y = max(0, min(MAP_HEIGHT - win_size, view_y - half))
    
    discovered_set = set(discovered_list)
    rows = [f"🌐 <b>Огляд світу ({view_x}, {view_y})</b>", "═" * win_size]
    
    for y in range(start_y, start_y + win_size):
        line = []
        for x in range(start_x, start_x + win_size):
            c_str = f"{x},{y}"
            if c_str in discovered_set:
                line.append(FULL_MAP[y][x])
            else:
                line.append(FOG_ICON)
        rows.append("".join(line))
    
    rows.append("═" * win_size)
    return "\n".join(rows)

def get_viewer_keyboard(vx, vy):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="⏫", callback_data=f"view:{vx}:{vy-5}"))
    builder.row(
        types.InlineKeyboardButton(text="⏪", callback_data=f"view:{vx-5}:{vy}"),
        types.InlineKeyboardButton(text="🔄", callback_data=f"open_map"),
        types.InlineKeyboardButton(text="⏩", callback_data=f"view:{vx+5}:{vy}")
    )
    builder.row(types.InlineKeyboardButton(text="⏬", callback_data=f"view:{vx}:{vy+5}"))
    builder.row(types.InlineKeyboardButton(text="🔙 Закрити", callback_data="open_map"))
    return builder.as_markup()