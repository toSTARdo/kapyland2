import math

def calculate_lvl_data(current_exp, added_exp):
    new_exp = current_exp + added_exp
    new_lvl = max(1, int(math.sqrt(new_exp / 2)))
    return new_exp, new_lvl

def format_time(td):
    hours, remainder = divmod(td.total_seconds(), 3600)
    minutes = remainder // 60
    res = []
    if hours > 0:
        res.append(f"{int(hours)} год")
    if minutes > 0 or not res:
        res.append(f"{int(minutes)} хв")
    return " ".join(res)