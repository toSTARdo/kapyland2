import asyncio, json, random
from aiogram import Router, types, html, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from core.capybara_mechanics import get_user_inventory
from database.postgres_db import get_db_connection
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from config import KANJI_DICT

class ShipCreation(StatesGroup):
    waiting_for_name = State()
    waiting_for_kanji = State()

router = Router()

@router.message(F.text.contains("⚓"))
@router.callback_query(F.data == "ship_main")
async def cmd_ship_menu(event: types.Message | types.CallbackQuery, state: FSMContext):
    await state.clear()
    uid = event.from_user.id
    message = event.message if isinstance(event, types.CallbackQuery) else event
    
    conn = await get_db_connection()
    try:
        ship = await conn.fetchrow("""
            SELECT s.*, c.name as capy_name 
            FROM capybaras c
            LEFT JOIN ships s ON c.ship_id = s.id
            WHERE c.owner_id = $1
        """, uid)
    finally:
        await conn.close()

    builder = InlineKeyboardBuilder()

    if not ship or ship['id'] is None:
        text = (
            "🌊 <b>Ти — вільний плавець</b>\n\n"
            "У тебе поки немає корабля. Ти можеш заснувати власний флот за 10 дерева."
        )
        builder.button(text="🔨 Збудувати корабель", callback_data="ship_create_init")
        builder.button(text="🔍 Пошук команди", callback_data="leaderboard:mass:0")
    else:
        engine_data = ship['engine'] if isinstance(ship['engine'], dict) else json.loads(ship['engine'] or '{}')
        engine_name = engine_data.get('name', 'Відсутній')
        ship_meta = ship['meta'] if isinstance(ship['meta'], dict) else json.loads(ship['meta'] or '{}')
        flag = ship_meta.get('flag', '🏴‍☠️')
        
        text = (
            f"🚢 <b>{flag} Корабель: «{ship['name']}»</b>\n"
            f"🎖 Рівень: {ship['lvl']}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🍉 Кавуни в трюмі: <b>{ship['gold']} шт.</b>\n"
            f"⚙️ Двигун: <b>{engine_name}</b>\n"
            f"👤 Роль: {'Капітан' if ship['captain_id'] == uid else 'Матрос'}\n"
            f"━━━━━━━━━━━━━━━"
        )
        builder.button(text="👥 Екіпаж", callback_data=f"ship_crew:{ship['id']}")
        builder.button(text="🍉 Скарбниця", callback_data="ship_treasury")
        builder.button(text="⚙️ Машинне відділення", callback_data="ship_engine")
        builder.button(text="🛠 Покращити", callback_data="ship_upgrade")
        
        if ship['captain_id'] == uid:
            builder.button(text="⚙️ Налаштування", callback_data="ship_settings")
        else:
            builder.button(text="🏃 Покинути борт", callback_data="ship_leave_confirm")

    builder.adjust(1)
    
    if isinstance(event, types.CallbackQuery):
        await message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data == "ship_treasury")
async def ship_watermelon_vault(callback: types.CallbackQuery):
    uid = callback.from_user.id
    conn = await get_db_connection()
    try:
        ship = await conn.fetchrow("""
            SELECT s.id, s.name, s.gold as watermelons 
            FROM ships s JOIN capybaras c ON s.id = c.ship_id 
            WHERE c.owner_id = $1
        """, uid)
        
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        user_melons = meta.get("inventory", {}).get("food", {}).get("Кавун", 0)

        text = (
            f"🍉 <b>Склад кавунів «{ship['name']}»</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📦 У трюмі: <b>{ship['watermelons']} шт.</b>\n"
            f"🎒 У тебе: <b>{user_melons} шт.</b>"
        )

        builder = InlineKeyboardBuilder()
        if user_melons > 0:
            builder.button(text="📥 Покласти 1 🍉", callback_data="ship_deposit:1")
            builder.button(text="📥 Покласти все", callback_data=f"ship_deposit:{user_melons}")
        
        builder.button(text="🔙 Назад", callback_data="ship_main")
        builder.adjust(1)
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    finally:
        await conn.close()

