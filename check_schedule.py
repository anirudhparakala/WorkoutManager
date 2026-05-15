import libsql_client
import re
import datetime

secrets={}
with open('.streamlit/secrets.toml', encoding='utf-8') as f:
    for line in f:
        m = re.match(r'^(TURSO_[A-Z_]+)\s*=\s*"(.*?)"', line.strip())
        if m:
            secrets[m.group(1)] = m.group(2)

client = libsql_client.create_client_sync(
    secrets['TURSO_DATABASE_URL'].replace('libsql://', 'https://'), 
    auth_token=secrets['TURSO_AUTH_TOKEN']
)

rows = client.execute("SELECT date, name, plan_type FROM workouts WHERE date >= '2025-12-22' AND date <= '2025-12-28' ORDER BY date").rows
client.close()

days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
for r in rows:
    dt = datetime.datetime.strptime(r[0], '%Y-%m-%d')
    day_name = days[dt.weekday()]
    if r[2] == 'WORKOUT':
        print(f"{day_name}: {r[1]}")
    else:
        print(f"{day_name}: Rest Day")
