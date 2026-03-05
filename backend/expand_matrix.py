import json
import os

# Paths
MATRIX_PATH = "backend/data/archetype_sphere_matrix.json"
BACKUP_PATH = "backend/data/archetype_sphere_matrix.json.bak"
ARCHETYPES_PATH = "backend/data/archetypes.json"
HAWKINS_PATH = ".agents/hawkins_scale.md"

def generate_expanded_matrix():
    # 1. Load basic archetypes info
    with open(ARCHETYPES_PATH, "r") as f:
        archetypes = json.load(f)
    
    # 2. Load existing (partially populated) matrix if exists, else start fresh
    if os.path.exists(MATRIX_PATH):
        with open(MATRIX_PATH, "r") as f:
            matrix = json.load(f)
    else:
        matrix = {}

    # 3. Load backup for base descriptions (shadow/light)
    with open(BACKUP_PATH, "r") as f:
        backup = json.load(f)

    # Spheres list (should match spheres.json)
    spheres = ["IDENTITY", "MONEY", "RELATIONS", "FAMILY", "MISSION", "HEALTH", "SOCIETY", "SPIRIT"]

    # 4. Process each archetype
    for arch in archetypes:
        arch_id = str(arch['id'])
        
        # Skip if already fully populated (like Fool) unless we want to overwrite
        if arch_id in matrix and arch_id != "0": # We keep 0 as a manual gold standard
             pass # Logic to expand goes here
        
        if arch_id not in matrix:
            matrix[arch_id] = {
                "_meta": {
                    "archetype_id": arch['id'],
                    "archetype_name": arch['name'],
                    "archetype_name_en": arch['name_en']
                },
                "_structure": matrix["0"]["_structure"] # Inherit structure from Fool
            }

        # 5. Populate spheres
        for sphere in spheres:
            # Get base data from backup if available, else from archetypes.json
            base_shadow = backup.get(arch_id, {}).get(sphere, {}).get("shadow", arch['shadow'])
            base_light = backup.get(arch_id, {}).get(sphere, {}).get("light", arch['light'])
            base_desc = backup.get(arch_id, {}).get(sphere, {}).get("description", arch['description'])

            # If the sphere already exists in matrix with full levels, skip
            if sphere in matrix[arch_id] and "level_1_0_20" in matrix[arch_id][sphere]:
                continue

            matrix[arch_id][sphere] = {
                "core_shadow": base_shadow,
                "core_light": base_light,
                "core_description": base_desc,
                # Levels will be generated or left as placeholders for refinement
                "level_1_0_20": f"Уровень выживания {arch['name']} в {sphere}: Тотальное подавление потенциала.",
                "level_2_20_100": f"Уровень Стыда/Вины {arch['name']} в {sphere}: Скрытые деструктивные паттерны.",
                "level_3_100_175": f"Уровень Страха {arch['name']} в {sphere}: Избегание и тревога.",
                "level_4_175_200": f"Уровень Гнева {arch['name']} в {sphere}: Агрессивное самоутверждение.",
                "level_5_200_250": f"Уровень Смелости {arch['name']} в {sphere}: Начало осознанного пути.",
                "level_6_250_310": f"Уровень Нейтральности {arch['name']} в {sphere}: Устойчивость.",
                "level_7_310_400": f"Уровень Готовности {arch['name']} в {sphere}: Активный рост.",
                "level_8_400_500": f"Уровень Разума {arch['name']} в {sphere}: Понимание законов игры.",
                "level_9_500_600": f"Уровень Любви {arch['name']} в {sphere}: Истинное служение.",
                "level_10_600_1000": f"Уровень Мира {arch['name']} в {sphere}: Тотальная реализация.",
                "speech_markers_shadow": ["плохо", "не могу", "виноват"],
                "speech_markers_light": ["хорошо", "могу", "спасибо"],
                "quantum_shift": f"Переход от тени {arch['name']} к свету через осознание уроков {sphere}.",
                "agent_question": f"Что ты чувствуешь прямо сейчас, глядя на {arch['name']} в сфере {sphere}?",
                "linked_cards": [],
                "xp_reward": 50
            }

    # 6. Save result
    with open(MATRIX_PATH, "w", encoding="utf-8") as f:
        json.dump(matrix, f, ensure_ascii=False, indent=2)
    
    print(f"Matrix updated with {len(matrix)} archetypes.")

if __name__ == "__main__":
    generate_expanded_matrix()
