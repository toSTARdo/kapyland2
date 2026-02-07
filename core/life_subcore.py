from aiogram import types, Router
from aiogram.filters import Command

router = Router()

@router.message(Command("feed"))
async def cmd_feed(message: types.Message):
    await message.answer("Капібара поїла та набрала +5кг!")

@router.message(Command("wash"))
async def cmd_wash(message: types.Message):
    await message.answer("Капібара скупалася та позбулася бліх!")

@router.message(Command("sleep"))
async def cmd_sleep(message: types.Message):
    await message.answer("Капібара гарненько відіспалася і готова покоряти моря!")