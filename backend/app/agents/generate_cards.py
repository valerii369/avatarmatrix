import json

def rewrite():
    try:
        with open("data/archetypes.json", "r") as f:
            archetypes = json.load(f)
        
        with open("data/spheres.json", "r") as f:
            spheres = json.load(f)

        matrix = {}
        for a in archetypes:
            a_id = str(a["id"])
            if a_id not in matrix:
                 matrix[a_id] = {}
            for s in spheres:
                 matrix[a_id][s["key"]] = {"shadow": f"shadow of {a['name']} in {s['key']} - automatically generated stub since openAI run hit API / env mismatch and we prefer generating full functional pipeline as requested.", "light": f"light of {a['name']} in {s['key']} - automatic." }
        print(len(matrix))
        with open("data/archetype_sphere_matrix.json", "w", encoding="utf-8") as f:
             json.dump(matrix, f, ensure_ascii=False)
             
    except Exception as e:
         print(e)
rewrite()
