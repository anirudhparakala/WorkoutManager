import pytest
from services.templates_service import (
    create_template, get_template, add_exercise, add_set, 
    update_set, reorder_exercises, ValidationError
)
from repos.exercises_repo import create_exercise

def test_template_creation():
    tid = create_template("My Push Day")
    tpl = get_template(tid)
    assert tpl is not None
    assert tpl['name'] == "My Push Day"
    assert len(tpl['exercises']) == 0

def test_template_validation():
    with pytest.raises(ValidationError):
        create_template("")
        
    with pytest.raises(ValidationError):
        create_template("   ")

def test_add_exercise_and_sets():
    tid = create_template("Leg Day")
    ex_id = create_exercise("Squat")
    
    # Use actual exercise id
    te_id = add_exercise(tid, ex_id)
    
    # Add sets
    add_set(te_id, 10, 135)
    add_set(te_id, 8, 185)
    
    tpl = get_template(tid)
    assert len(tpl['exercises']) == 1
    ex = tpl['exercises'][0]
    assert ex['name'] == "Squat"
    assert len(ex['sets']) == 2
    
    assert ex['sets'][0]['set_number'] == 1
    assert ex['sets'][0]['reps'] == 10
    assert ex['sets'][0]['weight'] == 135
    
    assert ex['sets'][1]['set_number'] == 2
    assert ex['sets'][1]['reps'] == 8
    assert ex['sets'][1]['weight'] == 185

def test_reorder_exercises():
    tid = create_template("Full Body")
    ex1 = create_exercise("Squat")
    ex2 = create_exercise("Bench")
    ex3 = create_exercise("Deadlift")
    
    te1 = add_exercise(tid, ex1) # Squat
    te2 = add_exercise(tid, ex2) # Bench
    te3 = add_exercise(tid, ex3) # Deadlift
    
    # Current order: Squat, Bench, Deadlift
    tpl = get_template(tid)
    assert tpl['exercises'][0]['exercise_id'] == ex1
    assert tpl['exercises'][2]['exercise_id'] == ex3
    
    # Reorder to: Deadlift, Squat, Bench
    reorder_exercises(tid, [te3, te1, te2])
    
    tpl = get_template(tid)
    assert tpl['exercises'][0]['exercise_id'] == ex3
    assert tpl['exercises'][1]['exercise_id'] == ex1
    assert tpl['exercises'][2]['exercise_id'] == ex2

def test_set_validation():
    tid = create_template("Test")
    ex_id = create_exercise("Curl")
    te = add_exercise(tid, ex_id)
    
    with pytest.raises(ValidationError, match="Reps must be at least 1."):
        add_set(te, 0, 50)
        
    with pytest.raises(ValidationError, match="Weight cannot be negative."):
        add_set(te, 10, -5)