@router.callback_query(F.data.startswith("ship_deposit:"))
async def execute_melon_deposit(callback: types.CallbackQuery):
    amount = int(callback.data.split(":")[1])
    uid = callback.from_user.id
    conn = await get_db_connection()
    try:
        res = await conn.execute(f"""
            UPDATE capybaras SET meta = jsonb_set(meta, '{{inventory, food, Кавун}}', 
            ((meta->'inventory'->'food'->>'Кавун')::int - {amount})::text::jsonb)
            WHERE owner_id = $1 AND (meta->'inventory'->'food'->>'Кавун')::int >= $2
        """, uid, amount)

        if res == "UPDATE 0":
            return await callback.answer("❌ Недостатньо кавунів!")

        await conn.execute("""
            UPDATE ships SET gold = gold + $1 
            WHERE id = (SELECT ship_id FROM capybaras WHERE owner_id = $2)
        """, amount, uid)

        await callback.answer(f"🍉 Додано {amount} кавунів!")
        await ship_watermelon_vault(callback)
    finally:
        await conn.close()

@router.callback_query(F.data == "ship_engine")
async def ship_engine_room(callback: types.CallbackQuery):
    uid = callback.from_user.id
    conn = await get_db_connection()
    try:
        ship = await conn.fetchrow("""
            SELECT s.name, s.engine 
            FROM ships s JOIN capybaras c ON s.id = c.ship_id 
            WHERE c.owner_id = $1
        """, uid)
        
        engine = ship['engine'] if isinstance(ship['engine'], dict) else json.loads(ship['engine'] or '{}')

        if not engine:
            status_text = "❌ <b>Двигун відсутній</b>\nСлот порожній. Потрібен ???? предмет."
        else:
            status_text = (
                f"🚀 <b>Модель:</b> {engine.get('name', 'хом\'як в колесі')}\n"
                f"⚡️ <b>Потужність:</b> +{engine.get('power', 0)}\n"
                f"🛠 <b>Стан:</b> {engine.get('durability', 100)}%"
            )

        text = f"⚙️ <b>Машинне відділення «{ship['name']}»</b>\n━━━━━━━━━━━━━━━\n{status_text}"
        
        builder = InlineKeyboardBuilder()
        if not engine:
            builder.button(text="🔧 Встановити T-двигун", callback_data="ship_install_engine")
        else:
            builder.button(text="🔋 Ремонт", callback_data="ship_repair_engine")
            
        builder.button(text="🔙 Назад", callback_data="ship_main")
        builder.adjust(1)
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    finally:
        await conn.close()

@router.callback_query(F.data == "ship_install_engine")
async def install_t_item(callback: types.CallbackQuery):
    uid = callback.from_user.id
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        inv_items = meta.get("inventory", {}).get("equipment", [])
        engine_to_install = next((i for i in inv_items if i.get("type") == "T-engine"), None)

        if not engine_to_install:
            return await callback.answer("🚨 У тебе немає T-двигуна в інвентарі!", show_alert=True)

        inv_items.remove(engine_to_install)
        await conn.execute("""
            UPDATE ships SET engine = $1 
            WHERE id = (SELECT ship_id FROM capybaras WHERE owner_id = $2)
        """, json.dumps(engine_to_install, ensure_ascii=False), uid)
        
        await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(meta, ensure_ascii=False), uid)

        await callback.answer("⚙️ T-двигун встановлено!", show_alert=True)
        await ship_engine_room(callback)
    finally:
        await conn.close()

@router.callback_query(F.data.startswith("ship_crew:"))
async def show_ship_crew(callback: types.CallbackQuery):
    ship_id = int(callback.data.split(":")[1])
    conn = await get_db_connection()
    try:
        crew = await conn.fetch("""
            SELECT u.username, c.lvl FROM users u
            JOIN capybaras c ON u.tg_id = c.owner_id
            WHERE c.ship_id = $1 ORDER BY c.lvl DESC
        """, ship_id)
        
        text = "👥 <b>Екіпаж:</b>\n━━━━━━━━━━━━━━━\n" + "\n".join([f"{i+1}. {m['username']} (Lvl {m['lvl']})" for i, m in enumerate(crew)])
        builder = InlineKeyboardBuilder().button(text="🔙 Назад", callback_data="ship_main")
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    finally:
        await conn.close()

