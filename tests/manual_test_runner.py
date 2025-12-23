import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repos.runner_repo import create_session_from_template, get_active_session, get_workout_set
from repos.templates_repo import create_template, add_exercise, add_set
from repos.exercises_repo import create_exercise, get_all_exercises
from db.conn import execute
from services.runner_service import complete_set
from core.timeutil import today_str_et
import datetime

def test_runner_idempotency():
    print("--- Setting up Test Data ---")
    today = today_str_et()
    execute("DELETE FROM workouts WHERE date = ?", (today,))
    
    # Template
    template_name = f"Runner Test {datetime.datetime.now().strftime('%H%M%S')}"
    tid = create_template(template_name)
    exercises = get_all_exercises()
    if not exercises: create_exercise("Test Curl")
    exercises = get_all_exercises()
    eid = exercises[0]['id']
    
    # 2 Exercises to test pointers
    # Ex 1
    te1 = add_exercise(tid, eid)
    add_set(te1, 10, 50) # Set 1
    add_set(te1, 10, 50) # Set 2
    
    # Snapshot
    print("--- Creating Session ---")
    wid = create_session_from_template(today, tid)
    print(f"Workout ID: {wid}")
    
    # Test 1: Complete Set 1
    print("\n--- Completing Set 1 (First Time) ---")
    # Ex 1 (Order 1), Set 1
    complete_set(wid, 1, 1, 12, 55)
    
    s1 = get_workout_set(wid, 1, 1)
    print(f"Set 1 Status: Completed={s1['completed']}, Actuals={s1['actual_reps']}x{s1['actual_weight']}")
    
    if s1['completed'] and s1['actual_reps'] == 12:
        print("PASS: Set 1 marked correctly.")
    else:
        print("FAIL: Set 1 not marked.")

    # Test 2: Complete Set 1 AGAIN (Double Click)
    print("\n--- Completing Set 1 (Second Time - Idempotency) ---")
    complete_set(wid, 1, 1, 12, 55)
    
    s1_again = get_workout_set(wid, 1, 1)
    s2 = get_workout_set(wid, 1, 2)
    
    print(f"Set 1 Status: Completed={s1_again['completed']}")
    print(f"Set 2 Status: Completed={s2['completed']}")
    
    if s1_again['completed'] and not s2['completed']:
        print("PASS: Idempotency verified. Set 2 remains untouched.")
    else:
        print("FAIL: Side effects detected.")

if __name__ == "__main__":
    test_runner_idempotency()
