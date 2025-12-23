from db.conn import execute, query_all, query_one, transaction

def create_template(name):
    """Creates a new workout template."""
    execute("INSERT INTO templates (name) VALUES (?)", (name,))
    return query_one("SELECT id FROM templates WHERE name = ? ORDER BY id DESC LIMIT 1", (name,))[0]

def get_template(template_id):
    """Returns a template with nested exercises and sets."""
    template = query_one("SELECT * FROM templates WHERE id = ?", (template_id,))
    if not template:
        return None
    
    # Convert Row to dict
    result = {
        "id": template[0],
        "name": template[1],
        "created_at": template[2],
        "exercises": []
    }
    
    # Fetch exercises
    exercises = query_all("""
        SELECT te.id, te.exercise_id, e.name, te.order_index, te.sets, te.reps, te.weight
        FROM template_exercises te
        JOIN exercises e ON te.exercise_id = e.id
        WHERE te.template_id = ?
        ORDER BY te.order_index
    """, (template_id,))
    
    for ex in exercises:
        ex_data = {
            "id": ex[0],
            "exercise_id": ex[1],
            "name": ex[2],
            "order_index": ex[3],
            "default_sets_count": ex[4], # Legacy/Summary column
            "default_reps": ex[5],       # Legacy/Summary column
            "default_weight": ex[6],     # Legacy/Summary column
            "sets": []
        }
        
        # Fetch detailed sets
        sets = query_all("""
            SELECT id, set_number, reps, weight
            FROM template_sets
            WHERE template_exercise_id = ?
            ORDER BY set_number
        """, (ex[0],))
        
        for s in sets:
            ex_data["sets"].append({
                "id": s[0],
                "set_number": s[1],
                "reps": s[2],
                "weight": s[3]
            })
            
        result["exercises"].append(ex_data)
        
    return result

def add_exercise(template_id, exercise_id):
    """Adds an exercise to the template at the end of the list."""
    # Get current max order
    row = query_one("SELECT MAX(order_index) FROM template_exercises WHERE template_id = ?", (template_id,))
    next_order = (row[0] or 0) + 1
    
    execute("""
        INSERT INTO template_exercises (template_id, exercise_id, order_index)
        VALUES (?, ?, ?)
    """, (template_id, exercise_id, next_order))
    
    # Return the new ID
    return query_one("SELECT id FROM template_exercises WHERE template_id = ? AND order_index = ?", (template_id, next_order))[0]

def remove_exercise(template_exercise_id):
    """Removes an exercise and re-normalizes order."""
    with transaction() as tx:
        # Get template_id and order_index
        row = query_one("SELECT template_id, order_index FROM template_exercises WHERE id = ?", (template_exercise_id,))
        if not row:
            return
        template_id, order_index = row
        
        # Delete
        execute("DELETE FROM template_exercises WHERE id = ?", (template_exercise_id,))
        
        # Shift others down
        execute("""
            UPDATE template_exercises
            SET order_index = order_index - 1
            WHERE template_id = ? AND order_index > ?
        """, (template_id, order_index))

from libsql_client import Statement
from db.conn import get_conn

def reorder_exercises(template_id, new_order_ids):
    """Updates order_index for all exercises in the list using batch execution."""
    stmts = []
    
    # 1. Set all to negative temporary values to avoid unique constraint collisions
    for te_id in new_order_ids:
        stmts.append(Statement(
            "UPDATE template_exercises SET order_index = -1 * id WHERE id = ? AND template_id = ?",
            (te_id, template_id)
        ))
        
    # 2. Set to correct new values
    for index, te_id in enumerate(new_order_ids):
        stmts.append(Statement(
            "UPDATE template_exercises SET order_index = ? WHERE id = ? AND template_id = ?",
            (index + 1, te_id, template_id)
        ))
    
    with get_conn() as client:
        client.batch(stmts)

def add_set(template_exercise_id, reps=None, weight=None):
    """Adds a set to a template exercise."""
    row = query_one("SELECT MAX(set_number) FROM template_sets WHERE template_exercise_id = ?", (template_exercise_id,))
    next_set = (row[0] or 0) + 1
    
    execute("""
        INSERT INTO template_sets (template_exercise_id, set_number, reps, weight)
        VALUES (?, ?, ?, ?)
    """, (template_exercise_id, next_set, reps, weight))

def delete_set(set_id):
    """Deletes a set and re-normalizes set numbers."""
    with transaction() as tx:
        row = query_one("SELECT template_exercise_id, set_number FROM template_sets WHERE id = ?", (set_id,))
        if not row:
            return
        te_id, set_num = row
        
        execute("DELETE FROM template_sets WHERE id = ?", (set_id,))
        
def get_all_templates():
    """Returns a list of all templates."""
    rows = query_all("SELECT id, name, created_at FROM templates ORDER BY name")
    return [{"id": r[0], "name": r[1], "created_at": r[2]} for r in rows]

def update_template(template_id, name):
    """Updates template name."""
    execute("UPDATE templates SET name = ? WHERE id = ?", (name, template_id))

def delete_template(template_id):
    """Deletes a template."""
    execute("DELETE FROM templates WHERE id = ?", (template_id,))

def update_set(set_id, reps=None, weight=None):
    """Updates a set."""
    execute("UPDATE template_sets SET reps = ?, weight = ? WHERE id = ?", (reps, weight, set_id))

def update_template_set_match(template_id, order_index, set_number, reps, weight):
    """Updates the template set that matches the given structure."""
    # Find list of exercises to map order_index
    # We could do a complex join update, but SQLite syntax varies.
    # Safe way: Find ID first.
    row = query_one("""
        SELECT ts.id 
        FROM template_sets ts
        JOIN template_exercises te ON ts.template_exercise_id = te.id
        WHERE te.template_id = ? AND te.order_index = ? AND ts.set_number = ?
    """, (template_id, order_index, set_number))
    
    if row:
        ts_id = row[0]
        execute("UPDATE template_sets SET reps = ?, weight = ? WHERE id = ?", (reps, weight, ts_id))
