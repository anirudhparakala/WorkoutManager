from repos import runner_repo, templates_repo

class RunnerError(Exception):
    pass

def start_workout(date_str, template_id):
    """Starts a new workout session (snapshot)."""
    return runner_repo.start_workout_session(date_str, template_id)

def start_set(workout_id, exercise_order, set_number):
    """Starts the timer for a specific set."""
    target_set = runner_repo.get_workout_set(workout_id, exercise_order, set_number)
    if not target_set:
        raise RunnerError(f"Set not found: W:{workout_id} E:{exercise_order} S:{set_number}")
    
    runner_repo.start_set_timer(target_set['id'])
    return True

def complete_set(workout_id, exercise_order, set_number, actual_reps, actual_weight):
    """Marks a set as complete. Idempotent."""
    target_set = runner_repo.get_workout_set(workout_id, exercise_order, set_number)
    if not target_set:
        raise RunnerError(f"Set not found: W:{workout_id} E:{exercise_order} S:{set_number}")
    runner_repo.update_set_actuals(target_set['id'], actual_reps, actual_weight)
    
    # Sync to Template (Ticket 17)
    # 1. Need template_id. Get it from session.
    # Optimization: We could pass it in or fetch it. Fetching is safer.
    # We don't have a direct "get_workout(id)" in runner_repo tailored for this, 
    # but we can look up via SQL or assume we can get it from somewhere.
    # Let's add a quick helper or just queries.
    # Or rely on `get_active_session` if we know date? No, workout_id is specific.
    # Let's assume we can fetch workout row.
    from db.conn import query_one
    w_row = query_one("SELECT template_id FROM workouts WHERE id = ?", (workout_id,))
    if w_row and w_row[0]:
        template_id = w_row[0]
        templates_repo.update_template_set_match(template_id, exercise_order, set_number, actual_reps, actual_weight)
    
    return True

def update_completed_set(set_id, actual_reps, actual_weight):
    """Updates an already completed set."""
    runner_repo.update_set_actuals(set_id, actual_reps, actual_weight)
    
    # Sync to Template (Ticket 17)
    # We have set_id. Need to traverse back to workout -> template
    from db.conn import query_one
    row = query_one("""
        SELECT w.template_id, we.order_index, s.set_number
        FROM sets s
        JOIN workout_exercises we ON s.workout_exercise_id = we.id
        JOIN workouts w ON we.workout_id = w.id
        WHERE s.id = ?
    """, (set_id,))
    
    if row and row[0]: # ensure template_id exists (not None)
        templates_repo.update_template_set_match(row[0], row[1], row[2], actual_reps, actual_weight)

def complete_session(workout_id):
    """Finishes the session."""
    runner_repo.complete_workout_session(workout_id)

def get_workout_progression(workout_id):
    """
    Analyzes the full workout structure to determine:
    - Current Active Set (first incomplete).
    - History (list of completed sets for the current exercise).
    - Completion status.
    """
    exercises = runner_repo.get_workout_exercises_with_sets(workout_id)
    
    current_set = None
    active_exercise = None
    active_exercise_history = []
    is_completed = True
    
    # 1. Find the first incomplete set
    for ex in exercises:
        ex_completed = True
        for s in ex['sets']:
            if not s['completed']:
                if current_set is None:
                    current_set = s
                    active_exercise = ex
                    ex_completed = False
                    is_completed = False
                    # Don't break yet, we need to know if there are MORE sets? 
                    # Actually we just need the FIRST incomplete one.
                else:
                    is_completed = False # There are more incomplete sets
            
            # If we found the active exercise, collect its history (sets before the current one)
            if active_exercise and ex['id'] == active_exercise['id']:
                if s['completed']:
                    active_exercise_history.append(s)
        
        if not ex_completed and active_exercise and ex['id'] == active_exercise['id']:
            # We found our active exercise and set, break exercise loop? 
            # We need to continue checking is_completed for the rest? 
            # If we found an incomplete set, "is_completed" is definitely False.
            # But we want to ensure we don't overwrite current_set.
            pass
            
    # If no incomplete set found, is_completed remains True (if exercises existed)
    if not exercises:
        is_completed = False # Empty workout?
        
    # Calculate State & Timers
    state = "COMPLETED"
    timer_base = None # ISO string to count from
    
    if not is_completed and current_set:
        if current_set.get('started_at'):
            state = "IN_SET"
            timer_base = current_set['started_at']
        else:
            state = "READY" # Implies Rest if applicable
            # Find previous set for Rest Timer
            # We need to flatten or search history? 
            # simplest: traverse backwards from current_set
            # current_set is active_exercise set X.
            # Look at set X-1, or last set of previous exercise.
            
            # Helper to find last completed set
            last_completed = None
            found_current = False
            
            # Flatten sets for easier traversal
            all_sets = []
            for ex in exercises:
                for s in ex['sets']:
                    all_sets.append(s)
            
            for i, s in enumerate(all_sets):
                if s['id'] == current_set['id']:
                    if i > 0:
                        last_completed = all_sets[i-1]
                    break
            
            if last_completed and last_completed['completed_at']:
                state = "REST"
                timer_base = last_completed['completed_at']
            else:
                # First set of workout
                # We could use workout start time? 
                # Let's leave it None or handle in UI
                pass

    return {
        "is_completed": is_completed,
        "current_set": current_set,
        "active_exercise": active_exercise,
        "active_exercise_history": active_exercise_history,
        "total_exercises_count": len(exercises),
        "state": state,
        "timer_base": timer_base
    }

