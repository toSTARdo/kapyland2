import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
import config
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
from handlers.start import render_story_node
from middlewares.capy_guard import CapyGuardMiddleware

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

dp.update.middleware(CapyGuardMiddleware())

@app.get("/")
async def health_check():
    return {"status": "OK", "bot_version": config.VERSION}

@dp.message(Command("start"))
async def cmd_start(message: types.Message, forced_entry: bool = False):
    uid = message.from_user.id
    user_name = message.from_user.first_name
    
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
        reply_markup=get_main_kb(layout_type=layout)
    )

@dp.callback_query(F.data == "finish_prologue")
async def handle_isekai(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    
    conn = await get_db_connection()
    try:
        await conn.execute("UPDATE users SET has_finished_prologue = TRUE WHERE tg_id = $1", callback.from_user.id)
    finally:
        await conn.close()
    
    await callback.message.answer("💫 В очах темніє і остання думка це 🍊")
    
    await cmd_start(callback.message, forced_entry=True)
    await callback.answer()

async def run_bot():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

async def main():
    await init_pg()
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