from db.conn import get_conn, execute, query_one, query_all
import datetime

def get_active_session(date_str):
    """Returns the active session for the date if exists."""
    row = query_one("""
        SELECT id, date, name, status, plan_type, template_id, started_at
        FROM workouts
        WHERE date = ? AND status = 'ACTIVE'
    """, (date_str,))
    
    if row:
        return {
            "id": row[0],
            "date": row[1],
            "name": row[2],
            "status": row[3],
            "plan_type": row[4],
            "template_id": row[5],
            "started_at": row[6]
        }
    return None

def create_session_from_template(date_str, template_id):
    """
    Creates a snapshot of the template into the workout session tables.
    Must be called when starting a workout.
    """
    # 1. Enforce one ACTIVE session per date
    active = get_active_session(date_str)
    if active:
        raise Exception("An active session already exists for this date.")

    # 2. Get Template Data (Exercises & Sets)
    # We need a deep fetch. 
    # For now, we'll do raw queries or reuse service/repo? 
    # Better to keep repo self-contained or use other repos.
    # Let's do raw queries for speed and decoupling from 'templates_service' logic which might change.
    
    # Fetch Template
    template = query_one("SELECT name FROM templates WHERE id = ?", (template_id,))
    if not template:
        raise Exception("Template not found.")
    template_name = template[0]
    
    # Fetch Template Exercises
    t_exercises = query_all("""
        SELECT id, exercise_id, order_index 
        FROM template_exercises 
        WHERE template_id = ? 
        ORDER BY order_index
    """, (template_id,))
    
    # Fetch Template Sets
    # Map temlpate_exercise_id -> list of sets
    t_sets_map = {}
    if t_exercises:
        placeholders = ','.join(['?'] * len(t_exercises))
        te_ids = [te[0] for te in t_exercises]
        rows = query_all(f"""
            SELECT template_exercise_id, set_number, reps, weight
            FROM template_sets
            WHERE template_exercise_id IN ({placeholders})
        """, te_ids)
        for r in rows:
            tid, s_num, reps, weight = r
            if tid not in t_sets_map:
                t_sets_map[tid] = []
            t_sets_map[tid].append({
                "set_number": s_num,
                "reps": reps,
                "weight": weight
            })

    # 3. Create/Update Workout
    # Check if workout row exists (PLANNED)
    existing = query_one("SELECT id FROM workouts WHERE date = ?", (date_str,))
    
    started_at = datetime.datetime.now().isoformat()
    
    if existing:
        workout_id = existing[0]
        execute("""
            UPDATE workouts 
            SET status = 'ACTIVE', started_at = ?, template_id = ?, name = ?, plan_type = 'WORKOUT'
            WHERE id = ?
        """, (started_at, template_id, template_name, workout_id))
        
        # Cleanup existing workout_exercises if any (start fresh snapshot)
        # This handles case where we might have started before or it was partial? 
        # Requirement says "Snapshot matches template at start time".
        # If we are "starting", we assume fresh snapshot of layout.
        execute("DELETE FROM workout_exercises WHERE workout_id = ?", (workout_id,))
        
    else:
        execute("""
            INSERT INTO workouts (date, status, started_at, template_id, name, plan_type)
            VALUES (?, 'ACTIVE', ?, ?, ?, 'WORKOUT')
        """, (date_str, started_at, template_id, template_name))
        
        # Need to get the ID.
        # Since execute doesn't return ID easily in this wrapper, fetch it.
        row = query_one("SELECT id FROM workouts WHERE date = ? AND status = 'ACTIVE'", (date_str,))
        workout_id = row[0]

    # 4. Insert Exercises & Sets
    # NOTE: Ideally this loop is in a transaction.
    # We will proceed sequentially.
    
    for te in t_exercises:
        te_id = te[0]
        ex_id = te[1]
        order = te[2]
        
        execute("""
            INSERT INTO workout_exercises (workout_id, exercise_id, order_index)
            VALUES (?, ?, ?)
        """, (workout_id, ex_id, order))
        
        # Get new ID
        # reliable way without last_insert_rowid race condition in app:
        # lookup by unique constraint (workout_id, order_index)
        we_row = query_one("""
            SELECT id FROM workout_exercises 
            WHERE workout_id = ? AND order_index = ?
        """, (workout_id, order))
        we_id = we_row[0]
        
        # Insert Sets
        sets = t_sets_map.get(te_id, [])
        for s in sets:
            execute("""
                INSERT INTO sets (workout_exercise_id, set_number, planned_reps, planned_weight, completed)
                VALUES (?, ?, ?, ?, 0)
            """, (we_id, s['set_number'], s['reps'], s['weight']))

    return workout_id

def get_workout_set(workout_id, exercise_order, set_number):
    """Retrieves a specific set by workout structure."""
    row = query_one("""
        SELECT s.id, s.completed, s.actual_reps, s.actual_weight
        FROM sets s
        JOIN workout_exercises we ON s.workout_exercise_id = we.id
        WHERE we.workout_id = ? 
          AND we.order_index = ? 
          AND s.set_number = ?
    """, (workout_id, exercise_order, set_number))
    
    if row:
        return {
            "id": row[0],
            "completed": bool(row[1]),
            "actual_reps": row[2],
            "actual_weight": row[3]
        }
    return None

def update_set_actuals(set_id, reps, weight):
    """Updates set with actual values and marks as complete."""
    completed_at = datetime.datetime.now().isoformat()
    execute("""
        UPDATE sets 
        SET actual_reps = ?, actual_weight = ?, completed = 1
        WHERE id = ?
    """, (reps, weight, set_id))

def get_workout_exercises_with_sets(workout_id):
    """Returns all exercises and sets for a workout to build progression."""
    # This is a bit complex, let's fetch flat and restructure or fetch hierarchically.
    # Flat fetch of sets joined with workout_exercises
    rows = query_all("""
        SELECT we.id, we.exercise_id, e.name, we.order_index, 
               s.id, s.set_number, s.planned_reps, s.planned_weight, s.actual_reps, s.actual_weight, s.completed
        FROM workout_exercises we
        JOIN exercises e ON we.exercise_id = e.id
        JOIN sets s ON s.workout_exercise_id = we.id
        WHERE we.workout_id = ?
        ORDER BY we.order_index, s.set_number
    """, (workout_id,))
    
    # Structure: [ { ...exercise, sets: [...] } ]
    exercises_map = {}
    results = []
    
    for r in rows:
        we_id = r[0]
        if we_id not in exercises_map:
            ex_obj = {
                "id": we_id,
                "exercise_id": r[1],
                "name": r[2],
                "order_index": r[3],
                "sets": []
            }
            exercises_map[we_id] = ex_obj
            results.append(ex_obj)
        else:
            ex_obj = exercises_map[we_id]
            
        ex_obj["sets"].append({
            "id": r[4],
            "set_number": r[5],
            "planned_reps": r[6],
            "planned_weight": r[7],
            "actual_reps": r[8],
            "actual_weight": r[9],
            "completed": bool(r[10])
        })
        
    return results

def start_workout_session(date_str, template_id):
    """Wrapper for create_session_from_template."""
    return create_session_from_template(date_str, template_id)

def complete_workout_session(workout_id):
    """Marks the workout as completed."""
    completed_at = datetime.datetime.now().isoformat()
    execute("UPDATE workouts SET status = 'COMPLETED', completed_at = ? WHERE id = ?", (completed_at, workout_id))

