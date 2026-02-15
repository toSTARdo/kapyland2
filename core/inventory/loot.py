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
        
        if loot.get("chest", 0) < 1 or loot.get("key", 0) < 1:
            return await callback.answer("❌ Тобі потрібна скриня та ключ!", show_alert=True)

        if random.random() < 0.5:
            await conn.execute("""
                UPDATE capybaras SET meta = jsonb_set(
                    jsonb_set(meta, '{inventory, loot, chest}', ((meta->'inventory'->'loot'->>'chest')::int - 1)::text::jsonb),
                    '{inventory, loot, key}', ((meta->'inventory'->'loot'->>'key')::int - 1)::text::jsonb
                ) WHERE owner_id = $1
            """, uid)

            await callback.message.edit_text(
                "💥 <b>ОТ БЛЯХА!</b>\n"
                "━━━━━━━━━━━━━━━\n"
                "Скриня виявилася <b>Міміком</b>! Вона клацає зубами і кидається на тебе!",
                parse_mode="HTML"
            )
            
            asyncio.create_task(run_battle_logic(callback, bot_type="mimic"))

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

        new_equip = []
        if random.random() < 0.1:
            rarity = random.choices(["Common", "Rare", "Epic", "Legendary"], weights=[60, 25, 12, 3])[0]
            item = random.choice(ARTIFACTS.get(rarity, [{"name": "Іржавий ніж"}]))
            new_equip.append({"name": item["name"], "rarity": rarity, "stats": item.get("stats", {})})
            rewards.append(f"✨ {rarity}: {item['name']}")

        base_meta = """
            jsonb_set(
                jsonb_set(meta, '{inventory, loot, chest}', ((meta->'inventory'->'loot'->>'chest')::int - 1)::text::jsonb),
                '{inventory, loot, key}', ((meta->'inventory'->'loot'->>'key')::int - 1)::text::jsonb
            )
        """
        
        if new_maps:
            base_meta = f"jsonb_set({base_meta}, '{{inventory, loot, treasure_maps}}', (COALESCE(meta->'inventory'->'loot'->'treasure_maps', '[]'::jsonb) || '{json.dumps(new_maps)}'::jsonb))"
        if new_equip:
            base_meta = f"jsonb_set({base_meta}, '{{inventory, equipment}}', (COALESCE(meta->'inventory'->'equipment', '[]'::jsonb) || '{json.dumps(new_equip)}'::jsonb))"

        final_sql_meta = base_meta
        for part in sql_parts:
            final_sql_meta = part.replace("COALESCE(target_meta, meta)", final_sql_meta)

        await conn.execute(f"UPDATE capybaras SET meta = {final_sql_meta} WHERE owner_id = $1", uid)

        loot_list = "\n".join([f"• {r}" for r in rewards])
        await callback.message.edit_text(
            f"🔓 <b>Скриню відкрито!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"Твій улов:\n{loot_list}\n\n"
            f"📦 <i>Усі речі перенесено в інвентар</i>",
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"Grand Chest Error: {e}")
        await callback.answer("🚨 Помилка при розпакуванні луту!")
    finally:
        await conn.close()
