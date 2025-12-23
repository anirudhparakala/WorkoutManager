from repos import planner_repo
import datetime
from core.timeutil import get_week_start

def check_week_consistency(week_plans):
    """
    Determines if a week's plan (list of workouts) meets the consistency criteria:
    1. At least 1 Rest Day (plan_type='REST').
    2. All 'WORKOUT' plans are 'COMPLETED'.
    
    If strict adherence is required, we might also check if planned days were actually done on that day,
    but checking status='COMPLETED' is usually sufficient for "Did I do my workouts?".
    """
    
    has_rest = False
    all_workouts_done = True
    workout_count = 0
    
    for p in week_plans:
        if p['plan_type'] == 'REST':
            has_rest = True
        elif p['plan_type'] == 'WORKOUT':
            workout_count += 1
            if p.get('status') != 'COMPLETED':
                all_workouts_done = False
                
    # If no workouts planned, is it consistent? 
    # Usually "Zero Days" weeks are not streaks.
    # Let's assume at least 1 workout required to count as a "Training Week".
    # Or just rest rule? 
    # Let's say: Streak requires >0 completed workouts AND adherence to rules.
    
    if workout_count == 0:
        return False 
        
    return has_rest and all_workouts_done

def calculate_current_streak(today_str):
    """
    Calculates consecutive consistent weeks ending at the most recently completed full week.
    """
    current_date = datetime.datetime.strptime(today_str, '%Y-%m-%d')
    
    # Start looking from "Last Week".
    # We find the Monday of the CURRENT week, then subtract 7 days to get Monday of PREVIOUS week.
    current_week_monday = current_date - datetime.timedelta(days=current_date.weekday())
    search_monday = current_week_monday - datetime.timedelta(days=7)
    
    streak = 0
    
    # We will loop backward for up to 52 weeks (1 year) cap to prevent infinite or slow loops 
    # if database is huge (not likely an issue here).
    for _ in range(52):
        week_start = search_monday.strftime('%Y-%m-%d')
        week_end = (search_monday + datetime.timedelta(days=6)).strftime('%Y-%m-%d')
        
        week_plans = planner_repo.get_range(week_start, week_end)
        
        if check_week_consistency(week_plans):
            streak += 1
            search_monday -= datetime.timedelta(days=7)
        else:
            break
            
    return streak
