from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InlineKeyboardBuilder

def get_main_kb(layout_type: int = 0) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    
    if layout_type == 1:
        buttons = [
            "👤 Профіль", "🎒 Інвентар", "⚔️ Бій",
            "⛵ Карта", "📜 Квести", "⚓ Корабель", "⚙️ Налаштування"
        ]
        for btn in buttons:
            builder.add(KeyboardButton(text=btn))
        builder.adjust(3)
        
    else:
        builder.row(KeyboardButton(text="👤 Профіль"), KeyboardButton(text="🎒 Інвентар"))
        builder.row(KeyboardButton(text="⚔️ Бій"), KeyboardButton(text="⛵ Карта"), KeyboardButton(text="📜 Квести"))
        builder.row(KeyboardButton(text="⚓ Корабель"), KeyboardButton(text="⚙️ Налаштування"))
    
    return builder.as_markup(resize_keyboard=True)

def get_settings_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🔄 Змінити вигляд меню", 
        callback_data="toggle_layout")
    )
    return builder.as_markup()