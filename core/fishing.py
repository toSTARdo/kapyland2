import asyncio, json, random, datetime
from aiogram import Router, types, html, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.helpers import consume_stamina
from database.postgres_db import get_db_connection

router = Router()

@router.callback_query(F.data == "fish")
async def handle_fishing(callback: types.CallbackQuery):
    uid = callback.from_user.id
    conn = await get_db_connection()
    
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
        if not row: return
        
        meta = row['meta'] if isinstance(row['meta'], dict) else json.loads(row['meta'])
        stamina = meta.get("stamina", 0)
        inventory = meta.get("inventory", {})
        equipment_list = inventory.get("equipment", [])

        rod_item = next((
            item for item in equipment_list 
            if isinstance(item, dict) and ("вудочка" in item.get("name", "").lower() or "рибальські снасті" in item.get("name", "").lower())
        ), None)
        
        if not rod_item:
            return await callback.answer("❌ Тобі потрібна вудочка в спорядженні!", show_alert=True)
        
        rod_lvl = rod_item.get("lvl", 0)
        luck_mult = 1 + (rod_lvl * 0.25) 

        if not await consume_stamina(conn, uid, "fish"):
            return await callback.answer("🪫 Недостатньо енергії!", show_alert=True)

        loot_pool = [
            {"name": "🦴 Стара кістка", "min_w": 0.1, "max_w": 0.4, "chance": 12, "type": "trash"},
            {"name": "📰 Промокла газета", "min_w": 0.05, "max_w": 0.1, "chance": 12, "type": "trash"},
            {"name": "🥫 Іржава бляшанка", "min_w": 0.1, "max_w": 0.3, "chance": 10, "type": "trash"},

            {"name": "🐟 Океанічний карась", "min_w": 0.3, "max_w": 1.5, "chance": 15, "type": "materials", "key": "carp"},
            {"name": "🐠 Уробороокеанський Окунь", "min_w": 0.2, "max_w": 0.8, "chance": 10, "type": "materials", "key": "perch"},
            {"name": "🐡 Риба-пупупу", "min_w": 0.5, "max_w": 2.0, "chance": 5, "type": "materials", "key": "pufferfish"},
            {"name": "🐙 Восьмирук", "min_w": 1.0, "max_w": 5.0, "chance": 4, "type": "materials", "key": "octopus"},
            {"name": "🦀 Бокохід", "min_w": 0.2, "max_w": 1.2, "chance": 5, "type": "materials", "key": "crab"},
            {"name": "🪼 Медуза", "min_w": 0.1, "max_w": 0.5, "chance": 8, "type": "materials", "key": "jellyfish"},
            {"name": "🗡️🐟 Риба-меч", "min_w": 15.0, "max_w": 50.0, "chance": 2, "type": "materials", "key": "swordfish"},
            {"name": "🦈 Маленька акула", "min_w": 10.0, "max_w": 40.0, "chance": 1, "type": "materials", "key": "shark"},
            
            {"name": "🍉 Скибочка кавуна", "min_w": 1, "max_w": 1, "chance": 20, "type": "food", "key": "watermelon_slices"},
            {"name": "🍊 Мандарин", "min_w": 0.5, "max_w": 0.5, "chance": 8, "type": "food", "key": "tangerines"},
            {"name": "🥭 Манго", "min_w": 0.5, "max_w": 0.5, "chance": 2, "type": "food", "key": "mango"},
            {"name": "🥝 Ківі", "min_w": 0.5, "max_w": 0.5, "chance": 2, "type": "food", "key": "kiwi"},
            {"name": "🍈 Диня", "min_w": 5.0, "max_w": 5.0, "chance": 4, "type": "food", "key": "melon"},
            
            {"name": "🗃 Скриня", "min_w": 5.0, "max_w": 10.0, "chance": 2, "type": "special", "key": "chest"},
            {"name": "🗝️ Ключ", "min_w": 0.1, "max_w": 0.2, "chance": 2, "type": "special", "key": "key"},
            {"name": "🎟️ Лотерейний квиток", "min_w": 0.01, "max_w": 0.01, "chance": 1, "type": "special", "key": "lottery_ticket"},
            {"name": "🫙 Стара мапа", "min_w": 0.1, "max_w": 0.1, "chance": 2, "type": "treasure_map", "key": "treasure_maps"}
        ]

        found_mythic = False
        if rod_lvl >= 5 and random.random() < 0.03:
            item = {"name": "🔮 Перлина Ехвазу", "min_w": 0.5, "max_w": 0.5, "type": "loot", "key": "pearl_of_ehwaz"}
            found_mythic = True
        else:
            item = random.choices(loot_pool, weights=[i['chance'] for i in loot_pool])[0]
        
        weight_bonus = 1 + (rod_lvl * 0.15)
        fish_weight = round(random.uniform(item['min_w'], item['max_w'] * weight_bonus), 2)

        if "fishing_stats" not in meta:
            meta["fishing_stats"] = {"max_weight": 0.0, "total_weight": 0.0}
        
        if item['type'] != "trash":
            meta["fishing_stats"]["total_weight"] = round(meta["fishing_stats"].get("total_weight", 0) + fish_weight, 2)
            if fish_weight > meta["fishing_stats"].get("max_weight", 0):
                meta["fishing_stats"]["max_weight"] = fish_weight
        
        meta["stamina"] = stamina - 10
        inventory_note = ""

        if item['type'] == "trash":
            inventory_note = "🗑️ <i>Ви викинули сміття назад.</i>"
        elif item['type'] == "treasure_map":
            map_id = f"#{random.randint(100, 999)}"
            new_map = {"id": map_id, "pos": f"{random.randint(0,149)},{random.randint(0,149)}", "bought_at": str(datetime.date.today())}
            loot = inventory.setdefault("loot", {})
            loot.setdefault("treasure_maps", []).append(new_map)
            inventory_note = f"🗺️ <b>Знайдено мапу {map_id}!</b>"
        else:
            if item.get('key') == "pearl_of_ehwaz" or item['type'] in ["special", "loot"]:
                folder = "loot"
            elif item['type'] == "food":
                folder = "food"
            else:
                folder = "materials"
                
            target = inventory.setdefault(folder, {})
            target[item['key']] = target.get(item['key'], 0) + 1
            inventory_note = f"📦 <i>{item['name']} додано в {folder}!</i>"

        await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(meta, ensure_ascii=False), uid)

        stars = "⭐" * rod_lvl
        title = "✨ МІФІЧНА ЗНАХІДКА ✨" if found_mythic else f"🎣 Риболовля {stars}"
        
        builder = InlineKeyboardBuilder()
        builder.button(text="Закинути знову", callback_data="fish")
        builder.button(text="🔙 Назад", callback_data="open_adventure")
        builder.adjust(1)

        await callback.message.edit_text(
            f"🎣 <b>Риболовля</b>\n━━━━━━━━━━━━━━━\n"
            f"Чілимо... Раптом поплавок смикнувся!\n"
            f"Твій улов: <b>{item['name']}</b> ({fish_weight} кг)\n\n"
            f"{inventory_note}\n"
            f"🔋 Залишок енергії: {meta['stamina']}/100",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    finally:
        await conn.close()