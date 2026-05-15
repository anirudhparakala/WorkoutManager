import libsql_client
import re
import os

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
        current_version = client.execute("SELECT MAX(version) FROM schema_version").rows[0][0] or 0
        if current_version < 7:
            print("Applying migration v7 (Cardio Time Tracking)...")
            client.execute("ALTER TABLE exercises ADD COLUMN is_time_based BOOLEAN DEFAULT 0")
            client.execute("ALTER TABLE template_sets ADD COLUMN time_minutes REAL")
            client.execute("ALTER TABLE sets ADD COLUMN planned_time_minutes REAL")
            client.execute("ALTER TABLE sets ADD COLUMN actual_time_minutes REAL")
            client.execute("INSERT OR IGNORE INTO exercises (name, notes, is_time_based) VALUES ('Cardio', 'Time-based cardio at the end of workout', 1)")
            client.execute("INSERT INTO schema_version (version) VALUES (7)")
            print("Migration v7 applied successfully.")
        else:
            print("Already at version 7+")
    finally:
        client.close()

if __name__ == '__main__':
    main()
