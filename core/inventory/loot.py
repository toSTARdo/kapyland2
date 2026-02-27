import asyncio, json, random
from aiogram import Router, types, html, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.capybara_mechanics import get_user_inventory
from database.postgres_db import get_db_connection
from core.activity_subcore import run_battle_logic
from config import ARTIFACTS

router = Router()

@router.callback_query(F.data == "open_chest")
async def handle_open_chest(callback: types.CallbackQuery):
    uid = callback.from_user.id
    conn = await get_db_connection()
    
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", uid)
        if not row: return
        
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        inv = meta.get("inventory", {})
        loot = inv.get("loot", {})
        
        has_chest = loot.get("chest", 0) >= 1
        has_key = loot.get("key", 0) >= 1
        has_lockpicker = loot.get("lockpicker", 0) >= 1

        if not has_chest:
            return await callback.answer("❌ У тебе немає скрині!", show_alert=True)
        
        method = None
        if has_key:
            method = "key"
        elif has_lockpicker:
            method = "lockpicker"
        else:
            return await callback.answer("❌ Тобі потрібен ключ або відмичка!", show_alert=True)

        lockpicker_broken = False
        if method == "lockpicker":
            if random.random() > 0.8:
                lockpicker_broken = True

        if method == "key":
            base_meta = """
                jsonb_set(
                    jsonb_set(meta, '{inventory, loot, chest}', ((meta->'inventory'->'loot'->>'chest')::int - 1)::text::jsonb),
                    '{inventory, loot, key}', ((meta->'inventory'->'loot'->>'key')::int - 1)::text::jsonb
                )
            """
        else:
            if lockpicker_broken:
                await conn.execute("""
                    UPDATE capybaras SET meta = jsonb_set(
                        meta, '{inventory, loot, lockpicker}', 
                        ((meta->'inventory'->'loot'->>'lockpicker')::int - 1)::text::jsonb
                    ) WHERE owner_id = $1
                """, uid)
                return await callback.message.edit_text(
                    "🔧 <b>Крак!</b>\n━━━━━━━━━━━━━━━\n"
                    "Твоя відмичка зламалася в замку. Скриня залишилася закритою, а інструмент зіпсовано.",
                    parse_mode="HTML"
                )
            else:
                base_meta = """
                    jsonb_set(meta, '{inventory, loot, chest}', ((meta->'inventory'->'loot'->>'chest')::int - 1)::text::jsonb)
                """
        
        if random.random() < 0.02:
            await conn.execute(f"UPDATE capybaras SET meta = {base_meta} WHERE owner_id = $1", uid)
            await callback.message.edit_text(
                "💥 <b>ОТ БЛЯХА!</b>\n━━━━━━━━━━━━━━━\n"
                "Скриня виявилася <b>Міміком</b>! Вона з’їла твій інструмент і кидається на тебе!",
                parse_mode="HTML"
            )
            return asyncio.create_task(run_battle_logic(callback, bot_type="mimic"))

        rewards = []
        sql_parts = []
        
        food_pool = [
            {"key": "tangerines", "name": "🍊 Мандарин", "chance": 50, "amt": (3, 7)},
            {"key": "watermelon_slices", "name": "🍉 Скибочка кавуна", "chance": 30, "amt": (2, 4)},
            {"key": "mango", "name": "🥭 Манго", "chance": 15, "amt": (1, 2)},
            {"key": "kiwi", "name": "🥝 Ківі", "chance": 5, "amt": (1, 1)}
        ]
        
        for _ in range(2): 
            f = random.choices(food_pool, weights=[i['chance'] for i in food_pool])[0]
            count = random.randint(*f['amt'])
            rewards.append(f"{f['name']} x{count}")
            sql_parts.append(f"jsonb_set(COALESCE(target_meta, meta), '{{inventory, food, {f['key']}}}', (COALESCE(meta->'inventory'->'food'->>'{f['key']}', '0')::int + {count})::text::jsonb)")

        if random.random() < 0.4:
            t_count = random.randint(1, 3)
            rewards.append(f"🎟️ Квиток x{t_count}")
            sql_parts.append(f"jsonb_set(COALESCE(target_meta, meta), '{{inventory, loot, lottery_ticket}}', (COALESCE(meta->'inventory'->'loot'->>'lottery_ticket', '0')::int + {t_count})::text::jsonb)")

        new_maps = []
        if random.random() < 0.2:
            map_id = random.randint(100, 999)
            new_maps.append({"id": map_id, "pos": f"{random.randint(0,149)},{random.randint(0,149)}"})
            rewards.append(f"🗺️ Карта #{map_id}")
            base_meta = f"jsonb_set({base_meta}, '{{inventory, loot, treasure_maps}}', (COALESCE(meta->'inventory'->'loot'->'treasure_maps', '[]'::jsonb) || '{json.dumps(new_maps)}'::jsonb))"

        if random.random() < 0.05:
            defeated = meta.get("stats_track", {}).get("bosses_defeated", 0)
            next_boss = defeated + 1
            
            if next_boss <= 20:
                existing_maps = inv.get("loot", {}).get("treasure_maps", [])
                has_this_boss_map = any(m.get("boss_num") == next_boss for m in existing_maps)
                
                if not has_this_boss_map:
                    boss_coords = f"{next_boss},{next_boss}"
                    
                    new_maps.append({
                        "type": "boss_den", 
                        "boss_num": next_boss, 
                        "pos": boss_coords,
                        "discovered": datetime.now().isoformat()
                    })
                    rewards.append(f"💀 Карта лігва: Бос №{next_boss}\n└ 📍 Координати: {boss_coords}")

        if new_maps:
            base_meta = f"jsonb_set({base_meta}, '{{inventory, loot, treasure_maps}}', (COALESCE(meta->'inventory'->'loot'->'treasure_maps', '[]'::jsonb) || '{json.dumps(new_maps)}'::jsonb))"

        new_equip = []
        if random.random() < 0.15:
            rarity = random.choices(["Epic", "Legendary"], weights=[1, 1])[0]
            item = random.choice(ARTIFACTS.get(rarity, [{"name": "Іржавий ніж"}]))
            new_equip.append({"name": item["name"], "rarity": rarity, "stats": item.get("stats", {})})
            rewards.append(f"✨ {rarity}: {item['name']}")
            base_meta = f"jsonb_set({base_meta}, '{{inventory, equipment_storage}}', (COALESCE(meta->'inventory'->'equipment_storage', '[]'::jsonb) || '{json.dumps(new_equip)}'::jsonb))"

        # Застосовуємо всі накопичені SQL зміни
        final_sql_meta = base_meta
        for part in sql_parts:
            final_sql_meta = part.replace("COALESCE(target_meta, meta)", final_sql_meta)

        await conn.execute(f"UPDATE capybaras SET meta = {final_sql_meta} WHERE owner_id = $1", uid)

        loot_list = "\n".join([f"• {r}" for r in rewards])
        method_text = "🔑 Використано ключ" if method == "key" else "🔧 Використано відмичку"
        
        await callback.message.edit_text(
            f"🔓 <b>Скриню відкрито!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"<i>{method_text}</i>\n\n"
            f"Твій улов:\n{loot_list}\n\n"
            f"📦 <i>Усі речі перенесено в інвентар</i>",
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"Grand Chest Error: {e}")
        await callback.answer("🚨 Помилка при розпакуванні луту!")
    finally:
        await conn.close()