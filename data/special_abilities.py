import random
from aiogram import html

def weapon_ability(base_prob):
    def decorator(func_list):
        state = {'current_idx': 0} 
        def wrapper(att, targets, round_num):
            w_data = att.weapon_data
            rarity = w_data.get("rarity", "common")
            lvl = getattr(att, 'weapon_lvl', 0)
            pattern = w_data.get("pattern", "sequential")
            is_aoe = w_data.get("is_aoe", False)

            lvl_bonus = lvl * 0.05
            luck_bonus = att.luck * 0.02
            if random.random() > (base_prob + luck_bonus + lvl_bonus):
                return 0, False, []

            limit = {"common": 1, "rare": 2, "epic": 4, "legendary": 6}.get(rarity, 1)
            available = func_list[:limit]
            total_dmg, logs = 0, []
            if not isinstance(targets, list): targets = [targets]

            actions = [available[state['current_idx'] % len(available)]] if pattern == "sequential" else available
            if pattern == "sequential": state['current_idx'] += 1

            for action in actions:
                for t in (targets if is_aoe else [random.choice(targets)]):
                    res_val, res_text = action(att, t)
                    total_dmg += res_val if isinstance(res_val, (int, float)) else 0
                    logs.append(res_text)
            return total_dmg, True, logs
        return wrapper
    return decorator

#COMMON
hook_snag = weapon_ability(0.1)([
    lambda a, d: (setattr(d, 'agi', max(0, d.agi - 1)) or 0, "🪝 Гак зачепив ногу! -1 Спритність"),
    lambda a, d: (setattr(a, 'agi', a.agi + 1) or 0, "🏃 Ви вирвали ініціативу! +1 Спритність")
])
wooden_leg = weapon_ability(0.1)([
    lambda a, d: (setattr(d, 'atk', max(0, d.atk - 1)) or 0, "🪵 Глухий удар деревом! -1 Атаки")
])
heavy_swing = weapon_ability(0.1)([
    lambda a, d: (1, "🔨 Потужний замах! +1 Шкоди")
])
mop_wash = weapon_ability(0.1)([
    lambda a, d: (setattr(d, 'luck', max(0, d.luck - 2)) or 0, "🧼 Підлога намочена! -2 Удачі")
])
yorshik_scrub = weapon_ability(0.1)([
    lambda a, d: (setattr(d, 'def_', max(0, d.def_ - 1)) or 0, "🧽 Чистка захисту! -1 Захисту")
])

#RARE
entangle_debuff = weapon_ability(0.15)([
    lambda a, d: (setattr(d, 'agi', max(0, d.agi - 2)) or 0, "🕸 Ворог заплутався! -2 Спритність"),
    lambda a, d: (setattr(d, 'atk', max(0, d.atk - 1)) or 0, "⛓ Пута тиснуть! -1 Атаки")
])
drunk_fury = weapon_ability(0.15)([
    lambda a, d: (setattr(a, 'atk', a.atk + 1.5) or 0, "🍺 П'яна відвага! +1.5 Атаки"),
    lambda a, d: (setattr(a, 'def_', max(0, a.def_ - 1)) or 0, "🥴 Хитає... -1 Захисту")
])
bleed_chance = weapon_ability(0.15)([
    lambda a, d: (setattr(a, 'luck', a.luck + 1) or 0, "🩸 Запах крові! +1 Удача"),
    lambda a, d: (1, "🔪 Глибокий поріз! +1 Шкоди")
])
precision_strike = weapon_ability(0.15)([
    lambda a, d: (setattr(d, 'def_', max(0, d.def_ - 1.5)) or 0, "🎯 Точний удар в стик! -1.5 Захисту"),
    lambda a, d: (setattr(a, 'luck', a.luck + 1) or 0, "👁 Фокус! +1 Удача")
])
parry = weapon_ability(0.2)([
    lambda a, d: (setattr(a, 'def_', a.def_ + 1) or 0, "🛡 Контрудар! +1 Захисту"),
    lambda a, d: (setattr(a, 'agi', a.agi + 1) or 0, "💨 Технічне зміщення! +1 Спритність")
])
curse_mark = weapon_ability(0.15)([
    lambda a, d: (setattr(d, 'luck', 0) or 0, "💀 Чорна мітка! Удача ворога = 0"),
    lambda a, d: (setattr(d, 'def_', max(0, d.def_ - 1)) or 0, "📉 Зустрічний врожай! -1 Захисту")
])
cannon_splash = weapon_ability(0.15)([
    lambda a, d: (1, "💣 Вибух ядра! +1 Шкоди"),
    lambda a, d: (setattr(d, 'agi', max(0, d.agi - 1)) or 0, "💨 Контузія! -1 Спритність")
])

