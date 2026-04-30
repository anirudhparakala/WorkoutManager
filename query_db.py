import os
import sys
from datetime import datetime, timedelta

# Add current dir to path to import db
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db.conn import query_all

query = """
SELECT 
    w.date, 
    w.name,
    w.status,
    e.name as exercise,
    s.planned_weight,
    s.actual_weight,
    s.planned_reps
FROM workouts w
JOIN workout_exercises we ON w.id = we.workout_id
JOIN exercises e ON we.exercise_id = e.id
JOIN sets s ON we.id = s.workout_exercise_id
WHERE w.date >= date('now', 'localtime', '-7 days')
  AND w.date <= date('now', 'localtime', '+7 days')
  AND w.status != 'STALE'
ORDER BY w.date, we.order_index, s.set_number
"""

rows = query_all(query)
print(f"Found {len(rows)} sets")
for r in rows[:10]:
    print(r)
