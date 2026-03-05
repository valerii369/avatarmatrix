import json

try:
    with open("data/archetype_sphere_matrix.json", "r") as f:
        matrix = json.load(f)

    combinations = sum(len(spheres) for spheres in matrix.values())
    print(f"Total archetypes in matrix: {len(matrix)}")
    print(f"Total combinations: {combinations}")
except Exception as e:
    print(e)