#EPIC
life_steal = weapon_ability(0.2)([
    lambda a, d: (setattr(a, 'hp', min(a.max_hp, a.hp + 1)) or 0, "🩸 Смак життя! +1 ХП"),
    lambda a, d: (setattr(d, 'atk', max(0, d.atk - 0.5)) or 0, "🥀 Ворог в'яне... -0.5 Атаки"),
    lambda a, d: (setattr(a, 'luck', a.luck + 1) or 0, "🍀 Вам щастить! +1 Удача"),
    lambda a, d: (1, "🔪 Жнива! +1 Шкоди")
])
confuse_hit = weapon_ability(0.2)([
    lambda a, d: (1, "🌀 Запаморочення! +1 Шкоди"),
    lambda a, d: (setattr(d, 'luck', max(0, d.luck - 2)) or 0, "❓ Де я? -2 Удачі"),
    lambda a, d: (setattr(a, 'agi', a.agi + 1) or 0, "💨 Користуючись моментом! +1 Спритність"),
    lambda a, d: (setattr(d, 'def_', max(0, d.def_ - 1)) or 0, "🛡 Захист відкритий! -1 Захисту")
])
freeze_debuff = weapon_ability(0.2)([
    lambda a, d: (setattr(d, 'agi', max(0, d.agi - 2)) or 0, "❄️ Обледеніння! -2 Спритність"),
    lambda a, d: (setattr(d, 'def_', max(0, d.def_ - 0.5)) or 0, "🧊 Крихка броня! -0.5 Захисту"),
    lambda a, d: (setattr(a, 'def_', a.def_ + 0.5) or 0, "🧥 Крижаний щит! +0.5 Захисту"),
    lambda a, d: (setattr(d, 'atk', max(0, d.atk - 1)) or 0, "🥶 Замерзлі пальці! -1 Атаки")
])
fear_debuff = weapon_ability(0.2)([
    lambda a, d: (setattr(d, 'atk', max(0, d.atk - 2)) or 0, "😱 Жах! -2 Атаки"),
    lambda a, d: (setattr(d, 'luck', max(0, d.luck - 1)) or 0, "📉 Руки дрижать! -1 Удача"),
    lambda a, d: (setattr(a, 'atk', a.atk + 1) or 0, "😈 Ваша перевага! +1 Атаки"),
    lambda a, d: (setattr(d, 'agi', max(0, d.agi - 1)) or 0, "🐢 Ступор! -1 Спритність")
])
energy_surge = weapon_ability(0.2)([
    lambda a, d: (setattr(a, 'agi', a.agi + 2) or 0, "⚡ Перевантаження! +2 Спритність"),
    lambda a, d: (setattr(a, 'luck', a.luck + 1) or 0, "🎰 Ривок! +1 Удача"),
    lambda a, d: (setattr(a, 'atk', a.atk + 1) or 0, "🔥 Сила тече! +1 Атаки"),
    lambda a, d: (setattr(a, 'hp', max(1, a.hp - 0.5)) or 1, "🧨 Віддача! 1 Шкоди (собі -0.5 ХП)")
])
owl_crit = weapon_ability(0.2)([
    lambda a, d: (1.5, "🦉 Удар кігтями! +1.5 Шкоди"),
    lambda a, d: (setattr(d, 'def_', max(0, d.def_ - 1)) or 0, "📉 Пробиття! -1 Захисту"),
    lambda a, d: (setattr(a, 'agi', a.agi + 1) or 0, "🦅 Політ! +1 Спритність"),
    lambda a, d: (setattr(a, 'luck', a.luck + 2) or 0, "🍀 Око сови! +2 Удача")
])
auto_attack = weapon_ability(0.2)([
    lambda a, d: (setattr(a, 'atk', a.atk + 0.5) or 0, "⚔️ Пристрілка! +0.5 Атаки"),
    lambda a, d: (setattr(d, 'def_', max(0, d.def_ - 1)) or 0, "🛡 Руйнування стійки! -1 Захисту"),
    lambda a, d: (setattr(a, 'def_', a.def_ + 1) or 0, "🧱 Окопи! +1 Захисту"),
    lambda a, d: (1, "🔫 Авто-удар! +1 Шкоди")
])
rage_boost = weapon_ability(0.2)([
    lambda a, d: (setattr(a, 'atk', a.atk + 0.5) or 0, "😤 Лють росте! +0.5 Атаки"),
    lambda a, d: (setattr(a, 'luck', a.luck + 0.5) or 0, "🎲 Азарт! +0.5 Удача"),
    lambda a, d: (setattr(d, 'atk', max(0, d.atk - 0.5)) or 0, "😨 Ворог пригнічений! -0.5 Атаки"),
    lambda a, d: (setattr(a, 'def_', a.def_ + 1) or 0, "🛡 Напролом! +1 Захисту")
])
ghost_strike = weapon_ability(0.2)([
    lambda a, d: (1, "👻 Удар з тіні! +1 Шкоди"),
    lambda a, d: (setattr(a, 'agi', a.agi + 2) or 0, "🌫 Примарність! +2 Спритність"),
    lambda a, d: (setattr(d, 'luck', 0) or 0, "🌑 Прокляття пустоти! Удача = 0"),
    lambda a, d: (setattr(a, 'hp', min(a.max_hp, a.hp + 1)) or 0, "🌌 Зцілення ефіром! +1 ХП")
])
crit_5 = weapon_ability(0.2)([
    lambda a, d: (2, "💣 Критичний вибух! +2 Шкоди"),
    lambda a, d: (setattr(a, 'luck', a.luck + 1) or 0, "🎰 Джекпот! +1 Удача"),
    lambda a, d: (setattr(d, 'agi', max(0, d.agi - 1)) or 0, "💨 Оглушення! -1 Спритність"),
    lambda a, d: (setattr(a, 'atk', a.atk + 1) or 0, "⚔️ Бойовий дух! +1 Атаки")
])

