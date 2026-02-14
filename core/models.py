from aiogram import html
import random
from config import UNITS_PER_HEART, BASE_HEARTS, BASE_HIT_CHANCE, STAT_WEIGHTS, BASE_BLOCK_CHANCE
from data.special_abilities import *

class Fighter:
    def __init__(self, capy, config_data, color="🔸"):
        self.name = capy.get("kapy_name", "Капібара")
        self.weight = capy.get("weight", 20.0)
        self.color = color
        
        stats = capy.get("stats", {})
        self.atk = stats.get("attack", 0)
        self.def_ = stats.get("defense", 0)
        self.agi = stats.get("agility", 0)
        self.luck = stats.get("luck", 0)

        self.w_name = capy.get("equipped_weapon", "Лапки")
        self.a_name = capy.get("equipped_armor", "")
        
        self.weapon_data = config_data["WEAPONS"].get(self.w_name, {
            "texts": ["вдаряє лапками {defen}"], "hit_bonus": 0, "power": 1
        })
        self.armor_data = config_data["ARMOR"].get(self.a_name, {
            "text": "отримала удар", "defense": 0
        })

        extra_heart = 2 if "Котяче життя" in capy.get("artifacts", []) else 0
        self.max_hp = (BASE_HEARTS * UNITS_PER_HEART) + extra_heart
        self.hp = self.max_hp

    def get_hp_display(self) -> str:
        display = ""
        temp_hp = self.hp
        total_hearts = self.max_hp // UNITS_PER_HEART
        
        for _ in range(total_hearts):
            if temp_hp >= 2:
                display += "❤️"
                temp_hp -= 2
            elif temp_hp == 1:
                display += "💔"
                temp_hp -= 1
            else:
                display += "🖤"
        return f"{display} ({self.hp}/{self.max_hp})"

    def get_hit_chance(self):
        weight_penalty = max(0, (self.weight - 20) / 5) * 0.01
        chance = BASE_HIT_CHANCE + (self.atk * STAT_WEIGHTS["atk_to_hit"]) + self.weapon_data.get("hit_bonus", 0)
        return chance - weight_penalty

    def get_dodge_chance(self):
        return self.agi * STAT_WEIGHTS["agi_to_dodge"]

    def get_block_chance(self):
        return BASE_BLOCK_CHANCE + (self.def_ * STAT_WEIGHTS["def_to_block"]) + self.armor_data.get("defense", 0)

class CombatEngine:
    @staticmethod
    def resolve_turn(att: Fighter, defe: Fighter):
        if random.random() > att.get_hit_chance():
            return f"💨 {att.color} {html.bold(att.name)} промахнувся!"

        if random.random() < defe.get_dodge_chance():
            return f"⚡ {html.bold(defe.name)} спритно ухилився від атаки!"

        if random.random() < defe.get_block_chance():
            armor_msg = defe.armor_data.get("text", "заблокував удар")
            return f"🔰 {html.bold(defe.name)} {armor_msg}!"

        base_damage = att.weapon_data.get("power", 1)
        crit_bonus = 0
        crit_text = ""
        
        if random.random() < (att.luck * STAT_WEIGHTS["luck_to_crit"]):
            crit_bonus = 1
            crit_text = "💥 "

        ability_damage = 0
        special_msg = ""
        special_key = att.weapon_data.get("special")
        
        if special_key in ABILITY_REGISTRY:
            result = ABILITY_REGISTRY[special_key](att, defe)
            
            if isinstance(result, (int, float)):
                ability_damage = int(result)
            
            if result:
                json_special_text = att.weapon_data.get("special_text", "")
                if json_special_text:
                    special_msg = f"\n{json_special_text}"

        total_damage = base_damage + crit_bonus + ability_damage
        defe.hp = max(0, defe.hp - total_damage)
        
        raw_text = random.choice(att.weapon_data["texts"])
        attack_verb = raw_text.replace("{defen}", html.bold(defe.name))
        
        return (f"{crit_text}{att.color} {html.bold(att.name)} {attack_verb}!\n"
                f"➔ Шкода: {html.bold('-' + str(total_damage) + ' HP')}"
                f"{special_msg}")