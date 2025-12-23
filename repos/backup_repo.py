from db.conn import query_all

def export_data():
    """Fetches all data from critical tables."""
    tables = [
        "exercises", 
        "templates", 
        "template_exercises", 
        "template_sets", 
        "workouts", 
        "workout_exercises", 
        "sets"
    ]
    
    data = {}
    
    for table in tables:
        # Fetch all rows for the table
        # We need columns to make it JSON friendly? 
        # query_all returns tuples. We can try to make it dicts if we know schema or just dump tuples.
        # For restore, list of lists (rows) + table name is sufficient if schema stable.
        # But dicts are safer.
        
        # Simple query to get columns
        # In SQLite: PRAGMA table_info(table_name)
        # But we use execute directly? 
        # Let's just dump list of lists for now, or assume we can rely on order.
        # Better: SELECT * matches schema order.
        
        rows = query_all(f"SELECT * FROM {table}")
        
        # We assume rows are tuples.
        # JSON dump handles tuples as lists.
        data[table] = rows
        
    return data
