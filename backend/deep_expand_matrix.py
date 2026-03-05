import json
import os

# Paths
MATRIX_PATH = "backend/data/archetype_sphere_matrix.json"
BACKUP_PATH = "backend/data/archetype_sphere_matrix.json.bak"
ARCHETYPES_PATH = "backend/data/archetypes.json"

def get_level_template(level_num, arch_name, sphere):
    templates = {
        1: f"Тотальный паралич {arch_name} в {sphere}. Ощущение небытия, коллапс воли и полная потеря ресурсов.",
        2: f"Стыд и вина {arch_name} в {sphere}. Ощущение собственной дефектности, желание спрятаться.",
        3: f"Страх и тревога {arch_name} в {sphere}. Мир воспринимается как угроза, постоянная ментальная самозащита.",
        4: f"Гнев и агрессия {arch_name} в {sphere}. Попытки доказать свою правоту через борьбу и подавление других.",
        5: f"Мужество и честность {arch_name} в {sphere}. Принятие ответственности за свою жизнь в этой сфере.",
        6: f"Нейтральность и гибкость {arch_name} в {sphere}. Устойчивость, спокойное решение задач без драмы.",
        7: f"Готовность и оптимизм {arch_name} в {sphere}. Активное развитие, видение новых возможностей.",
        8: f"Разум и понимание {arch_name} в {sphere}. Системный взгляд, использование интеллекта как инструмента.",
        9: f"Любовь и сострадание {arch_name} в {sphere}. Служение из целостности, глубокое принятие всего.",
        10: f"Мир и единство {arch_name} в {sphere}. Тотальная реализация Божественного Намерения в этой сфере."
    }
    return templates.get(level_num, "Описание уровня...")

def get_markers_for_level(level_num, is_shadow=True, arch_name=""):
    # Markers represent the VIBE of the level + ARCHETYPE flavor
    flavor = {
        "Шут": {"shadow": ["просто так", "завтра будет", "не моя вина"], "light": ["доверяю потоку", "игра", "всё новое"]},
        "Маг": {"shadow": ["я всё просчитал", "манипуляция", "иллюзия"], "light": ["создаю", "намерение", "фокус"]},
        "Жрица": {"shadow": ["тайна", "меня не поймут", "холод"], "light": ["интуиция", "тишина", "суть"]},
        "Императрица": {"shadow": ["надо больше", "удушье", "жадность"], "light": ["изобилие", "забота", "плодородие"]},
        "Император": {"shadow": ["будет по-моему", "контроль", "жесткость"], "light": ["структура", "порядок", "защита"]},
        "Иерофант": {"shadow": ["так положено", "догма", "вы неправы"], "light": ["традиция", "мудрость", "наставник"]},
        "Влюблённые": {"shadow": ["не могу выбрать", "без тебя никак", "пустота"], "light": ["выбор из сердца", "целостность", "союз"]},
        "Колесница": {"shadow": ["по головам", "быстрее", "агрессия"], "light": ["баланс сил", "цель", "победа"]},
        "Сила": {"shadow": ["сломаю", "страсть", "насилие"], "light": ["мягкая сила", "приручение", "стойкость"]},
        "Отшельник": {"shadow": ["уйдите все", "одиночество", "холод"], "light": ["внутренний свет", "поиск сути", "уединение"]},
        "Фортуна": {"shadow": ["не везет", "жертва судьбы", "азарт"], "light": ["циклы", "центр циклона", "принятие этапов"]},
        "Справедливость": {"shadow": ["виновны", "перфекционизм", "месть"], "light": ["честность", "баланс", "последствия"]},
        "Повешенный": {"shadow": ["я жертва", "тупик", "бессилие"], "light": ["новый взгляд", "пауза", "озарение"]},
        "Смерть": {"shadow": ["страх конца", "цепляюсь", "стагнация"], "light": ["освобождение", "новое начало", "трансформация"]},
        "Умеренность": {"shadow": ["серость", "болото", "избегаю"], "light": ["алхимия", "гармония", "чувство меры"]},
        "Дьявол": {"shadow": ["зависимость", "одержимость", "ложь"], "light": ["встреча с тенью", "свобода", "ресурс"]},
        "Башня": {"shadow": ["катастрофа", "разрушение", "гнев"], "light": ["прорыв", "озарение", "очищение"]},
        "Звезда": {"shadow": ["мечты", "далеко", "холодность"], "light": ["надежда", "путеводная нить", "предназначение"]},
        "Луна": {"shadow": ["страх", "бред", "паранойя"], "light": ["интуиция", "глубина", "сны"]},
        "Солнце": {"shadow": ["я — есть всё", "эго", "высокомерие"], "light": ["радость", "тепло", "ясность"]},
        "Суд": {"shadow": ["вина", "обида", "прошлое"], "light": ["пробуждение", "прощение", "призыв"]},
        "Мир": {"shadow": ["страх финиша", "недоделанность", "фрагменты"], "light": ["целостность", "интеграция", "завершение"]}
    }
    
    arch_flavor = flavor.get(arch_name, {"shadow": [], "light": []})
    
    if is_shadow:
        base_markers = {
            1: ["меня нет", "всё кончено", "пустота"],
            2: ["я виноват", "мне стыдно", "я ошибка"],
            3: ["страшно", "а вдруг", "опасно"],
            4: ["они ответят", "я им покажу", "моя правда"],
        }
        return list(set(base_markers.get(level_num, ["проблема"]) + arch_flavor["shadow"]))
    else:
        base_markers = {
            5: ["я решу", "я попробую", "я справлюсь"],
            6: ["всё нормально", "я спокоен", "баланс"],
            7: ["я готов", "мне интересно", "возможности"],
            8: ["я понимаю", "вижу систему", "логично"],
            9: ["я люблю", "благодарю", "единство"],
            10: ["тишина", "я есть", "свет"]
        }
        return list(set(base_markers.get(level_num, ["свет"]) + arch_flavor["light"]))

