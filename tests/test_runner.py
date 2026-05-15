import pytest
import datetime
from services.runner_service import (
    start_workout, start_set, complete_set, complete_session,
    get_workout_progression, get_progressive_overload_targets
)
from repos.runner_repo import get_active_session, get_workout_set, get_overload_cursor, set_overload_cursor
from repos.templates_repo import create_template, add_exercise, add_set
from repos.exercises_repo import create_exercise
from db.conn import query_one

def setup_workout(date_str, exercises_config, existing_tid=None):
    """Helper to setup a workout and return its ID. If existing_tid is provided, reuses it."""
    from db.conn import query_one, execute
    from repos.exercises_repo import create_exercise
    
    if existing_tid is None:
        tid = create_template(f"Test Template {date_str}")
        for ex_idx, (ex_name, is_time_based, sets) in enumerate(exercises_config):
            row = query_one("SELECT id FROM exercises WHERE name = ?", (ex_name,))
            if row:
                ex_id = row[0]
            else:
                ex_id = create_exercise(ex_name)
                
            if is_time_based:
                execute("UPDATE exercises SET is_time_based = 1 WHERE id = ?", (ex_id,))
                
            te_id = add_exercise(tid, ex_id)
            for s in sets:
                if is_time_based:
                    add_set(te_id, None, None, time_minutes=s.get('time'))
                else:
                    add_set(te_id, s.get('reps'), s.get('weight'))
    else:
        tid = existing_tid
                
    wid = start_workout(date_str, tid)
    return tid, wid

def test_runner_progression_states():
    tid, wid = setup_workout("2025-05-01", [
        ("Bench", False, [{'reps': 10, 'weight': 100}, {'reps': 10, 'weight': 100}])
    ])
    
    prog = get_workout_progression(wid)
    assert not prog['is_completed']
    assert prog['state'] == "READY"
    assert prog['current_set']['set_number'] == 1
    
    # Start set 1
    start_set(wid, 1, 1)
    prog = get_workout_progression(wid)
    assert prog['state'] == "IN_SET"
    
    # Complete set 1
    complete_set(wid, 1, 1, 10, 100)
    prog = get_workout_progression(wid)
    assert prog['state'] == "REST"
    assert prog['current_set']['set_number'] == 2
    
    # Complete set 2
    complete_set(wid, 1, 2, 10, 100)
    prog = get_workout_progression(wid)
    assert prog['is_completed']
    
def test_progressive_overload_wrap_and_weight_reset():
    # Run workout 1 to establish baseline
    tid, wid1 = setup_workout("2025-06-01", [
        ("Squat", False, [{'reps': 5, 'weight': 200}, {'reps': 5, 'weight': 200}])
    ])
    complete_set(wid1, 1, 1, 5, 200)
    complete_set(wid1, 1, 2, 5, 200)
    complete_session(wid1)
    
    # Cursor initializes to 2.
    ex_id = query_one("SELECT id FROM exercises WHERE name = 'Squat'")[0]
    set_overload_cursor(tid, ex_id, 2)
    
    # Run workout 2 - target is set 2, 6 reps
    _, wid2 = setup_workout("2025-06-08", [], existing_tid=tid)
    
    # Complete set 1 first so it gets tracked in history
    complete_set(wid2, 1, 1, 5, 200)
    
    # Hit target on set 2 (reps exceeded)
    complete_set(wid2, 1, 2, 6, 200)
    
    # Cursor should advance backwards from 2 -> 1
    assert get_overload_cursor(tid, ex_id) == 1
    
    # Complete session
    complete_session(wid2)
    
    # Run workout 3 - target is set 1, 6 reps (because we hit 5 last time on set 1)
    # But let's increase the weight!
    _, wid3 = setup_workout("2025-06-15", [], existing_tid=tid)
    
    # We increase weight, even if reps drop. This should reset cursor to last set (2).
    complete_set(wid3, 1, 1, 4, 225) 
    
    # Cursor should reset to 2
    assert get_overload_cursor(tid, ex_id) == 2

def test_cardio_time_tracking():
    tid, wid = setup_workout("2025-07-01", [
        ("Cardio", True, [{'time': 15.0}])
    ])
    
    prog = get_workout_progression(wid)
    assert prog['active_exercise']['is_time_based'] is True
    
    # Complete with 20 minutes
    complete_set(wid, 1, 1, None, None, time_minutes=20.0)
    
    s1 = get_workout_set(wid, 1, 1)
    assert s1['actual_time_minutes'] == 20.0
    assert s1['actual_reps'] is None
    
    # Let's verify the Friday summary logic directly using the DB
    # We will simulate the same query app.py does.
    complete_session(wid)
    from db.conn import query_one
    from repos.runner_repo import complete_workout_session
    
    # We need to change the workout date to a Friday for the test query
    from db.conn import execute
    execute("UPDATE workouts SET date = '2026-05-15' WHERE id = ?", (wid,)) # 2026-05-15 is a Friday
    
    res = query_one("""
        SELECT SUM(s.actual_time_minutes)
        FROM sets s
        JOIN workout_exercises we ON s.workout_exercise_id = we.id
        JOIN workouts w ON we.workout_id = w.id
        JOIN exercises e ON we.exercise_id = e.id
        WHERE e.name = 'Cardio' 
          AND s.completed = 1
          AND w.date >= '2026-05-11' AND w.date <= '2026-05-15'
    """)
    
    assert res[0] == 20.0
