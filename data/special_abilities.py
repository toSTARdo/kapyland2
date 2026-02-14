import random
from aiogram import html

def weapon_ability(base_prob):
    def decorator(func_list):
        def wrapper(att, targets, round_num):
            w_data = att.weapon_data
            rarity = w_data.get("rarity", "common")
            lvl = getattr(att, 'weapon_lvl', 0)
            pattern = w_data.get("pattern", "sequential")
            is_aoe = w_data.get("is_aoe", False)

            lvl_bonus = lvl * 0.05
            luck_bonus = att.luck * 0.02
            if random.random() > (base_prob + luck_bonus + lvl_bonus):
                return 0, False

            if rarity == "common": limit = 1
            elif rarity == "rare": limit = 2
            elif rarity == "epic": limit = 3 + (1 if lvl >= 1 else 0)
            elif rarity == "legendary": limit = 4 + (2 if lvl >= 1 else 0)
            else: limit = 1

            available = func_list[:limit]
            total_dmg = 0
            
            if not isinstance(targets, list):
                targets = [targets]

            if pattern == "sequential":
                idx = (round_num - 1) % len(available)
                action = available[idx]
                for t in (targets if is_aoe else [random.choice(targets)]):
                    res = action(att, t)
                    total_dmg += res if isinstance(res, int) else 0

            elif pattern == "simultaneous":
                for action in available:
                    for t in (targets if is_aoe else [random.choice(targets)]):
                        res = action(att, t)
                        total_dmg += res if isinstance(res, int) else 0
            
            return total_dmg, True
        return wrapper
    return decorator

#COMMON
hook_snag = weapon_ability(0.20)([
    lambda a, d: setattr(d, 'agi', max(0, d.agi - 1)) or 0,
    lambda a, d: setattr(a, 'agi', a.agi + 1) or 0
])

wooden_leg = weapon_ability(0.18)([
    lambda a, d: setattr(d, 'atk', max(0, d.atk - 2)) or 0
])

heavy_swing = weapon_ability(0.25)([
    lambda a, d: 0.5
])

mop_wash = weapon_ability(0.22)([
    lambda a, d: setattr(d, 'luck', max(0, d.luck - 3)) or 0
])

yorshik_scrub = weapon_ability(0.25)([
    lambda a, d: setattr(d, 'def_', max(0, d.def_ - 1)) or 0
])

#RARE
entangle_debuff = weapon_ability(1.0)([
    lambda a, d: setattr(d, 'agi', max(0, d.agi - 2)) or 0,
    lambda a, d: setattr(d, 'atk', max(0, d.atk - 1)) or 0
])

drunk_fury = weapon_ability(1.0)([
    lambda a, d: setattr(a, 'atk', a.atk + 2) or 0,
    lambda a, d: setattr(a, 'def_', max(0, a.def_ - 2)) or 0
])

bleed_chance = weapon_ability(0.35)([
    lambda a, d: setattr(a, 'luck', a.luck + 1) or 0,
    lambda a, d: 0.5
])

precision_strike = weapon_ability(0.40)([
    lambda a, d: setattr(d, 'def_', max(0, d.def_ - 2)) or 0,
    lambda a, d: setattr(a, 'luck', a.luck + 2) or 0
])

parry = weapon_ability(1.0)([
    lambda a, d: setattr(a, 'def_', a.def_ + 2) or 0,
    lambda a, d: setattr(a, 'agi', a.agi + 1) or 0
])

curse_mark = weapon_ability(1.0)([
    lambda a, d: setattr(d, 'luck', 0) or 0,
    lambda a, d: setattr(d, 'def_', max(0, d.def_ - 1)) or 0
])

cannon_splash = weapon_ability(0.30)([
    lambda a, d: 1,
    lambda a, d: setattr(d, 'agi', max(0, d.agi - 1)) or 0
])

#EPIC
life_steal = weapon_ability(0.40)([
    lambda a, d: setattr(a, 'hp', min(a.max_hp, a.hp + 2)) or 0,
    lambda a, d: setattr(d, 'atk', max(0, d.atk - 1)) or 0,
    lambda a, d: setattr(a, 'luck', a.luck + 1) or 0,
    lambda a, d: 1
])

confuse_hit = weapon_ability(0.35)([
    lambda a, d: 1,
    lambda a, d: setattr(d, 'luck', max(0, d.luck - 3)) or 0,
    lambda a, d: setattr(a, 'agi', a.agi + 1) or 0,
    lambda a, d: setattr(d, 'def_', max(0, d.def_ - 2)) or 0
])

