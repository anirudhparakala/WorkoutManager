import libsql_client
import os
import re

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

def clear_data():
    print("Clearing trial data...")
    client = get_conn()
    
    # Batch delete
    stmts = [
        "DELETE FROM sets",
        "DELETE FROM workout_exercises",
        "DELETE FROM workouts",
        "DELETE FROM template_sets",
        "DELETE FROM template_exercises",
        "DELETE FROM templates"
    ]
    
    try:
        # libsql client batch expects list of statement strings or objects
        client.batch(stmts)
        print("Deleted all workout history and templates.")
    finally:
        client.close()
    
    print("Done. Exercise library preserved.")

if __name__ == "__main__":
    clear_data()
