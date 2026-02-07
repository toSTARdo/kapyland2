from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def get_main_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    
    #MAIN/MOST USED
    builder.row(
        KeyboardButton(text="👤 Профіль"),
        KeyboardButton(text="🎒 Інвентар")
    )
    #LESS USED
    builder.row(
        KeyboardButton(text="⚔️ Бій"),
        KeyboardButton(text="⛵ Карта"),
        KeyboardButton(text="📜 Квести")
    )
    #RARELY USED
    builder.row(
        KeyboardButton(text="⚓ Корабель"),
        KeyboardButton(text="⚙️ Налаштування")
    )
    
    return builder.as_markup(resize_keyboard=True)