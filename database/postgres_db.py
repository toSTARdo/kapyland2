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
        CREATE TABLE IF NOT EXISTS ships (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            captain_id BIGINT REFERENCES users(tg_id),
            lvl INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            gold BIGINT DEFAULT 0,
            engine JSONB DEFAULT NULL,
            meta JSONB DEFAULT '{"flag": "🏴‍☠️"}'::jsonb,
            stats JSONB DEFAULT '{"hull": 100, "cannons": 2, "speed": 10}'::jsonb,
            cargo JSONB DEFAULT '{"wood": 0, "iron": 0, "watermelons": 0}'::jsonb,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS capybaras (
            id SERIAL PRIMARY KEY,
            owner_id BIGINT REFERENCES users(tg_id) ON DELETE CASCADE,
            name TEXT NOT NULL DEFAULT 'Безіменна булочка',
            
            -- CORE STATS
            lvl INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            hp INTEGER DEFAULT 3,
            atk INTEGER DEFAULT 1,
            def INTEGER DEFAULT 0,
            agi INTEGER DEFAULT 1,
            luck INTEGER DEFAULT 0,
            stamina INTEGER DEFAULT 100,
            hunger INTEGER DEFAULT 3,
            weight FLOAT DEFAULT 20.0,
            cleanness INTEGER DEFAULT 3,
            
            -- WORLD & MAP
            navigation JSONB DEFAULT '{
                "x": 2, "y": 1, 
                "discovered": [], 
                "trees": {}, 
                "flowers": {}
            }'::jsonb,
            
            -- INVENTORY & GEAR
            inventory JSONB DEFAULT '{
                "food": {}, "materials": {}, "loot": {}, "potions": {}, "maps": {}
            }'::jsonb,
            equipment JSONB DEFAULT '{
                "weapon": {"name": "Лапки", "lvl": 0}, 
                "armor": "Хутро", 
                "artifact": null
            }'::jsonb,
            
            -- PROGRESS & SOCIAL
            achievements TEXT[] DEFAULT '{}',
            unlocked_titles TEXT[] DEFAULT '{ "Новачок" }',
            stats_track JSONB DEFAULT '{}'::jsonb,
            fishing_stats JSONB DEFAULT '{"max_weight": 0, "total_weight": 0}'::jsonb,
            
            -- TIME & STATE
            state JSONB DEFAULT '{
                "status": "active", "mode": "capy", "mood": "Normal"
            }'::jsonb,
            cooldowns JSONB DEFAULT '{}'::jsonb,
            last_feed TIMESTAMP,
            last_wash TIMESTAMP
        )
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
        VALUES ('environment', '{"weather": "clear", "time_of_day": "zenith", "cycle_count": 1, "is_eclipse": false}')
        ON CONFLICT (key) DO NOTHING
    ''')
    
    await conn.close()