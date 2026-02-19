from database.postgres_db import get_db_connection
from utils.helpers import calculate_lvl_data
from datetime import datetime, timezone, timedelta
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
            SELECT 
                u.username, u.reincarnation_count, 
                c.name, c.lvl, c.exp, c.meta,
                c.zen, c.karma, c.wins, c.total_fights
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
        multiplier = row.get('reincarnation_multiplier', 1.0)

        last_feed_str = meta.get("last_feed")
        if last_feed_str:
            last_feed = datetime.datetime.fromisoformat(last_feed_str)
            if datetime.datetime.now() - last_feed < datetime.timedelta(hours=8):
                remaining = datetime.timedelta(hours=8) - (datetime.datetime.now() - last_feed)
                return {"status": "cooldown", "remaining": remaining}

        actual_gain = round((weight_gain * multiplier) * 2) / 2
        exp_gain = int(actual_gain)
        
        meta["hunger"] = min(meta.get("hunger", 0) + 1, 3)
        meta["last_feed"] = datetime.datetime.now().isoformat()
        
        await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", 
                           json.dumps(meta, ensure_ascii=False), tg_id)

        res = await grant_exp_and_lvl(tg_id, exp_gain=exp_gain, weight_gain=actual_gain)

        return {
            "status": "success", 
            "gain": actual_gain, 
            "exp_gain": exp_gain,
            "lvl": res["new_lvl"],
            "lvl_up": res["lvl_up"],
            "total_weight": res["new_weight"],
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
from datetime import datetime, timezone, timedelta

async def sleep_db_operation(tg_id: int):
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", tg_id)
        if not row: return "no_capy", None
        
        meta = row['meta'] if isinstance(row['meta'], dict) else json.loads(row['meta'])
        
        if meta.get("status") == "sleep":
            return "already_sleeping", meta.get("wake_up")

        now = datetime.now(timezone.utc)
        wake_up_time = now + timedelta(hours=2)
        
        meta["status"] = "sleep"
        meta["sleep_start"] = now.isoformat()
        meta["wake_up"] = wake_up_time.isoformat()
        
        await conn.execute(
            "UPDATE capybaras SET meta = $1 WHERE owner_id = $2", 
            json.dumps(meta, ensure_ascii=False), tg_id
        )
        return "success", None
    finally: await conn.close()

async def wakeup_db_operation(tg_id: int):
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", tg_id)
        if not row: return "error", 0
        
        meta = row['meta'] if isinstance(row['meta'], dict) else json.loads(row['meta'])
        
        if meta.get("status") != "sleep":
            return "not_sleeping", 0

        start_time = datetime.fromisoformat(meta["sleep_start"])
        now = datetime.now(timezone.utc)

        start_time = datetime.fromisoformat(meta["sleep_start"])

        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)

        duration_seconds = max(0, (now - start_time).total_seconds())
        
        duration_seconds = max(0, (now - start_time).total_seconds())
        duration_minutes = duration_seconds / 60
        
        recovery_rate = 100 / 120 
        
        current_stamina = meta.get("stamina", 0)
        gained_stamina = int(duration_minutes * recovery_rate)
        
        new_stamina = min(100, current_stamina + gained_stamina)
        
        actual_gain = new_stamina - current_stamina

        meta["status"] = "active"
        meta["stamina"] = new_stamina
        meta.pop("sleep_start", None)
        meta.pop("wake_up", None)

        await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(meta, ensure_ascii=False), tg_id)
        return "success", actual_gain
    finally: await conn.close()

async def grant_exp_and_lvl(tg_id: int, exp_gain: int, weight_gain: float = 0, bot=None):
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow(
            "SELECT exp, lvl, zen, meta FROM capybaras WHERE owner_id = $1", 
            tg_id
        )
        if not row: return None

        old_lvl = row['lvl'] or 1
        current_exp = row['exp'] or 0
        current_zen = row['zen'] or 0
        meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']

        new_total_exp, new_lvl = calculate_lvl_data(current_exp, exp_gain)
        
        lvl_diff = new_lvl - old_lvl
        new_zen = current_zen + max(0, lvl_diff)

        if weight_gain != 0:
            current_weight = meta.get("weight", 20.0)
            meta["weight"] = round(max(1.0, current_weight + weight_gain), 1)

        await conn.execute('''
            UPDATE capybaras 
            SET exp = $1, lvl = $2, zen = $3, meta = $4
            WHERE owner_id = $5
        ''', new_total_exp, new_lvl, new_zen, json.dumps(meta, ensure_ascii=False), tg_id)

        if lvl_diff > 0 and bot:
            try:
                await bot.send_message(
                    tg_id, 
                    f"🎊 <b>LEVEL UP!</b>\n"
                    f"Твоя капібара досягла <b>{new_lvl} рівня</b>!\n"
                    f"Отримано Zen-очок: <b>+{lvl_diff}</b> 💠\n\n"
                    f"<i>Поточний запас Zen: {new_zen}</i>",
                    parse_mode="HTML"
                )
            except: pass

        return {
            "new_lvl": new_lvl,
            "lvl_up": lvl_diff > 0,
            "added_zen": lvl_diff,
            "total_zen": new_zen,
            "new_weight": meta.get("weight")
        }
    finally:
        await conn.close()