freeze_debuff = weapon_ability(1.0)([
    lambda a, d: setattr(d, 'agi', max(0, d.agi - 4)) or 0,
    lambda a, d: setattr(d, 'def_', max(0, d.def_ - 1)) or 0,
    lambda a, d: setattr(a, 'def_', a.def_ + 1) or 0,
    lambda a, d: setattr(d, 'atk', max(0, d.atk - 2)) or 0
])

fear_debuff = weapon_ability(1.0)([
    lambda a, d: setattr(d, 'atk', max(0, d.atk - 3)) or 0,
    lambda a, d: setattr(d, 'luck', max(0, d.luck - 2)) or 0,
    lambda a, d: setattr(a, 'atk', a.atk + 1) or 0,
    lambda a, d: setattr(d, 'agi', max(0, d.agi - 2)) or 0
])

energy_surge = weapon_ability(1.0)([
    lambda a, d: setattr(a, 'agi', a.agi + 4) or 0,
    lambda a, d: setattr(a, 'luck', a.luck + 2) or 0,
    lambda a, d: setattr(a, 'atk', a.atk + 1) or 0,
    lambda a, d: (setattr(a, 'hp', max(1, a.hp - 1)) or 3)
])

owl_crit = weapon_ability(0.45)([
    lambda a, d: 2,
    lambda a, d: setattr(d, 'def_', max(0, d.def_ - 2)) or 0,
    lambda a, d: setattr(a, 'agi', a.agi + 2) or 0,
    lambda a, d: setattr(a, 'luck', a.luck + 5) or 0
])

auto_attack = weapon_ability(1.0)([
    lambda a, d: setattr(a, 'atk', a.atk + 2) or 0,
    lambda a, d: setattr(d, 'def_', max(0, d.def_ - 2)) or 0,
    lambda a, d: setattr(a, 'def_', a.def_ + 2) or 0,
    lambda a, d: 2
])

rage_boost = weapon_ability(1.0)([
    lambda a, d: setattr(a, 'atk', a.atk + 2) or 0,
    lambda a, d: setattr(a, 'luck', a.luck + 1) or 0,
    lambda a, d: setattr(d, 'atk', max(0, d.atk - 1)) or 0,
    lambda a, d: setattr(a, 'def_', a.def_ + 2) or 0
])

ghost_strike = weapon_ability(0.35)([
    lambda a, d: 1,
    lambda a, d: setattr(a, 'agi', a.agi + 3) or 0,
    lambda a, d: setattr(d, 'luck', 0) or 0,
    lambda a, d: setattr(a, 'hp', min(a.max_hp, a.hp + 2)) or 0
])

crit_5 = weapon_ability(0.55)([
    lambda a, d: 4,
    lambda a, d: setattr(a, 'luck', a.luck + 3) or 0,
    lambda a, d: setattr(d, 'agi', max(0, d.agi - 2)) or 0,
    lambda a, d: setattr(a, 'atk', a.atk + 2) or 0
])

#LEGENDARY
cat_life = weapon_ability(0.40)([
    lambda a, d: setattr(a, 'hp', min(a.max_hp, a.hp + 2)) or 0,
    lambda a, d: setattr(a, 'agi', a.agi + 2) or 0,
    lambda a, d: setattr(a, 'luck', a.luck + 2) or 0,
    lambda a, d: setattr(d, 'luck', max(0, d.luck - 2)) or 0,
    lambda a, d: setattr(d, 'agi', max(0, d.agi - 3)) or 0,
    lambda a, d: setattr(a, 'atk', a.atk + 2) or 0
])

tea_mastery = weapon_ability(1.0)([
    lambda a, d: setattr(a, 'def_', a.def_ + 2) or 0,
    lambda a, d: setattr(a, 'hp', min(a.max_hp, a.hp + 2)) or 0,
    lambda a, d: setattr(a, 'luck', a.luck + 3) or 0,
    lambda a, d: setattr(d, 'atk', max(0, d.atk - 2)) or 0,
    lambda a, d: setattr(d, 'luck', 0) or 0,
    lambda a, d: setattr(a, 'agi', a.agi + 2) or 0
])

double_strike = weapon_ability(0.35)([
    lambda a, d: 2,
    lambda a, d: setattr(a, 'atk', a.atk + 1) or 0,
    lambda a, d: setattr(a, 'agi', a.agi + 2) or 0,
    lambda a, d: setattr(d, 'def_', max(0, d.def_ - 1)) or 0,
    lambda a, d: 2,
    lambda a, d: setattr(d, 'agi', 0) or 0
])

