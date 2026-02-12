import asyncpg
import json
from config import POSTGRE_URL

async def get_db_connection():
    return await asyncpg.connect(POSTGRE_URL)

async def init_pg():
    conn = await get_db_connection()
    
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            tg_id BIGINT PRIMARY KEY,
            username TEXT,
            lang TEXT DEFAULT 'ua',
            has_finished_prologue BOOLEAN DEFAULT FALSE,
            reincarnation_count INTEGER DEFAULT 0,
            reincarnation_multiplier FLOAT DEFAULT 1.0,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            kb_layout INTEGER DEFAULT 0
        )
    ''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS capybaras (
            id SERIAL PRIMARY KEY,
            owner_id BIGINT REFERENCES users(tg_id) ON DELETE CASCADE,
            name TEXT NOT NULL DEFAULT 'Безіменна булочка',
            lvl INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            win_streak INTEGER DEFAULT 0,
            meta JSONB DEFAULT '{
                "x": 76,
                "y": 140,
                "discovered": ["76,140"],
                "stamina": 100,
                "status": "active",
                "wake_up": null,
                "mode": "capy",
                "weight": 20.0,
                "hunger": 3,
                "cleanness": 3,
                "mood": "Normal",
                "stats": {
                    "hp": 3,
                    "attack": 1,
                    "defense": 1,
                    "luck": 1,
                    "agility": 1
                },
                "inventory": {
                    "food": {
                        "tangerines": 5,
                        "melon": 1,
                        "watermelon_slices": 14,
                        "mango": 7,
                        "kiwi": 2
                    },
                    "loot": {"chest": 0, "key": 0, "lottery_ticket": 5},
                    "equipment": []
                },
                "equipment": {
                    "weapon": "Лапки",
                    "armor": "Хутро",
                    "artifact": null
                },
                "last_feed": null,
                "last_wash": null,
                "last_weekly_lega": null
            }'::jsonb
        )
    ''')
    await conn.close()
