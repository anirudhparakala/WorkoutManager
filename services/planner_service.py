from repos import planner_repo
from services import templates_service
from core.timeutil import get_week_start, get_week_end

class PlannerError(Exception):
    pass

def assign_workout(date_str, template_id):
    """Assigns a workout template to a date."""
    # Check for active session
    plan = planner_repo.get_day_plan(date_str)
    if plan and plan['status'] == 'ACTIVE':
        raise PlannerError("Cannot change plan: An active session exists for this date.")
    
    # Get template name
    template = templates_service.get_template(template_id)
    if not template:
        raise PlannerError("Template not found.")
    
    planner_repo.upsert_day_plan(date_str, 'WORKOUT', template_id, template['name'])

def assign_rest(date_str):
    """Assigns a rest day to a date."""
    # Check for active session
    plan = planner_repo.get_day_plan(date_str)
    if plan and plan['status'] == 'ACTIVE':
        raise PlannerError("Cannot change plan: An active session exists for this date.")
    
    planner_repo.upsert_day_plan(date_str, 'REST', None, "Rest Day")

def assign_off(date_str):
    """Removes any plan from a date."""
    # Check for active session
    plan = planner_repo.get_day_plan(date_str)
    if plan and plan['status'] == 'ACTIVE':
        raise PlannerError("Cannot change plan: An active session exists for this date.")
    
    planner_repo.delete_day_plan(date_str)


def get_day_plan(date_str):
    return planner_repo.get_day_plan(date_str)

def get_week_schedule(date_str):
    """Returns the schedule for the week containing the date."""
    start = get_week_start(date_str)
    end = get_week_end(date_str)
    return planner_repo.get_range(start, end)
