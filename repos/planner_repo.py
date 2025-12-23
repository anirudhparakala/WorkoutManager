from db.conn import execute, query_one, query_all

def get_day_plan(date_str):
    """Returns the workout row for the date."""
    row = query_one("""
        SELECT id, date, name, status, plan_type, template_id 
        FROM workouts 
        WHERE date = ?
    """, (date_str,))
    if row:
        return {
            "id": row[0],
            "date": row[1],
            "name": row[2],
            "status": row[3],
            "plan_type": row[4],
            "template_id": row[5]
        }
    return None

def upsert_day_plan(date_str, plan_type, template_id=None, name=None):
    """Creates or updates the plan for a date."""
    # Check if exists
    existing = get_day_plan(date_str)
    
    if existing:
        execute("""
            UPDATE workouts 
            SET plan_type = ?, template_id = ?, name = ?
            WHERE date = ?
        """, (plan_type, template_id, name, date_str))
    else:
        execute("""
            INSERT INTO workouts (date, plan_type, template_id, name)
            VALUES (?, ?, ?, ?)
        """, (date_str, plan_type, template_id, name))

def get_range(start_date, end_date):
    """Returns list of plans in range."""
    rows = query_all("""
        SELECT id, date, name, status, plan_type, template_id
        FROM workouts
        WHERE date >= ? AND date <= ?
        ORDER BY date
    """, (start_date, end_date))
    
    return [{
        "id": r[0],
        "date": r[1],
        "name": r[2],
        "status": r[3],
        "plan_type": r[4],
        "template_id": r[5]
    } for r in rows]

def delete_day_plan(date_str):
    """Deletes the plan for a date."""
    execute("DELETE FROM workouts WHERE date = ?", (date_str,))

