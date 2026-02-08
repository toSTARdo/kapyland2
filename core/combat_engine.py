from aiogram import html

class CombatEngine:
    @staticmethod
    def resolve_turn(attacker, defender):
        log_text, damage = attacker.attack(defender)
        
        report = (
            f"{log_text}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"{attacker.color} {html.bold(attacker.name)}: {attacker.get_hp_display()}\n"
            f"{defender.color} {html.bold(defender.name)}: {defender.get_hp_display()}"
        )
        
        return report, damage