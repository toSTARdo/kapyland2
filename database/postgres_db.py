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
            total_fights INTEGER DEFAULT 0,
            win_streak INTEGER DEFAULT 0,
            karma INTEGER DEFAULT 0,
            zen INTEGER DEFAULT 0,
            ship_id INTEGER REFERENCES ships(id) ON DELETE SET NULL,
            blessings TEXT[] DEFAULT '{}',
            curses TEXT[] DEFAULT '{}',
            current_quest JSONB DEFAULT NULL,
            meta JSONB DEFAULT '{
                "x": 76,
                "y": 140,
                "discovered": ["77,144"],
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
                    "attack": 0,
                    "defense": 0,
                    "luck": 0,
                    "agility": 0
                },
                "inventory": {
                    "food": {
                        "tangerines": 5,
                        "melon": 0,
                        "watermelon_slices": 0,
                        "mango": 0,
                        "kiwi": 0
                    },
                    "materials": {
                        "carp": 0,
                        "perch": 0,
                        "pufferfish": 0,
                        "octopus": 0,
                        "crab": 0,
                        "jellyfish": 0,
                        "swordfish": 0,
                        "shark": 0,
                        "herbs": 0,
                        "wood": 0
                    },
                    "loot": {
                        "chest": 0, 
                        "key": 0, 
                        "lottery_ticket": 10
                    },
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

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS ships (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            captain_id BIGINT REFERENCES users(tg_id),
            lvl INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            gold BIGINT DEFAULT 0,
            engine JSONB DEFAULT NULL,
            meta JSONB DEFAULT '{"flag": "🏴‍☠️"}'::jsonb,
            stats JSONB DEFAULT '{
                "hull": 100, 
                "cannons": 2, 
                "speed": 10
            }'::jsonb,
            cargo JSONB DEFAULT '{
                "wood": 0,
                "iron": 0,
                "watermelons": 0
            }'::jsonb,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        ALTER TABLE capybaras 
        ADD COLUMN IF NOT EXISTS ship_id INTEGER REFERENCES ships(id) ON DELETE SET NULL;
    ''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS world_state (
            key TEXT PRIMARY KEY,
            value JSONB DEFAULT '{}'::jsonb,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    await conn.execute('''
        INSERT INTO world_state (key, value) 
        VALUES 
        ('environment', '{
            "weather": "clear", 
            "time_of_day": "zenith", 
            "cycle_count": 1,
            "is_eclipse": false
        }')
        ON CONFLICT (key) DO NOTHING
    ''')
    
    await conn.close()
