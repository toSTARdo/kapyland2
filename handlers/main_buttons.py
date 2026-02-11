from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_kb(layout_type: int = 0) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    
    main = ["🐾 Профіль", "🎒 Інвентар"]
    actions = ["🌿 Їсти", "💤 Відпочити", "🧼 Покупатися"]
    adventure = ["🗺️ Карта", "⚓ Корабель", "📜 Квести"]
    activities = ["⚔️ Бій", "🎣 Рибалити", "🎟️ Лотерея"]
    utils = ["⚙️ Налаштування"]

    if layout_type == 1:
        all_btns = main + adventure + ["⚙️"]
        for btn in all_btns:
            builder.add(KeyboardButton(text=btn))
        builder.adjust(2)

    elif layout_type == 2:
        icons = ["🐾", "🎒", "🎟️", "⚔️", "🗺️", "📜", "⚓", "⚙️"]
        for icon in icons:
            builder.add(KeyboardButton(text=icon))
        builder.adjust(8)

    elif layout_type == 3:
        builder.row(*(KeyboardButton(text=btn) for btn in actions))
        builder.row(KeyboardButton(text="🐾 Профіль"), KeyboardButton(text="🎒 Інвентар"))
        builder.row(KeyboardButton(text="⚙️ Налаштування"))

    elif layout_type == 4:
        builder.row(KeyboardButton(text="⚔️ Бій"), KeyboardButton(text="🎒 Інвентар"))
        builder.row(KeyboardButton(text="🐾 Профіль"), KeyboardButton(text="🎟️ Лотерея"))
        builder.row(KeyboardButton(text="⚙️ Налаштування"))

    elif layout_type == 5:
        builder.row(KeyboardButton(text="🗺️ Карта"), KeyboardButton(text="⚓ Корабель"))
        builder.row(KeyboardButton(text="📜 Квести"), KeyboardButton(text="🎣 Рибалити"))
        builder.row(KeyboardButton(text="🐾 Профіль"), KeyboardButton(text="⚙️"))

    elif layout_type == 6: #for now same as the standart
        builder.row(KeyboardButton(text="🐾 Профіль"), KeyboardButton(text="🎒 Інвентар"), KeyboardButton(text="🎟️ Лотерея"))
        builder.row(KeyboardButton(text="⚔️ Бій"), KeyboardButton(text="🗺️ Карта"), KeyboardButton(text="📜 Квести"))
        builder.row(KeyboardButton(text="⚓ Корабель"), KeyboardButton(text="⚙️ Налаштування"))

    else:
        builder.row(KeyboardButton(text="🐾 Профіль"), KeyboardButton(text="🎒 Інвентар"), KeyboardButton(text="🎟️ Лотерея"))
        builder.row(KeyboardButton(text="⚔️ Бій"), KeyboardButton(text="🗺️ Карта"), KeyboardButton(text="📜 Квести"))
        builder.row(KeyboardButton(text="⚓ Корабель"), KeyboardButton(text="⚙️ Налаштування"))

    return builder.as_markup(resize_keyboard=True)

def get_settings_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(
        text="📝 Змінити ім'я", 
        callback_data="change_name_start")
    )
    
    builder.row(InlineKeyboardButton(
        text="🔄 Змінити вигляд меню", 
        callback_data="toggle_layout")
    )
    
    return builder.as_markup()

"""
🎒 Інвентар
⚔️ Бої
⚙️ Налаштування
⚓ Моя команда
📜 Квести
🎣 Рибалити | 🦀/🐟/🦈/🪼/🐡/
🧭 І
🗺️ Карта
🐾 Мій профіль

🌿 Їсти 💤 Відпочити 🧼 Покупатися | 💰 Продати
🥭🍊🍉🍈🥝 - Їсти з ефектами
🍄‍🟫 - Їсти гриб

🎟️ Лотерея
⚗️ Синтез
🗃 - Скриня 🔑 - Ключі
🔮
Головні напрями розвитку
⚡
🍀
💪
🛡️

----
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