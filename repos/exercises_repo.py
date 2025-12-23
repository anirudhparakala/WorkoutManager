from db.conn import execute, query_all, query_one

def get_all_exercises():
    """Returns a list of all exercises ordered by name."""
    rows = query_all("SELECT id, name, notes FROM exercises ORDER BY name")
    return [{"id": r[0], "name": r[1], "notes": r[2]} for r in rows]

def create_exercise(name, notes=None):
    """Creates a new exercise."""
    execute("INSERT INTO exercises (name, notes) VALUES (?, ?)", (name, notes))
    return query_one("SELECT id FROM exercises WHERE name = ?", (name,))[0]
