from db.conn import execute, query_one
from core.timeutil import today_str_et
import streamlit as st

# Verify we can access secrets
try:
    _ = st.secrets["TURSO_DATABASE_URL"]
except:
    print("Secrets not loaded automatically. Attempting manual load for script context.")
    import os, toml
    secrets_path = os.path.join(".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        with open(secrets_path, "r") as f:
             st.secrets = toml.load(f)

date_str = today_str_et()
print(f"Resetting workout for {date_str}...")

# 1. Get Workout ID
row = query_one("SELECT id FROM workouts WHERE date = ?", (date_str,))
if not row:
    print("No workout found for today.")
    exit()

workout_id = row[0]

# 2. Reset Workout Status
execute("""
    UPDATE workouts 
    SET status = 'PLANNED', started_at = NULL, completed_at = NULL 
    WHERE id = ?
""", (workout_id,))

# 3. Reset Sets
execute("""
    UPDATE sets 
    SET completed = 0, 
        actual_reps = planned_reps, 
        actual_weight = planned_weight,
        started_at = NULL,
        completed_at = NULL
    WHERE workout_exercise_id IN (
        SELECT id FROM workout_exercises WHERE workout_id = ?
    )
""", (workout_id,))

print("Success! Workout reset to PLANNED.")
import os
os._exit(0)
