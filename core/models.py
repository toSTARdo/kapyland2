import random
from aiogram import html
#=======================#
from config import UNITS_PER_HEART, BASE_HEARTS, BASE_HIT_CHANCE

class Fighter:
    def __init__(self, name: str, weight: float, color: str = "🔸"):
        self.name = name
        self.weight = weight
        self.color = color
        self.max_hp = BASE_HEARTS * UNITS_PER_HEART
        self.hp = self.max_hp

    def get_hp_display(self) -> str:
        """
        Visualisation of HP:
        2 HP -> ❤️ (WHOLE)
        1 HP -> 💔 (DAMAGED)
        0 HP -> 🖤 (DESTROYED)
        """
        display = ""
        temporary_hp = self.hp
        
        for _ in range(BASE_HEARTS):
            if temporary_hp >= 2:
                display += "❤️"
                temporary_hp -= 2
            elif temporary_hp == 1:
                display += "💔"
                temporary_hp -= 1
            else:
                display += "🖤"
        
        return f"{display} ({self.hp}/{self.max_hp} HP)"

    def attack(self, target: 'Fighter') -> tuple[str, int]:
        if random.random() < BASE_HIT_CHANCE:
            damage = 1
            target.hp = max(0, target.hp - damage)
            return f"⚔️ {self.color} {html.bold(self.name)} влучив! (–1 HP)", damage
        
        return f"💨 {self.color} {html.bold(self.name)} промахнувся!", 0