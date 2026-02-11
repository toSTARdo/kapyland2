import random
from aiogram import html

def effect_chance(base_prob):
    def decorator(func):
        def wrapper(att, defe):
            lvl_bonus = getattr(att, 'weapon_lvl', 0) * 0.05
            luck_bonus = att.luck * 0.02
            final_chance = max(0, min(0.98, base_prob + luck_bonus + lvl_bonus))
            
            if random.random() < final_chance:
                func(att, defe)
                return True
            return False
        return wrapper
    return decorator

#COMMON
@effect_chance(0.20)
def hook_snag(att, defe):
    defe.agi = max(0, defe.agi - 1)
    att.agi += 1 

@effect_chance(0.18)
def wooden_leg_effect(att, defe):
    defe.atk = max(0, defe.atk - 2)

@effect_chance(0.25)
def heavy_swing_effect(att, defe):
    defe.hp = max(0, defe.hp - 1)

@effect_chance(0.22)
def mop_wash_effect(att, defe):
    defe.luck = max(0, defe.luck - 3)

@effect_chance(0.25)
def yorshik_effect(att, defe):
    defe.def_ = max(0, defe.def_ - 1)

#RARE
@effect_chance(1.0) 
def entangle_effect(att, defe):
    defe.agi = max(0, defe.agi - 2) 
    defe.atk = max(0, defe.atk - 1) 

@effect_chance(1.0)
def drunk_fury_effect(att, defe):
    att.atk += 2
    att.def_ = max(0, att.def_ - 2)

@effect_chance(0.35)
def bleed_effect(att, defe):
    defe.hp = max(0, defe.hp - 2)
    att.luck += 1

@effect_chance(0.40)
def precision_strike_effect(att, defe):
    defe.def_ = max(0, defe.def_ - 2) 
    att.luck += 2 

@effect_chance(1.0)
def parry_effect(att, defe):
    att.def_ += 2
    att.agi += 1 

@effect_chance(1.0)
def curse_mark_effect(att, defe):
    defe.luck = 0  
    defe.def_ = max(0, defe.def_ - 1) 

@effect_chance(0.30)
def cannon_splash_effect(att, defe):
    defe.hp = max(0, defe.hp - 3)  
    defe.agi = max(0, defe.agi - 1) 

#EPIC
@effect_chance(0.40)
def life_steal_effect(att, defe):
    att.hp = min(att.max_hp, att.hp + 2)
    defe.atk = max(0, defe.atk - 1)
    att.luck += 1
    if getattr(att, 'weapon_lvl', 0) > 0:
        defe.hp = max(0, defe.hp - 1)

@effect_chance(0.35)
def confuse_hit_effect(att, defe):
    defe.hp = max(0, defe.hp - 2)
    defe.luck = max(0, defe.luck - 3)
    att.agi += 1
    if getattr(att, 'weapon_lvl', 0) > 0:
        defe.def_ = max(0, defe.def_ - 2)

@effect_chance(1.0)
def freeze_debuff_effect(att, defe):
    defe.agi = max(0, defe.agi - 4)
    defe.def_ = max(0, defe.def_ - 1)
    att.def_ += 1
    if getattr(att, 'weapon_lvl', 0) > 0:
        defe.atk = max(0, defe.atk - 2)

@effect_chance(1.0)
def fear_debuff_effect(att, defe):
    defe.atk = max(0, defe.atk - 3)
    defe.luck = max(0, defe.luck - 2)
    att.atk += 1
    if getattr(att, 'weapon_lvl', 0) > 0:
        defe.agi = max(0, defe.agi - 2)

@effect_chance(1.0)
def energy_surge_effect(att, defe):
    att.agi += 4
    att.luck += 2
    att.atk += 1
    if getattr(att, 'weapon_lvl', 0) > 0:
        att.hp = max(1, att.hp - 1)
        att.atk += 3

@effect_chance(0.45)
def owl_crit_effect(att, defe):
    defe.hp = max(0, defe.hp - 3)
    defe.def_ = max(0, defe.def_ - 2)
    att.agi += 2
    if getattr(att, 'weapon_lvl', 0) > 0:
        att.luck += 5

@effect_chance(1.0)
def auto_attack_effect(att, defe):
    att.atk += 2
    defe.def_ = max(0, defe.def_ - 2)
    att.def_ += 2
    if getattr(att, 'weapon_lvl', 0) > 0:
        defe.hp = max(0, defe.hp - 2)

@effect_chance(1.0)
def rage_boost_effect(att, defe):
    att.atk += 2
    att.luck += 1
    defe.atk = max(0, defe.atk - 1)
    if getattr(att, 'weapon_lvl', 0) > 0:
        att.def_ += 2

@effect_chance(0.35)
def ghost_strike_effect(att, defe):
    defe.hp = max(0, defe.hp - 2)
    att.agi += 3
    defe.luck = 0
    if getattr(att, 'weapon_lvl', 0) > 0:
        att.hp = min(att.max_hp, att.hp + 2)

@effect_chance(0.55)
def crit_5_effect(att, defe):
    defe.hp = max(0, defe.hp - 4)
    att.luck += 3
    defe.agi = max(0, defe.agi - 2)
    if getattr(att, 'weapon_lvl', 0) > 0:
        att.atk += 2

