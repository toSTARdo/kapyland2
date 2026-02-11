from database.postgres_db import get_db_connection
import datetime

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
            SELECT u.username, u.reincarnation_count, c.name, c.lvl, c.exp, c.energy, c.meta 
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
            SELECT c.meta, u.reincarnation_multiplier 
            FROM capybaras c 
            JOIN users u ON c.owner_id = u.tg_id 
            WHERE c.owner_id = $1
        ''', tg_id)
        
        if not row: return "no_capy"

        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
        multiplier = row['reincarnation_multiplier']

        last_feed_str = meta.get("last_feed")
        if last_feed_str:
            last_feed = datetime.datetime.fromisoformat(last_feed_str)
            if datetime.datetime.now() - last_feed < datetime.timedelta(hours=8):
                remaining = datetime.timedelta(hours=8) - (datetime.datetime.now() - last_feed)
                return {"status": "cooldown", "remaining": remaining}

        actual_gain = round((weight_gain * multiplier) * 2) / 2
        
        new_weight = meta.get("weight", 20.0) + actual_gain
        new_hunger = min(meta.get("hunger", 0) + 1, 3)
        
        meta["weight"] = round(new_weight, 1)
        meta["hunger"] = new_hunger
        meta["last_feed"] = datetime.datetime.now().isoformat()

        await conn.execute(
            "UPDATE capybaras SET meta = $1 WHERE owner_id = $2",
            json.dumps(meta), tg_id
        )
        
        return {"status": "success", "gain": actual_gain, "total": new_weight, "hunger": new_hunger}
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