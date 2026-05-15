import pytest
from services.planner_service import assign_workout, assign_rest, assign_off, get_week_schedule, PlannerError
from repos.templates_repo import create_template
from db.conn import execute

def test_assign_workout():
    tid = create_template("My Push Day")
    assign_workout("2025-01-01", tid)
    
    # We can use get_week_schedule to verify, but it gets the week relative to today.
    # Let's query the DB directly to verify.
    from repos.planner_repo import get_range
    plans = get_range("2025-01-01", "2025-01-01")
    
    assert len(plans) == 1
    assert plans[0]['date'] == "2025-01-01"
    assert plans[0]['plan_type'] == "WORKOUT"
    assert plans[0]['template_id'] == tid
    assert plans[0]['name'] == "My Push Day"

def test_assign_rest_and_off():
    assign_rest("2025-01-02")
    
    from repos.planner_repo import get_range
    plans = get_range("2025-01-02", "2025-01-02")
    assert len(plans) == 1
    assert plans[0]['plan_type'] == "REST"
    
    assign_off("2025-01-02")
    plans = get_range("2025-01-02", "2025-01-02")
    assert len(plans) == 0

def test_unique_date_constraint():
    """Verify that multiple assignments to the same date overwrite each other cleanly."""
    tid1 = create_template("Template 1")
    tid2 = create_template("Template 2")
    
    assign_workout("2025-01-03", tid1)
    
    # Second assignment should overwrite due to ON CONFLICT DO UPDATE
    assign_workout("2025-01-03", tid2)
    
    from repos.planner_repo import get_range
    plans = get_range("2025-01-03", "2025-01-03")
    
    assert len(plans) == 1
    assert plans[0]['template_id'] == tid2
    assert plans[0]['name'] == "Template 2"
    
    # Overwrite with REST
    assign_rest("2025-01-03")
    plans = get_range("2025-01-03", "2025-01-03")
    assert len(plans) == 1
    assert plans[0]['plan_type'] == "REST"
    assert plans[0]['template_id'] is None
