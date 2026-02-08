import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import config
#==========================================#
from fastapi import FastAPI
import uvicorn
#==========================================#
from core.life_subcore import router as life_cmd_router
from core.activity_subcore import router as activity_cmd_router
from handlers.main_buttons import get_main_kb

logging.basicConfig(level=logging.INFO)
app = FastAPI()

bot = Bot(token=config.TOKEN)
dp = Dispatcher()

dp.include_router(life_cmd_router)
dp.include_router(activity_cmd_router)

@app.get("/")
async def health_check():
    return {"status": "OK", "bot_version": config.VERSION}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_name = message.from_user.first_name
    await message.answer(
        f"🏴‍☠️ Вітаємо на планеті Мофу {user_name}!\n"
        f"Версія бота: {config.VERSION}\n"
        f"Годувати капібару-пірата щоденно /feed\n"
        f"Митися теж не завадить /wash\n"
        f"Відновитися та відпочити /sleep\n"
        f"Якщо лапи сверблять то /fight @username <- капі опонента-жертви\n"
        f"Капібаряче базове HP: {config.BASE_HITPOINTS} (3 серця)",
        reply_markup=get_main_kb()
    )

async def run_bot():
    print(f"🚀 Капіленд de Test (v{config.VERSION}) запущений!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

async def main():
    config_uvicorn = uvicorn.Config(app=app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config_uvicorn)

    await asyncio.gather(
        server.serve(),
        run_bot()
    )
    print(f"🚀 Капіленд de Test (v{config.VERSION}) запущений!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())