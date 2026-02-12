from database.postgres_db import get_db_connection
from utils.helpers import calculate_lvl_data
import datetime
import json

async def get_user_inventory(tg_id: int):
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", tg_id)
        return row['meta'] if row else None
    finally:
        await conn.close()

async def get_user_profile(tg_id: int):
    conn = await get_db_connection()
    try:
        query = '''
            SELECT u.username, u.reincarnation_count, c.name, c.lvl, c.exp, c.meta 
            FROM users u 
            JOIN capybaras c ON u.tg_id = c.owner_id 
            WHERE u.tg_id = $1
        '''
        return await conn.fetchrow(query, tg_id)
    finally:
        await conn.close()

async def feed_capybara_logic(tg_id: int, weight_gain: float):
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow('''
            SELECT c.meta, c.exp, u.reincarnation_multiplier 
            FROM capybaras c 
            JOIN users u ON c.owner_id = u.tg_id 
            WHERE c.owner_id = $1
        ''', tg_id)
        
        if not row: return "no_capy"

        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        multiplier = row['reincarnation_multiplier']
        current_exp = row['exp'] or 0

        last_feed_str = meta.get("last_feed")
        if last_feed_str:
            last_feed = datetime.datetime.fromisoformat(last_feed_str)
            if datetime.datetime.now() - last_feed < datetime.timedelta(hours=8):
                remaining = datetime.timedelta(hours=8) - (datetime.datetime.now() - last_feed)
                return {"status": "cooldown", "remaining": remaining}

        actual_gain = round((weight_gain * multiplier) * 2) / 2
        exp_gain = int(actual_gain)
        
        new_total_exp, new_lvl = calculate_lvl_data(current_exp, exp_gain)

        meta["weight"] = round(meta.get("weight", 20.0) + actual_gain, 1)
        meta["hunger"] = min(meta.get("hunger", 0) + 1, 3)
        meta["last_feed"] = datetime.datetime.now().isoformat()

        await conn.execute('''
            UPDATE capybaras 
            SET meta = $1, exp = $2, lvl = $3 
            WHERE owner_id = $4
        ''', json.dumps(meta, ensure_ascii=False), new_total_exp, new_lvl, tg_id)
        
        return {
            "status": "success", 
            "gain": actual_gain, 
            "exp_gain": exp_gain,
            "lvl": new_lvl,
            "total_weight": meta["weight"],
            "hunger": meta["hunger"] 
        }
    finally:
        await conn.close()

def calculate_dynamic_stats(meta):
    now = datetime.datetime.now()
    hp = meta.get("stats", {}).get("hp", 3)
    
    val = meta.get("last_feed")
    if val and isinstance(val, str):
        last_feed = datetime.datetime.fromisoformat(val)
    else:
        last_feed = now
    days_since_feed = (now - last_feed).total_seconds() / 86400 
    
    hunger_loss = int(days_since_feed // 1)
    meta["hunger"] = max(0, 3 - hunger_loss)
    
    if hunger_loss > 3:
        starving_days = hunger_loss - 3
        hp -= starving_days

    val = meta.get("last_wash")
    if val and isinstance(val, str):
        last_wash = datetime.datetime.fromisoformat(val)
    else:
        last_wash = now
    days_since_wash = (now - last_wash).total_seconds() / 86400
    
    wash_loss = int(days_since_wash // 1)
    meta["cleanness"] = max(0, 3 - wash_loss)
    
    if wash_loss > 3:
        dirty_days = wash_loss - 3
        hp -= dirty_days

    meta["stats"]["hp"] = max(0, int(hp))
    
    if meta["stats"]["hp"] < 3:
        if meta["cleanness"] == 0:
            meta["mood"] = "Sick"
        elif meta["hunger"] == 0:
            meta["mood"] = "Weak"
    else:
        meta.pop("mood", None)

    return meta

async def wash_db_operation(tg_id: int):
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta, exp FROM capybaras WHERE owner_id = $1", tg_id)
        if not row: return "no_capy", None
        
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        
        last_wash_str = meta.get("last_wash")
        if last_wash_str:
            last_wash = datetime.datetime.fromisoformat(last_wash_str)
            diff = datetime.datetime.now() - last_wash
            if diff < datetime.timedelta(hours=12):
                remaining = datetime.timedelta(hours=12) - diff
                return "cooldown", remaining

        exp_gain = 1
        new_exp, new_lvl = calculate_lvl_data(row['exp'], exp_gain)

        meta["cleanness"] = 3
        meta["last_wash"] = datetime.datetime.now().isoformat()
        
        await conn.execute('''
            UPDATE capybaras SET meta = $1, exp = $2, lvl = $3 WHERE owner_id = $4
        ''', json.dumps(meta), new_exp, new_lvl, tg_id)
        
        return "success", {"exp_gain": exp_gain, "lvl": new_lvl}
    finally:
        await conn.close()

async def sleep_db_operation(tg_id: int):
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", tg_id)
        if not row: return "no_capy", None
        
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        
        wake_up_time = datetime.datetime.now() + datetime.timedelta(hours=2)
        meta["status"] = "sleep"
        meta["wake_up"] = wake_up_time.isoformat()
        meta["stamina"] = 100
        
        await conn.execute(
            "UPDATE capybaras SET meta = $1 WHERE owner_id = $2", 
            json.dumps(meta, ensure_ascii=False), tg_id
        )
        return "success", None
    finally:
        await conn.close()