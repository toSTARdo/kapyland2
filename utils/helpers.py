import math
from datetime import datetime

def calculate_lvl_data(current_exp, added_exp):
    new_exp = current_exp + added_exp
    new_lvl = max(1, int(math.sqrt(new_exp / 2)))
    return new_exp, new_lvl

def calculate_winrate(wins, total_fights):
    return round(wins/total_fights, 1) * 100

def format_time(td):
    hours, remainder = divmod(td.total_seconds(), 3600)
    minutes = remainder // 60
    res = []
    if hours > 0:
        res.append(f"{int(hours)} год")
    if minutes > 0 or not res:
        res.append(f"{int(minutes)} хв")
    return " ".join(res)

def check_daily_limit(meta, action_key):
    today = datetime.now().strftime("%Y-%m-%d")
    last_action_date = meta.get("cooldowns", {}).get(action_key)
    
    if last_action_date == today:
        return False, today
    
    if "cooldowns" not in meta:
        meta["cooldowns"] = {}
    meta["cooldowns"][action_key] = today
    return True, today