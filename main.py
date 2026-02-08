import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
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

logging.basicConfig(level=logging.INFO)
app = FastAPI()

bot = Bot(token=config.TOKEN)
dp = Dispatcher()

dp.include_router(life_cmd_router)
dp.include_router(activity_cmd_router)
dp.include_router(settings_router)

@app.get("/")
async def health_check():
    return {"status": "OK", "bot_version": config.VERSION}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    uid = message.from_user.id
    user_name = message.from_user.first_name
    
    conn = await get_db_connection()
    try:
        await conn.execute(
            "INSERT INTO users (tg_id, username) VALUES ($1, $2) ON CONFLICT (tg_id) DO NOTHING",
            uid, user_name
        )
        await conn.execute(
            "INSERT INTO capybaras (owner_id, name) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            uid, f"Капібара {user_name}"
        )
        user_data = await conn.fetchrow("SELECT kb_layout FROM users WHERE tg_id = $1", uid)
    finally:
        await conn.close()

    layout = user_data['kb_layout'] if user_data else 0

    await message.answer(
        f"🏴‍☠️ Вітаємо на планеті Мофу {user_name}!\n"
        f"Версія бота: {config.VERSION}\n"
        f"Годувати капібару-пірата щоденно /feed\n"
        f"Митися теж не завадить /wash\n"
        f"Відновитися та відпочити /sleep\n"
        f"Якщо лапи сверблять то /fight @username <- капі опонента-жертви\n"
        f"Капібаряче базове HP: {config.BASE_HITPOINTS} (3 серця)",
        reply_markup=get_main_kb(layout_type=layout)
    )

async def run_bot():
    await init_pg()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

async def main():
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