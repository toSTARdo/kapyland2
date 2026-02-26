import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
import config
from config import DEV_ID, IMAGES_URLS
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
#==============================================================#
from fastapi import FastAPI
import uvicorn
#==============================================================#
from database.postgres_db import init_pg, get_db_connection
from core.life_subcore import router as life_cmd_router
from core.activity_subcore import router as activity_cmd_router
from handlers.main_buttons import get_main_kb
from handlers.setting import router as settings_router
from handlers.lottery import router as lottery_router
from core.map import router as map_router
from handlers.start import router as prolog_router
from handlers.quests import router as quest_router
from handlers.meditation import router as zen_router
from core.inventory.food import router as food_router
from core.inventory.loot import router as loot_router
from core.inventory.equipment import router as eq_router
from core.fishing import router as fish_router
from handlers.ships import router as ship_router
from handlers.emotes import router as emote_router
from handlers.alchemy import router as alchemy_router
from handlers.forge import router as forge_router
from handlers.start import render_story_node
from middleware.capy_guard import CapyGuardMiddleware
from jobs.send_goodnight import send_goodnight

logging.basicConfig(level=logging.INFO)
app = FastAPI()

bot = Bot(token=config.TOKEN)
dp = Dispatcher(storage=MemoryStorage())

dp.include_router(prolog_router)
dp.include_router(life_cmd_router)
dp.include_router(activity_cmd_router)
dp.include_router(settings_router)
dp.include_router(lottery_router)
dp.include_router(map_router)
dp.include_router(quest_router)
dp.include_router(food_router)
dp.include_router(loot_router)
dp.include_router(eq_router)
dp.include_router(fish_router)
dp.include_router(zen_router)
dp.include_router(ship_router)
dp.include_router(emote_router)
dp.include_router(alchemy_router)
dp.include_router(forge_router)

dp.update.middleware(CapyGuardMiddleware())

@app.get("/")
async def health_check():
    return {"status": "OK", "bot_version": config.VERSION}

@dp.message(Command("start"))
async def cmd_start(message: types.Message, forced_entry: bool = False, user_id: int = None):
    uid = user_id if user_id else message.from_user.id
    user_name = message.from_user.first_name if message.from_user else "Капібара"
    
    conn = await get_db_connection()
    try:
        user = await conn.fetchrow(
            "INSERT INTO users (tg_id, username) VALUES ($1, $2) "
            "ON CONFLICT (tg_id) DO UPDATE SET username = EXCLUDED.username "
            "RETURNING has_finished_prologue, kb_layout",
            uid, user_name
        )

        if not user['has_finished_prologue'] and not forced_entry:
            await render_story_node(message, "1")
            return

        capy_exists = await conn.fetchval("SELECT id FROM capybaras WHERE owner_id = $1", uid)
        if not capy_exists:
            await conn.execute(
                "INSERT INTO capybaras (owner_id, name) VALUES ($1, $2)",
                uid, "Безіменна булочка"
            )
            is_new = True
        else:
            is_new = False
        
        layout = user['kb_layout'] if user else 0
    finally:
        await conn.close()

    welcome_text = f"🏴‍☠️ Вітаємо на планеті Мофу, {user_name}!" if is_new else f"⚓️ З поверненням, {user_name}!"
    await message.answer(
        f"{welcome_text}\n\n"
        f"Версія бота: {config.VERSION}\n"
        "🍎 /feed | 🧼 /wash | 💤 /sleep",
        reply_markup=get_main_kb()
    )