#LEGENDARY
cat_life = weapon_ability(0.3)([
    lambda a, d: (setattr(a, 'hp', min(a.max_hp, a.hp + 1)) or 0, "🐱 Лапка допомоги! +1 ХП"),
    lambda a, d: (setattr(a, 'agi', a.agi + 1) or 0, "🐾 М'яка хода! +1 Спритність"),
    lambda a, d: (setattr(a, 'luck', a.luck + 1) or 0, "🎰 Вдача кота! +1 Удача"),
    lambda a, d: (setattr(d, 'luck', max(0, d.luck - 1.5)) or 0, "😿 Чорний кіт перебіг! -1.5 Удачі"),
    lambda a, d: (setattr(d, 'agi', max(0, d.agi - 1.5)) or 0, "🧶 Заплутані нитки! -1.5 Спритності"),
    lambda a, d: (setattr(a, 'atk', a.atk + 1.5) or 0, "😼 Кігті! +1.5 Атаки")
])
tea_mastery = weapon_ability(0.3)([
    lambda a, d: (setattr(a, 'def_', a.def_ + 1.5) or 0, "🍵 Спокій! +1.5 Захисту"),
    lambda a, d: (setattr(a, 'hp', min(a.max_hp, a.hp + 1)) or 0, "🌱 Цілющий чай! +1 ХП"),
    lambda a, d: (setattr(a, 'luck', a.luck + 2) or 0, "🧘 Дзен! +2 Удача"),
    lambda a, d: (setattr(d, 'atk', max(0, d.atk - 1)) or 0, "🥱 Ворог розслабився! -1 Атаки"),
    lambda a, d: (setattr(d, 'luck', 0) or 0, "🚫 Гармонія порушена! Удача ворога 0"),
    lambda a, d: (setattr(a, 'agi', a.agi + 1.5) or 0, "💨 Плинність води! +1.5 Спритність")
])
double_strike = weapon_ability(0.3)([
    lambda a, d: (1, "⚔️ Перший удар! +1 Шкоди"),
    lambda a, d: (setattr(a, 'atk', a.atk + 1) or 0, "🗡 Загострення! +1 Атаки"),
    lambda a, d: (setattr(a, 'agi', a.agi + 1) or 0, "👟 Швидкий крок! +1 Спритність"),
    lambda a, d: (setattr(d, 'def_', max(0, d.def_ - 1)) or 0, "🛡 Пробиття! -1 Захисту"),
    lambda a, d: (1.5, "⚔️ Другий удар! +1.5 Шкоди"),
    lambda a, d: (setattr(d, 'agi', 0) or 0, "🛑 Ступор! Спритність ворога 0")
])
crit_20 = weapon_ability(0.3)([
    lambda a, d: (setattr(a, 'luck', a.luck + 2) or 0, "🎰 Фортуна! +2 Удача"),
    lambda a, d: (setattr(a, 'atk', a.atk + 2) or 0, "👑 Сила Титана! +2 Атаки"),
    lambda a, d: (setattr(a, 'def_', a.def_ + 2) or 0, "🧱 Моноліт! +2 Захисту"),
    lambda a, d: (3, "💥 КРИТ-МАШИНА! +3 Шкоди"),
    lambda a, d: (setattr(a, 'hp', a.max_hp) or 0, "🌟 Повне зцілення! ХП MAX"),
    lambda a, d: (setattr(d, 'luck', 0) or 0, "💀 Доля вирішена! Удача ворога 0")
])
pierce_armor = weapon_ability(0.3)([
    lambda a, d: (setattr(d, 'def_', 0) or 0, "🔓 Броню знято! Захист ворога 0"),
    lambda a, d: (1, "📌 Укол! +1 Шкоди"),
    lambda a, d: (setattr(a, 'atk', a.atk + 1) or 0, "🗡 Фокус на слабких місцях! +1 Атаки"),
    lambda a, d: (setattr(a, 'luck', a.luck + 1) or 0, "🍀 Влучність! +1 Удача"),
    lambda a, d: (setattr(d, 'atk', max(0, d.atk - 1.5)) or 0, "🩸 Болюча рана! -1.5 Атаки"),
    lambda a, d: (setattr(d, 'agi', max(0, d.agi - 1)) or 0, "👣 Хромота! -1 Спритність")
])
heavy_weight = weapon_ability(0.3)([
    lambda a, d: (setattr(a, 'agi', max(0, a.agi - 1)) or 0, "🐘 Тяжка хода! -1 Спритність"),
    lambda a, d: (setattr(a, 'atk', a.atk + 2.5) or 0, "🌋 Вага світу! +2.5 Атаки"),
    lambda a, d: (setattr(a, 'def_', a.def_ + 2) or 0, "🧱 Сталева стіна! +2 Захисту"),
    lambda a, d: (setattr(d, 'def_', max(0, d.def_ - 1.5)) or 0, "🏚 Трощення броні! -1.5 Захисту"),
    lambda a, d: (2, "💥 Землетрус! +2 Шкоди"),
    lambda a, d: (setattr(a, 'luck', a.luck + 1) or 0, "🍀 Домінація! +1 Удача")
])
range_attack = weapon_ability(0.3)([
    lambda a, d: (setattr(a, 'luck', a.luck + 2) or 0, "🏹 Далекоглядність! +2 Удача"),
    lambda a, d: (setattr(a, 'agi', a.agi + 2) or 0, "👟 Дистанція! +2 Спритність"),
    lambda a, d: (setattr(d, 'agi', max(0, d.agi - 1.5)) or 0, "📍 Пришпилено! -1.5 Спритності"),
    lambda a, d: (setattr(d, 'atk', max(0, d.atk - 1)) or 0, "📉 Безпорадність! -1 Атаки"),
    lambda a, d: (setattr(a, 'atk', a.atk + 1.5) or 0, "🎯 Снайпер! +1.5 Атаки"),
    lambda a, d: (setattr(d, 'def_', max(0, d.def_ - 1.5)) or 0, "🛡 Прошите наскрізь! -1.5 Захисту")
])
stun_chance = weapon_ability(0.3)([
    lambda a, d: (setattr(d, 'agi', 0) or 0, "🌀 СТАН! Спритність ворога 0"),
    lambda a, d: (setattr(d, 'atk', max(0, d.atk - 1)) or 0, "🥴 Шок! -1 Атаки"),
    lambda a, d: (setattr(d, 'def_', max(0, d.def_ - 2)) or 0, "🛡 Беззахисність! -2 Захисту"),
    lambda a, d: (setattr(a, 'luck', a.luck + 1) or 0, "🍀 Перевага! +1 Удача"),
    lambda a, d: (1.5, "🔨 Важкий бах! +1.5 Шкоди"),
    lambda a, d: (setattr(a, 'def_', a.def_ + 1.5) or 0, "🛡 Впевненість! +1.5 Захисту")
])
latex_choke = weapon_ability(0.3)([
    lambda a, d: (setattr(d, 'atk', max(0, d.atk - 2)) or 0, "🧤 Латексний зашморг! -2 Атаки"),
    lambda a, d: (setattr(d, 'agi', max(0, d.agi - 2)) or 0, "🛑 Брак повітря! -2 Спритність"),
    lambda a, d: (setattr(d, 'luck', 0) or 0, "🌑 Відчай ворога! Удача 0"),
    lambda a, d: (setattr(a, 'luck', a.luck + 2) or 0, "🎰 Домінація! +2 Удача"),
    lambda a, d: (setattr(d, 'def_', 0) or 0, "🔓 Захист зламано! Захист ворога 0"),
    lambda a, d: (1, "🥀 Ослаблення! +1 Шкоди")
])
scissor_sever = weapon_ability(0.3)([
    lambda a, d: (setattr(d, 'def_', max(0, d.def_ - 3)) or 0, "✂️ Розрізана броня! -3 Захисту"),      
    lambda a, d: (setattr(a, 'agi', a.agi + 2) or 0, "🏃 Швидкі леза! +2 Спритність"), 
    lambda a, d: (2, "🩸 Відсікання! +2 Шкоди"),
    lambda a, d: (setattr(d, 'atk', max(0, d.atk - 1)) or 0, "📉 Ворог поранений! -1 Атаки"), 
    lambda a, d: (setattr(a, 'luck', a.luck + 1) or 0, "🍀 Вдача різника! +1 Удача"),
    lambda a, d: (setattr(d, 'def_', 0) or 0, "🔓 Фінальний розріз! Захист ворога 0")
])
gaulish_might = weapon_ability(0.3)([
    lambda a, d: (setattr(a, 'atk', a.atk + 2) or 0, "🏺 Магічне зілля! +2 Атаки"),
    lambda a, d: (setattr(a, 'def_', a.def_ + 2) or 0, "🛡 Незламність! +2 Захисту"), 
    lambda a, d: (setattr(d, 'agi', max(0, d.agi - 1.5)) or 0, "🌪 Відкинуто назад! -1.5 Спритності"), 
    lambda a, d: (1.5, "👊 Удар кабаном! +1.5 Шкоди"),
    lambda a, d: (setattr(a, 'hp', min(a.max_hp, a.hp + 1)) or 0, "🍗 Відновлення сил! +1 ХП"), 
    lambda a, d: (setattr(d, 'def_', max(0, d.def_ - 1)) or 0, "📉 Шок від сили! -1 Захисту")
])
getsuga_tensho = weapon_ability(0.3)([
    lambda a, d: (setattr(a, 'agi', a.agi + 3) or 0, "⚡ Швидкість світла! +3 Спритність"),
    lambda a, d: (1, "🌙 Гецуга! +1 Шкоди"),
    lambda a, d: (setattr(d, 'def_', max(0, d.def_ - 2)) or 0, "💔 Розріз простору! -2 Захисту"),
    lambda a, d: (setattr(a, 'luck', a.luck + 2) or 0, "🌌 Сила шинігамі! +2 Удача"), 
    lambda a, d: (setattr(d, 'atk', max(0, d.atk - 1)) or 0, "📉 Подавлення! -1 Атаки"), 
    lambda a, d: (2, "🌙 ТЕНШО! +2 Шкоди")
])