crit_20 = weapon_ability(0.20)([
    lambda a, d: setattr(a, 'luck', a.luck + 5) or 0,
    lambda a, d: setattr(a, 'atk', a.atk + 5) or 0,
    lambda a, d: setattr(a, 'def_', a.def_ + 5) or 0,
    lambda a, d: 99,
    lambda a, d: setattr(a, 'hp', a.max_hp) or 0,
    lambda a, d: setattr(d, 'luck', 0) or 0
])

pierce_armor = weapon_ability(1.0)([
    lambda a, d: setattr(d, 'def_', 0) or 0,
    lambda a, d: 2,
    lambda a, d: setattr(a, 'atk', a.atk + 2) or 0,
    lambda a, d: setattr(a, 'luck', a.luck + 1) or 0,
    lambda a, d: setattr(d, 'atk', max(0, d.atk - 3)) or 0,
    lambda a, d: setattr(d, 'agi', max(0, d.agi - 2)) or 0
])

heavy_weight = weapon_ability(1.0)([
    lambda a, d: setattr(a, 'agi', max(0, a.agi - 2)) or 0,
    lambda a, d: setattr(a, 'atk', a.atk + 5) or 0,
    lambda a, d: setattr(a, 'def_', a.def_ + 4) or 0,
    lambda a, d: setattr(d, 'def_', max(0, d.def_ - 3)) or 0,
    lambda a, d: 3,
    lambda a, d: setattr(a, 'luck', a.luck + 4) or 0
])

range_attack = weapon_ability(1.0)([
    lambda a, d: setattr(a, 'luck', a.luck + 3) or 0,
    lambda a, d: setattr(a, 'agi', a.agi + 3) or 0,
    lambda a, d: setattr(d, 'agi', max(0, d.agi - 2)) or 0,
    lambda a, d: setattr(d, 'atk', max(0, d.atk - 1)) or 0,
    lambda a, d: setattr(a, 'atk', a.atk + 3) or 0,
    lambda a, d: setattr(d, 'def_', max(0, d.def_ - 2)) or 0
])

stun_chance = weapon_ability(0.40)([
    lambda a, d: setattr(d, 'agi', 0) or 0,
    lambda a, d: setattr(d, 'atk', max(0, d.atk - 4)) or 0,
    lambda a, d: setattr(d, 'def_', max(0, d.def_ - 2)) or 0,
    lambda a, d: setattr(a, 'luck', a.luck + 2) or 0,
    lambda a, d: 2,
    lambda a, d: setattr(a, 'def_', a.def_ + 3) or 0
])

latex_choke = weapon_ability(0.60)([
    lambda a, d: setattr(d, 'atk', max(0, d.atk - 4)) or 0,
    lambda a, d: setattr(d, 'agi', max(0, d.agi - 4)) or 0,
    lambda a, d: setattr(d, 'luck', 0) or 0,
    lambda a, d: setattr(a, 'luck', a.luck + 4) or 0,
    lambda a, d: setattr(d, 'def_', 0) or 0,
    lambda a, d: 2
])

ABILITY_REGISTRY = {
    "none": lambda a, t, r: (0, False),
    "hook_snag": hook_snag,
    "wooden_leg": wooden_leg,
    "heavy_swing": heavy_swing,
    "mop_wash": mop_wash,
    "yorshik_scrub": yorshik_scrub,
    "entangle_debuff": entangle_debuff,
    "drunk_fury": drunk_fury,
    "bleed_chance": bleed_chance,
    "precision_strike": precision_strike,
    "parry": parry,
    "curse_mark": curse_mark,
    "cannon_splash": cannon_splash,
    "life_steal": life_steal,
    "confuse_hit": confuse_hit,
    "freeze_debuff": freeze_debuff,
    "fear_debuff": fear_debuff,
    "energy_surge": energy_surge,
    "owl_crit": owl_crit,
    "auto_attack": auto_attack,
    "rage_boost": rage_boost,
    "ghost_strike": ghost_strike,
    "crit_5": crit_5,
    "cat_life": cat_life,
    "tea_mastery": tea_mastery,
    "double_strike": double_strike,
    "crit_20": crit_20,
    "pierce_armor": pierce_armor,
    "heavy_weight": heavy_weight,
    "range_attack": range_attack,
    "stun_chance": stun_chance,
    "latex_choke": latex_choke
}