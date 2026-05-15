import os
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

def run_migrations(client):
    print("Running migrations...")
    client.execute('''
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    
    current_version = client.execute("SELECT MAX(version) FROM schema_version").rows[0][0] or 0
    print(f"Current version: {current_version}")
    
    if current_version < 6:
        print("Applying migration v6...")
        client.execute("""
            DELETE FROM workouts
            WHERE id NOT IN (
                SELECT id FROM (
                    SELECT id, ROW_NUMBER() OVER (
                        PARTITION BY date
                        ORDER BY 
                            CASE status WHEN 'COMPLETED' THEN 1 WHEN 'ACTIVE' THEN 2 ELSE 3 END,
                            id DESC
                    ) as rn
                    FROM workouts
                ) WHERE rn = 1
            )
        """)
        client.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_workouts_date_unique ON workouts(date)")
        client.execute("INSERT INTO schema_version (version) VALUES (6)")
        print("Migration v6 applied successfully.")

def update_schedule(client):
    print("Fetching templates...")
    templates = client.execute("SELECT id, name FROM templates").rows
    upper_mixed_id = None
    accessory_day_id = None
    
    for t in templates:
        tid = t[0]
        name = t[1].lower()
        if 'upper' in name and 'mixed' in name:
            upper_mixed_id = tid
        if 'accessory' in name:
            accessory_day_id = tid
            
    if upper_mixed_id:
        print(f"Assigning Upper Mixed to Thursday (2025-12-25)")
        client.execute('''
            INSERT INTO workouts (date, plan_type, template_id, name, status)
            VALUES (?, 'WORKOUT', ?, 'Upper Mixed', 'PLANNED')
            ON CONFLICT(date) DO UPDATE SET
                plan_type = excluded.plan_type,
                template_id = excluded.template_id,
                name = excluded.name,
                status = excluded.status
        ''', ['2025-12-25', upper_mixed_id])
        
    if accessory_day_id:
        print(f"Assigning Accessory Day to Friday (2025-12-26)")
        client.execute('''
            INSERT INTO workouts (date, plan_type, template_id, name, status)
            VALUES (?, 'WORKOUT', ?, 'Accessory Day', 'PLANNED')
            ON CONFLICT(date) DO UPDATE SET
                plan_type = excluded.plan_type,
                template_id = excluded.template_id,
                name = excluded.name,
                status = excluded.status
        ''', ['2025-12-26', accessory_day_id])

def main():
    secrets = get_secrets()
    url = secrets.get("TURSO_DATABASE_URL")
    if url.startswith("libsql://"):
        url = url.replace("libsql://", "https://")
    token = secrets.get("TURSO_AUTH_TOKEN")
    
    client = libsql_client.create_client_sync(url, auth_token=token)
    try:
        run_migrations(client)
        update_schedule(client)
    finally:
        client.close()

if __name__ == '__main__':
    main()
