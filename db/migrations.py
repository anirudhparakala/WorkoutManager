import os
from db.conn import execute, query_one

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), 'schema.sql')

def migrate():
    """Applies database migrations."""
    print("Checking for migrations...")
    
    # Ensure schema_version table exists
    execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Get current version
    row = query_one("SELECT MAX(version) FROM schema_version")
    current_version = row[0] if row and row[0] is not None else 0
    
    print(f"Current schema version: {current_version}")
    
    if current_version < 1:
        print("Applying migration v1...")
        with open(SCHEMA_FILE, 'r') as f:
            schema_sql = f.read()
            
        # Split by statement to execute one by one (libsql might not support multi-statement in one call depending on driver)
        # But for simplicity and transaction safety, we'll try to execute the whole block if supported, 
        # or split by semicolon if needed. libsql-client usually supports batch or we can just run execute on the whole string if it's DDL.
        # Let's split by semicolon to be safe and robust.
        statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
        
        for statement in statements:
            execute(statement)
            
        execute("INSERT INTO schema_version (version) VALUES (1)")
        print("Migration v1 applied successfully.")
        
    if current_version < 2:
        print("Applying migration v2...")
        execute("""
            CREATE TABLE IF NOT EXISTS template_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_exercise_id INTEGER NOT NULL,
                set_number INTEGER NOT NULL,
                reps INTEGER,
                weight REAL,
                FOREIGN KEY (template_exercise_id) REFERENCES template_exercises(id) ON DELETE CASCADE,
                UNIQUE (template_exercise_id, set_number)
            );
        """)
        execute("INSERT INTO schema_version (version) VALUES (2)")
        print("Migration v2 applied successfully.")
        
    if current_version < 3:
        print("Applying migration v3...")
        # SQLite doesn't support adding multiple columns in one ALTER TABLE (in older versions), 
        # but modern SQLite does. However, to be safe and standard:
        try:
            execute("ALTER TABLE workouts ADD COLUMN plan_type TEXT CHECK(plan_type IN ('WORKOUT', 'REST')) DEFAULT 'WORKOUT'")
        except Exception:
            pass # Column might exist if partially applied
            
        try:
            execute("ALTER TABLE workouts ADD COLUMN template_id INTEGER REFERENCES templates(id) ON DELETE SET NULL")
        except Exception:
            pass
            
        execute("INSERT INTO schema_version (version) VALUES (3)")
        print("Migration v3 applied successfully.")
    else:
        print("Database is up to date.")
