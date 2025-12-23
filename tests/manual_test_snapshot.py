import sys
import os

# Add parent dir to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repos.runner_repo import create_session_from_template, get_active_session
from repos.templates_repo import create_template, add_exercise, add_set, get_template
from repos.exercises_repo import create_exercise, get_all_exercises
from db.conn import execute
from core.timeutil import today_str_et
import datetime

def test_snapshot():
    print("--- Setting up Test Data ---")
    # 1. Clean up today's workout for testing
    today = today_str_et()
    execute("DELETE FROM workouts WHERE date = ?", (today,))
    
    # 2. Create a Test Template
    template_name = f"Snapshot Test {datetime.datetime.now().strftime('%H%M%S')}"
    tid = create_template(template_name)
    print(f"Created Template: {template_name} (ID: {tid})")
    
    # Ensure strict order of creation to avoid UNIQUE constraint errors if re-running
    exercises = get_all_exercises()
    if not exercises:
        create_exercise("Test Squat")
        exercises = get_all_exercises()
    
    eid = exercises[0]['id']
    
    # Add Exercise to Template
    te_id = add_exercise(tid, eid)
    # Add Sets
    add_set(te_id, 10, 100)
    add_set(te_id, 8, 110)
    print(f"Added Exercise (ID: {eid}) with 2 sets.")
    
    print("\n--- executing create_session_from_template ---")
    try:
        workout_id = create_session_from_template(today, tid)
        print(f"Success! Created Workout ID: {workout_id}")
    except Exception as e:
        print(f"FAILED: {e}")
        return

    print("\n--- Verifying Snapshot ---")
    session = get_active_session(today)
    if session:
        print(f"Active Session Found: {session['name']} (Status: {session['status']})")
        print(f"Started At: {session['started_at']}")
    else:
        print("ERROR: No active session found.")
        
    print("\n--- Testing Constraint (Double Start) ---")
    try:
        create_session_from_template(today, tid)
        print("ERROR: Should have failed to create second session.")
    except Exception as e:
        print(f"Correctly caught expected error: {e}")

if __name__ == "__main__":
    test_snapshot()