#LEGENDARY
@effect_chance(0.40)
def cat_life_effect(att, defe):
    att.hp = min(att.max_hp, att.hp + 2)
    att.agi += 2
    att.luck += 2
    defe.luck = max(0, defe.luck - 2)
    if getattr(att, 'weapon_lvl', 0) >= 1:
        defe.agi = max(0, defe.agi - 3)
    if getattr(att, 'weapon_lvl', 0) >= 2:
        att.atk += 2

@effect_chance(1.0)
def tea_mastery_effect(att, defe):
    att.def_ += 2
    att.hp = min(att.max_hp, att.hp + 2)
    att.luck += 3
    defe.atk = max(0, defe.atk - 2)
    if getattr(att, 'weapon_lvl', 0) >= 1:
        defe.luck = 0
    if getattr(att, 'weapon_lvl', 0) >= 2:
        att.agi += 2

@effect_chance(0.35)
def double_strike_effect(att, defe):
    defe.hp = max(0, defe.hp - 2)
    att.atk += 1
    att.agi += 2
    defe.def_ = max(0, defe.def_ - 1)
    if getattr(att, 'weapon_lvl', 0) >= 1:
        defe.hp = max(0, defe.hp - 2)
    if getattr(att, 'weapon_lvl', 0) >= 2:
        defe.agi = 0

@effect_chance(0.20)
def crit_20_effect(att, defe):
    defe.hp = 0
    att.luck += 5
    att.atk += 5
    att.def_ += 5
    if getattr(att, 'weapon_lvl', 0) >= 1:
        att.hp = att.max_hp
    if getattr(att, 'weapon_lvl', 0) >= 2:
        defe.luck = 0

@effect_chance(1.0)
def pierce_armor_effect(att, defe):
    defe.def_ = 0
    defe.hp = max(0, defe.hp - 2)
    att.atk += 2
    att.luck += 1
    if getattr(att, 'weapon_lvl', 0) >= 1:
        defe.atk = max(0, defe.atk - 3)
    if getattr(att, 'weapon_lvl', 0) >= 2:
        defe.agi = max(0, defe.agi - 2)

@effect_chance(1.0)
def heavy_weight_effect(att, defe):
    att.agi = max(0, att.agi - 2)
    att.atk += 5
    att.def_ += 4
    defe.def_ = max(0, defe.def_ - 3)
    if getattr(att, 'weapon_lvl', 0) >= 1:
        defe.hp = max(0, defe.hp - 3)
    if getattr(att, 'weapon_lvl', 0) >= 2:
        att.luck += 4

@effect_chance(1.0)
def range_attack_effect(att, defe):
    att.luck += 3
    att.agi += 3
    defe.agi = max(0, defe.agi - 2)
    defe.atk = max(0, defe.atk - 1)
    if getattr(att, 'weapon_lvl', 0) >= 1:
        att.atk += 3
    if getattr(att, 'weapon_lvl', 0) >= 2:
        defe.def_ = max(0, defe.def_ - 2)

@effect_chance(0.40)
def stun_chance_effect(att, defe):
    defe.agi = 0
    defe.atk = max(0, defe.atk - 4)
    defe.def_ = max(0, defe.def_ - 2)
    att.luck += 2
    if getattr(att, 'weapon_lvl', 0) >= 1:
        defe.hp = max(0, defe.hp - 3)
    if getattr(att, 'weapon_lvl', 0) >= 2:
        att.def_ += 3

@effect_chance(0.60)
def rubber_choke_effect(att, defe):
    defe.atk = max(0, defe.atk - 4)
    defe.agi = max(0, defe.agi - 4)
    defe.luck = 0
    att.luck += 4
    if getattr(att, 'weapon_lvl', 0) >= 1:
        defe.def_ = 0
    if getattr(att, 'weapon_lvl', 0) >= 2:
        defe.hp = max(0, defe.hp - 2)

ABILITY_REGISTRY = {
    "none": lambda a, d: False,
    "hook_snag": hook_snag,
    "wooden_leg": wooden_leg_effect,
    "heavy_swing": heavy_swing_effect,
    "mop_wash": mop_wash_effect,
    "yorshik_scrub": yorshik_effect,
    "entangle_debuff": entangle_effect,
    "drunk_fury": drunk_fury_effect,
    "bleed_chance": bleed_effect,
    "precision_strike": precision_strike_effect,
    "parry": parry_effect,
    "curse_mark": curse_mark_effect,
    "cannon_splash": cannon_splash_effect,
    "life_steal": life_steal_effect,
    "confuse_hit": confuse_hit_effect,
    "freeze_debuff": freeze_debuff_effect,
    "fear_debuff": fear_debuff_effect,
    "energy_surge": energy_surge_effect,
    "owl_crit": owl_crit_effect,
    "auto_attack": auto_attack_effect,
    "rage_boost": rage_boost_effect,
    "ghost_strike": ghost_strike_effect,
    "crit_5": crit_5_effect,
    "cat_life": cat_life_effect,
    "tea_mastery": tea_mastery_effect,
    "double_strike": double_strike_effect,
    "crit_20": crit_20_effect,
    "pierce_armor": pierce_armor_effect,
    "heavy_weight": heavy_weight_effect,
    "range_attack": range_attack_effect,
    "stun_chance": stun_chance_effect,
    "latex_choke": rubber_choke_effect
}