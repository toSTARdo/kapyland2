import random

class CombatEngine:
    @staticmethod
    def resolve_turn(attacker_name: str, defender_name: str):
        success = random.choice([True, False])
        if success:
            damage = 1
            return f"⚔️ <b>{attacker_name}</b> влучив у <b>{defender_name}</b> і завдав {damage} шкоди!", damage
        else:
            return f"🛡 <b>{attacker_name}</b> промахнувся по <b>{defender_name}</b>!", 0

