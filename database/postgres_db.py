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
            
            -- Глобальний прогрес аккаунту
            reincarnation_count INTEGER DEFAULT 0,
            reincarnation_multiplier FLOAT DEFAULT 1.0,
            
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS capybaras (
            id SERIAL PRIMARY KEY,
            owner_id BIGINT REFERENCES users(tg_id) ON DELETE CASCADE,
            name TEXT NOT NULL DEFAULT 'Безіменна булочка',
            
            -- Прогресія
            lvl INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            energy INTEGER DEFAULT 100,
            
            -- Бойова статистика
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            win_streak INTEGER DEFAULT 0,
            
            -- JSONB Гнучкі дані (Заміна MongoDB)
            meta JSONB DEFAULT '{
                "weight": 20.0,
                "stats": {
                    "attack": 0,
                    "defense": 0,
                    "luck": 0,
                    "agility": 0
                },
                "effects": {
                    "blessings": [],
                    "curses": []
                },
                "inventory": {
                    "food": {"grass": 5},
                    "loot": {"wooden_chest": 0, "golden_key": 0},
                    "items": []
                },
                "equipment": {
                    "weapon": "Лапки",
                    "armor": null,
                    "artifact": null
                },
                "last_feed": null
            }'::jsonb
        )
    ''')
    await conn.close()