@dp.callback_query(F.data == "finish_prologue")
async def handle_isekai(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    uid = callback.from_user.id
    user_name = callback.from_user.first_name
    
    conn = await get_db_connection()
    try:
        await conn.execute("UPDATE users SET has_finished_prologue = TRUE WHERE tg_id = $1", uid)
        
        capy_exists = await conn.fetchval("SELECT id FROM capybaras WHERE owner_id = $1", uid)
        if not capy_exists:
            await conn.execute(
                "INSERT INTO capybaras (owner_id, name) VALUES ($1, $2)",
                uid, "Безіменна булочка"
            )
        
        user_data = await conn.fetchrow("SELECT kb_layout FROM users WHERE tg_id = $1", uid)
        layout = user_data['kb_layout'] if user_data else 0
    finally:
        await conn.close()
    
    await callback.message.answer("💫 В очах темніє і остання думка це 🍊")
    
    welcome_text = f"🏴‍☠️ Вітаємо на планеті Мофу, {user_name}!"
    await callback.message.answer(
        f"{welcome_text}\n\n"
        f"Версія бота: {config.VERSION}\n"
        "🍎 /feed | 🧼 /wash | 💤 /sleep",
        reply_markup=get_main_kb()
    )
    await callback.answer()

@dp.message(Command("notify"))
async def broadcast_update(message: types.Message):
    if message.from_user.id != int(DEV_ID):
        return await message.answer("❌ Доступ заборонено. Тільки для розробника.")

    broadcast_text = message.text.replace("/notify", "").strip()
    
    if not broadcast_text:
        return await message.answer("⚠️ Введіть текст повідомлення після команди.")

    conn = await get_db_connection()
    try:
        rows = await conn.fetch("SELECT DISTINCT owner_id FROM capybaras")
        
        count = 0
        error_count = 0
        
        sent_msg = await message.answer(f"🚀 Починаю розсилку на {len(rows)} капібар...")

        for row in rows:
            uid = row['owner_id']
            try:
                await message.bot.send_message(
                    chat_id=uid,
                    text=f"📰 <b>Газета MOFU</b>\n━━━━━━━━━━━━━━━\n\n{broadcast_text}",
                    parse_mode="HTML"
                )
                count += 1
                await asyncio.sleep(0.05) 
            except Exception:
                error_count += 1

        await sent_msg.edit_text(
            f"✅ Розсилку завершено!\n\n"
            f"📥 Отримали: {count}\n"
            f"🚫 Заблокували бота: {error_count}"
        )

    finally:
        await conn.close()

async def give_everyday_gift(bot: Bot):
    conn = await get_db_connection()
    try:
        players = await conn.fetch("SELECT owner_id FROM capybaras")
        
        await conn.execute('''
            UPDATE capybaras 
            SET meta = jsonb_set(
                meta, 
                '{inventory, loot, lottery_ticket}', 
                (COALESCE(meta->'inventory'->'loot'->>'lottery_ticket', '0')::int + 1)::text::jsonb
            )
        ''')
        
        print(f"🎁 Подарунок нараховано в БД для {len(players)} гравців.")

        sent_count = 0
        for player in players:
            uid = player['owner_id']
            try:
                await bot.send_photo(
                    chat_id=uid,
                    photo=IMAGES_URLS["delivery"],
                    caption=(
                        "🎁 <b>Ранкова пошта Архіпелагу!</b>\n\n"
                        "Поки ви спали, чайки-поштарі принесли вам 🎟 <b>Лотерейний квиток</b>.\n"
                        "Він уже чекає у вашому інвентарі. Гарного дня!"
                    ),
                    parse_mode="HTML"
                )
                sent_count += 1
                await asyncio.sleep(0.05)
                
            except TelegramForbiddenError:
                print(f"🚫 Користувач {uid} заблокував бота.")
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
            except Exception as e:
                print(f"⚠️ Помилка надсилання до {uid}: {e}")

        print(f"📢 Розсилка завершена. Успішно надіслано: {sent_count} повідомлень.")

    except Exception as e:
        print(f"❌ Критична помилка у give_everyday_gift: {e}")
    finally:
        await conn.close()

async def run_bot():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

async def main():
    await init_pg()
    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
    scheduler.add_job(give_everyday_gift, 'cron', hour=8, minute=0, args=[bot])
    scheduler.add_job(send_goodnight, 'cron', hour=20, minute=0, args=[bot])
    scheduler.start()
    config_uvicorn = uvicorn.Config(app=app, host="0.0.0.0", port=8000, log_level="error")
    server = uvicorn.Server(config_uvicorn)

    await asyncio.gather(
        server.serve(),
        run_bot()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Stopped")