@router.callback_query(F.data == "ship_create_init")
async def ship_create_start(callback: types.CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
        
        if not row:
            return await callback.answer("❌ Капібару не знайдено!", show_alert=True)

        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        
        inventory = meta.get("inventory", {})
        materials = inventory.get("materials", {})
        wood_count = materials.get("wood", 0)

        if wood_count < 10:
            return await callback.answer(
                f"❌ Тобі потрібно 10 🪵 Дерева! (Зараз у тебе: {wood_count})", 
                show_alert=True
            )
        
        await state.set_state(ShipCreation.waiting_for_name)
        await callback.message.edit_text(
            "🔨 <b>Верф готова до роботи!</b>\n\n"
            "У тебе достатньо дерева для каркасу. Напиши назву свого майбутнього корабля:",
            reply_markup=InlineKeyboardBuilder()
                .button(text="❌ Скасувати", callback_data="ship_main")
                .as_markup()
        )
    finally:
        await conn.close()
@router.message(ShipCreation.waiting_for_name)
async def ship_name_received(message: types.Message, state: FSMContext):
    ship_name = message.text.strip()
    if len(ship_name) > 30:
        return await message.answer("⚠️ Назва занадто довга! Спробуй коротшу.")
    
    await state.update_data(name=ship_name)
    await state.set_state(ShipCreation.waiting_for_kanji)
    
    builder = InlineKeyboardBuilder()
    random_kanji = random.sample(list(KANJI_DICT.items()), 10)
    for kanji, mean in random_kanji:
        builder.button(text=f"{kanji} ({mean})", callback_data=f"set_kanji:{kanji}")
    
    builder.adjust(2)
    await message.answer(f"🚢 Назва «{ship_name}» прийнята!\nТепер обери <b>Прапороканджі</b>:", 
                         reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(ShipCreation.waiting_for_kanji, F.data.startswith("set_kanji:"))
async def ship_final_confirm(callback: types.CallbackQuery, state: FSMContext):
    kanji = callback.data.split(":")[1]
    data = await state.get_data()
    ship_name = data['name']
    uid = callback.from_user.id
    
    conn = await get_db_connection()
    try:
        res = await conn.execute("""
            UPDATE capybaras 
            SET meta = jsonb_set(
                meta, 
                '{inventory, materials, wood}', 
                ((meta->'inventory'->'materials'->>'wood')::int - 10)::text::jsonb
            )
            WHERE owner_id = $1 
            AND (meta->'inventory'->'materials'->>'wood')::int >= 10
        """, uid)

        if res == "UPDATE 0":
            return await callback.answer("❌ Недостатньо дерева! Потрібно 10 🪵", show_alert=True)

        ship_id = await conn.fetchval("""
            INSERT INTO ships (name, captain_id, lvl, gold, meta) 
            VALUES ($1, $2, 1, 0, $3) RETURNING id
        """, ship_name, uid, json.dumps({"flag": kanji}, ensure_ascii=False))

        await conn.execute("UPDATE capybaras SET ship_id = $1 WHERE owner_id = $2", ship_id, uid)
        
        await callback.message.edit_text(
            f"🎊 <b>Вітаємо, Капітане!</b>\n\n"
            f"Корабель {kanji} <b>«{ship_name}»</b> успішно збудовано з 10 🪵 і спущено на воду!", 
            parse_mode="HTML"
        )
        await state.clear()
        
    except Exception as e:
        if "unique constraint" in str(e).lower():
            await callback.answer("❌ Корабель з такою назвою вже існує!", show_alert=True)
        else:
            raise e
    finally:
        await conn.close()