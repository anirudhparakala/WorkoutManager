import re
import libsql_client

def get_secrets():
    secrets = {}
    path = ".streamlit/secrets.toml"
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            m = re.match(r'^(TURSO_[A-Z_]+)\s*=\s*"(.*?)"', line.strip())
            if m:
                secrets[m.group(1)] = m.group(2)
    return secrets

def main():
    secrets = get_secrets()
    url = secrets.get("TURSO_DATABASE_URL")
    if url.startswith("libsql://"):
        url = url.replace("libsql://", "https://")
    token = secrets.get("TURSO_AUTH_TOKEN")
    
    client = libsql_client.create_client_sync(url, auth_token=token)
    try:
        # Get cardio ID
        cardio_row = client.execute("SELECT id FROM exercises WHERE name = 'Cardio'").rows
        if not cardio_row:
            print("Cardio not found. Did migrations run?")
            return
        cardio_id = cardio_row[0][0]
        
        # Get templates
        templates = client.execute("SELECT id, name FROM templates").rows
        for t in templates:
            tid = t[0]
            name = t[1]
            if "leg" not in name.lower():
                print(f"Adding Cardio to {name}...")
                
                # Check if cardio is already in this template
                existing = client.execute("SELECT id FROM template_exercises WHERE template_id = ? AND exercise_id = ?", [tid, cardio_id]).rows
                if existing:
                    print("Already exists. Skipping.")
                    continue
                
                # Find max order_index
                max_order = client.execute("SELECT MAX(order_index) FROM template_exercises WHERE template_id = ?", [tid]).rows[0][0]
                if max_order is None:
                    max_order = 0
                else:
                    max_order += 1
                
                # Insert template exercise
                res = client.execute("INSERT INTO template_exercises (template_id, exercise_id, order_index, sets, reps, weight) VALUES (?, ?, ?, 1, NULL, NULL) RETURNING id", [tid, cardio_id, max_order])
                te_id = res.rows[0][0]
                
                # Insert template set with default time of 15 minutes
                client.execute("INSERT INTO template_sets (template_exercise_id, set_number, time_minutes) VALUES (?, 1, 15)", [te_id])
                
        print("Done.")
    finally:
        client.close()

if __name__ == '__main__':
    main()