def run_deep_expansion():
    with open(ARCHETYPES_PATH, "r") as f:
        archetypes = json.load(f)
    
    with open(MATRIX_PATH, "r") as f:
        matrix = json.load(f)

    with open(BACKUP_PATH, "r") as f:
        backup = json.load(f)

    spheres = ["IDENTITY", "MONEY", "RELATIONS", "FAMILY", "MISSION", "HEALTH", "SOCIETY", "SPIRIT"]

    for arch in archetypes:
        arch_id = str(arch['id'])
        
        # REMOVED SKIP logic to ensure Fool and Magician also get the refined markers
        # but we preserve their core_shadow/light if they were already good.
            
        if arch_id not in matrix:
            matrix[arch_id] = {
                "_meta": {
                    "archetype_id": arch['id'],
                    "archetype_name": arch['name'],
                    "archetype_name_en": arch['name_en']
                },
                "_structure": matrix["0"]["_structure"]
            }

        for sphere in spheres:
            # Get base data
            base_shadow = backup.get(arch_id, {}).get(sphere, {}).get("shadow", arch['shadow'])
            base_light = backup.get(arch_id, {}).get(sphere, {}).get("light", arch['light'])
            base_desc = backup.get(arch_id, {}).get(sphere, {}).get("description", arch['description'])

            matrix[arch_id][sphere] = {
                "core_shadow": base_shadow,
                "core_light": base_light,
                "core_description": base_desc,
                "level_1_0_20": get_level_template(1, arch['name'], sphere),
                "level_2_20_100": get_level_template(2, arch['name'], sphere),
                "level_3_100_175": get_level_template(3, arch['name'], sphere),
                "level_4_175_200": get_level_template(4, arch['name'], sphere),
                "level_5_200_250": get_level_template(5, arch['name'], sphere),
                "level_6_250_310": get_level_template(6, arch['name'], sphere),
                "level_7_310_400": get_level_template(7, arch['name'], sphere),
                "level_8_400_500": get_level_template(8, arch['name'], sphere),
                "level_9_500_600": get_level_template(9, arch['name'], sphere),
                "level_10_600_1000": get_level_template(10, arch['name'], sphere),
                "speech_markers_shadow": get_markers_for_level(3, True, arch['name']), 
                "speech_markers_light": get_markers_for_level(5, False, arch['name']), 
                "quantum_shift": f"Переход от тени {arch['name']} к свету через осознанную работу в сфере {sphere}.",
                "agent_question": f"Что самое важное тебе нужно понять о {arch['name']} в сфере {sphere} прямо сейчас?",
                "linked_cards": [],
                "xp_reward": 50
            }

    with open(MATRIX_PATH, "w", encoding="utf-8") as f:
        json.dump(matrix, f, ensure_ascii=False, indent=2)
    
    print(f"Deep expansion complete for {len(matrix)} archetypes.")

if __name__ == "__main__":
    run_deep_expansion()