ABILITY_REGISTRY = {
    "none": lambda a, t, r: (0, False, []),
    "hook_snag": hook_snag, "wooden_leg": wooden_leg, "heavy_swing": heavy_swing,
    "mop_wash": mop_wash, "yorshik_scrub": yorshik_scrub, "entangle_debuff": entangle_debuff,
    "drunk_fury": drunk_fury, "bleed_chance": bleed_chance, "precision_strike": precision_strike,
    "parry": parry, "curse_mark": curse_mark, "cannon_splash": cannon_splash,
    "life_steal": life_steal, "confuse_hit": confuse_hit, "freeze_debuff": freeze_debuff,
    "fear_debuff": fear_debuff, "energy_surge": energy_surge, "owl_crit": owl_crit,
    "auto_attack": auto_attack, "rage_boost": rage_boost, "ghost_strike": ghost_strike,
    "crit_5": crit_5, "cat_life": cat_life, "tea_mastery": tea_mastery,
    "double_strike": double_strike, "crit_20": crit_20, "pierce_armor": pierce_armor,
    "heavy_weight": heavy_weight, "range_attack": range_attack, "stun_chance": stun_chance,
    "latex_choke": latex_choke, "scissor_sever": scissor_sever, "gaulish_might": gaulish_might,
    "getsuga_tensho": getsuga_tensho
}