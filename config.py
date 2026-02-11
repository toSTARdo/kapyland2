import os
import json
from dotenv import load_dotenv

load_dotenv()

#========================HELPER===========================#

#Завантажувально завантажувальний завантажувач завантажень
def load_game_data(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"⚠️ Помилка завантаження {filepath}: {e}")
        return {}

#===================ENVIROMENT VARS======================#

TOKEN = os.getenv("BOT_TOKEN")
DEV_ID = os.getenv("DEV_ID")
MONGO_URL = os.getenv("MONGO_URL")
POSTGRE_URL = os.getenv("POSTGRE_URL")

#===================CONSTANTS============================#

    #FIGHT_CONSTS:
BASE_HIT_CHANCE = 0.33
BASE_HEARTS = 3
UNITS_PER_HEART = 2
BASE_HITPOINTS = BASE_HEARTS * UNITS_PER_HEART
BASE_BLOCK_CHANCE = 0.05
STAT_WEIGHTS = {
    # FIGHT
    "atk_to_hit": 0.04,
    "def_to_block": 0.05,
    "agi_to_dodge": 0.03,
    "luck_to_crit": 0.02,
    
    # NON-FIGHT
    "agi_to_trap": 0.03,
    "def_to_anti_steal": 0.05,
    "luck_to_drop": 0.01,
    "luck_to_steal": 0.01
}

    #ECONOMY_СONSTS:
DROP_RATES = {
    "common": 0.67,
    "rare": 0.20,
    "epic": 0.10,
    "legendary": 0.03
}

RARITY_META = {
    "common": {"emoji": "⚪️", "label": "Звичайний", "color": 0x808080},
    "rare": {"emoji": "🔵", "label": "Рідкісний", "color": 0x0000FF},
    "epic": {"emoji": "🟣", "label": "Епічний", "color": 0xA020F0},
    "legendary": {"emoji": "💎", "label": "Легендарний", "color": 0xFFD700}
}

#====================ITEMS LIST============================#

    #GENERAL:
GAME_ITEMS = load_game_data("data/game_items.json")

    #ARTIFACTS:
ARTIFACTS = GAME_ITEMS.get("GACHA_ITEMS", {})

    #WEAPON:
WEAPON = GAME_ITEMS.get("WEAPONS", {})

    #ARMOR:
ARMOR = GAME_ITEMS.get("ARMOR", {})


#MISC:
VERSION = "1.4.0"

#BAD WORDS LIST:
BAD_WORDS = load_game_data("data/bad_words.json").get("ukrainian", ["капілайка"])