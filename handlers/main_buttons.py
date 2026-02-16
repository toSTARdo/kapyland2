from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

def get_main_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text="🐾 Капібара"),
        KeyboardButton(text="🎒 Трюм")
    )
    builder.row(
        KeyboardButton(text="🧭 Пригоди"),
        KeyboardButton(text="⚓ Порт")
    )
    
    return builder.as_markup(resize_keyboard=True)

def get_settings_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📝 Змінити ім'я", callback_data="change_name_start")
    builder.button(text="🎬 Додати переможні реакції", callback_data="setup_victory_gif")
    
    builder.row(InlineKeyboardButton(text="⬅️ Назад до Порту", callback_data="open_port"))
    
    return builder.as_markup()

"""
🍄‍🟫 - Їсти гриб

⚗️ Синтез

🔮

🗡️
🔰
🧿
🐲🐦‍🔥🦄

5 lvl - ships & map (50exp)
|--8 lvl (128exp) fishing & foraging
11 lvl - boss fights & plot (242exp)
|--14 lvl (392exp)
17 lvl - quests (578exp)
|--20 lvl (800exp)
23 lvl - kiwi forgery (1058exp)
|--26 lvl (1352exp)
29 lvl (1682exp)
|--31 lvl (1922exp)
34 lvl - syntesis / pearls quests (2312exp)
"""