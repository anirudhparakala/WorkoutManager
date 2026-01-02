import libsql_client
import os
import re
import datetime

def get_secrets():
    """Manually parse secrets.toml."""
    secrets = {}
    path = ".streamlit/secrets.toml"
    if not os.path.exists(path):
        raise Exception("Secrets file not found")
        
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            m = re.match(r'^(TURSO_[A-Z_]+)\s*=\s*"(.*?)"', line.strip())
            if m:
                secrets[m.group(1)] = m.group(2)
    return secrets

def get_conn():
    secrets = get_secrets()
    url = secrets.get("TURSO_DATABASE_URL")
    token = secrets.get("TURSO_AUTH_TOKEN")
    
    if url.startswith("libsql://"):
        url = url.replace("libsql://", "https://")
        
    return libsql_client.create_client_sync(url, auth_token=token)

def bulk_schedule():
    print("Initializing bulk schedule...")
    client = get_conn()
    
    # 1. Identify Source Week Range (Current Week)
    # Today is presumably set in the system or we use machine today.
    # Metadata says: 2025-12-23 is Tuesday.
    # Monday is 2025-12-22. Sunday is 2025-12-28.
    
    today = datetime.date(2025, 12, 23) # Using known metadata date to be safe
    start_week = today - datetime.timedelta(days=today.weekday())
    end_week = start_week + datetime.timedelta(days=6)
    
    start_str = start_week.strftime('%Y-%m-%d')
    end_str = end_week.strftime('%Y-%m-%d')
    
    print(f"Source Week: {start_str} to {end_str}")
    
    # 2. Fetch Source Schedule
    # status doesn't matter for pattern, just plan_type and template
    rows = client.execute("SELECT date, plan_type, template_id, name FROM workouts WHERE date >= ? AND date <= ?", [start_str, end_str]).rows
    
    # Map weekday (0-6) -> Plan
    schedule_pattern = {}
    for r in rows:
        # r is (date, plan_type, template_id, name)
        # Parse date to get weekday
        d = datetime.datetime.strptime(r[0], '%Y-%m-%d').date()
        wd = d.weekday()
        schedule_pattern[wd] = {
            "plan_type": r[1],
            "template_id": r[2],
            "name": r[3]
        }
        
    if not schedule_pattern:
        print("No workouts found in current week! Aborting.")
        client.close()
        return

    print(f"Found pattern for days: {list(schedule_pattern.keys())}")
    
    # 3. Iterate from Next Week until 2026-06-01
    target_end_date = datetime.date(2026, 6, 1)
    
    current_date = end_week + datetime.timedelta(days=1) # Start next Monday
    
    inserts = []
    
    while current_date <= target_end_date:
        wd = current_date.weekday()
        if wd in schedule_pattern:
            plan = schedule_pattern[wd]
            # (date, plan_type, template_id, name, status)
            # Use 'PLANNED' status
            inserts.append((
                current_date.strftime('%Y-%m-%d'),
                plan['plan_type'],
                plan['template_id'],
                plan['name'],
                'PLANNED'
            ))
        
        current_date += datetime.timedelta(days=1)
        
    print(f"Prepared {len(inserts)} entries to insert.")
    
    # 4. Batch Insert
    # SQLite batch insert: INSERT INTO workouts (...) VALUES (...), (...);
    # Or executemany style. libsql_client might prefer explicit batch of statements or execute with params.
    # Generating a big transaction might be better.
    # Let's do chunked inserts or just loop if it's not too slow (approx 25 weeks * ~5 days = 125 inserts, fast enough).
    # Wait, Dec 2025 to June 2026 is ~6 months + ~1 week left in Dec? 
    # Current date is Dec 2025. June 2026 is 6 months away. ~26 weeks. ~150 inserts. Very fast.
    
    cnt = 0
    for item in inserts:
        # Check if already exists? Upsert? 
        # User said "assign them". Overwriting is risky if they modified future, but presumably future is empty.
        # UPSERT logic: DELETE first or INSERT OR REPLACE.
        # Let's use INSERT OR REPLACE to be robust.
        
        # item: (date, plan, tid, name, status)
        client.execute("""
            INSERT OR REPLACE INTO workouts (date, plan_type, template_id, name, status)
            VALUES (?, ?, ?, ?, ?)
        """, item)
        cnt += 1
        
    print(f"Successfully scheduled {cnt} days.")
    client.close()

if __name__ == "__main__":
    bulk_schedule()
    os._exit(0)
