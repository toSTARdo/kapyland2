import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import config

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_name = message.from_user.first_name
    await message.answer(
        f"🏴‍☠️ Вітаємо на борту {user_name}!\n"
        f"Версія системи: {config.VERSION}\n"
        f"Годувати капібару-пірата щоденно /feed\n"
        f"Митися теж не завадить /wash\n"
        f"Якщо лапи сверблять то /fight @username <- капі опонента-жертви\n"
        f"Капібаряче базове HP: {config.BASE_HITPOINTS} (3 серця)"
    )

async def main():
    print(f"🚀 Капіленд de Test (v{config.VERSION}) запущений!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())