import os
import sys
from collections import defaultdict
import libsql_client

def get_db_credentials():
    secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
    
    url = ""
    token = ""
    with open(secrets_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("TURSO_DATABASE_URL"):
                url = line.split("=")[1].strip().strip('"').strip("'")
            elif line.startswith("TURSO_AUTH_TOKEN"):
                token = line.split("=")[1].strip().strip('"').strip("'")
    
    if url.startswith("libsql://"):
        url = url.replace("libsql://", "https://")
        
    return url, token

def main():
    url, token = get_db_credentials()
    if not url or not token:
        print("Error: Could not read database credentials from .streamlit/secrets.toml")
        return

    query = """
    SELECT 
        w.date, 
        w.name,
        e.name as exercise,
        s.set_number,
        s.planned_weight,
        s.actual_weight,
        s.planned_reps,
        s.actual_reps,
        w.status
    FROM workouts w
    JOIN workout_exercises we ON w.id = we.workout_id
    JOIN exercises e ON we.exercise_id = e.id
    JOIN sets s ON we.id = s.workout_exercise_id
    WHERE w.date >= '2026-04-20'
      AND w.date <= '2026-04-25'
      AND w.status IN ('PLANNED', 'ACTIVE', 'COMPLETED')
      AND w.plan_type = 'WORKOUT'
      AND w.template_id IS NOT NULL -- filter out random unassigned stuff
    ORDER BY w.date, we.order_index, s.set_number
    """
    
    client = libsql_client.create_client_sync(url, auth_token=token)
    try:
        result = client.execute(query)
        rows = result.rows
    finally:
        client.close()
    
    if not rows:
        print("No planned/completed workouts found for the recent week.")
        return

    # Group by Date -> Workout -> Exercise -> Sets
    schedule = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    
    for r in rows:
        date_str = r[0]
        workout_name = r[1]
        exercise_name = r[2]
        set_num = r[3]
        p_weight = r[4]
        a_weight = r[5]
        p_reps = r[6]
        a_reps = r[7]
        status = r[8]
        
        workout_key = f"{workout_name} ({status})"
        schedule[date_str][workout_key][exercise_name].append((set_num, p_weight, a_weight, p_reps, a_reps))

    output_file = "weekly_plan.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# Your Weekly Plan (4/20/26 - 4/25/26)\n\n")
        for date, workouts in sorted(schedule.items()):
            f.write(f"## {date}\n")
            for workout_name, exercises in workouts.items():
                f.write(f"### {workout_name}\n\n")
                for exercise_name, sets in exercises.items():
                    set_details = []
                    for s in sets:
                        # s is (set_num, p_weight, a_weight, p_reps, a_reps)
                        weight_val = s[2] if s[2] is not None else s[1]
                        reps_val = s[4] if s[4] is not None else s[3]
                        
                        weight_str = f"{weight_val}lbs" if weight_val else "BW"
                        reps_str = f"{reps_val}" if reps_val else "?"
                        set_details.append(f"{weight_str}x{reps_str}")
                    
                    f.write(f"- **{exercise_name}**: {', '.join(set_details)}\n")
                f.write("\n")
                
    print(f"Plan successfully saved to {output_file}")
                
if __name__ == "__main__":
    main()
