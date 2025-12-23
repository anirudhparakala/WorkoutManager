import datetime
import pytz

TIMEZONE = pytz.timezone('America/New_York')

def now_et():
    """Returns current datetime in ET."""
    return datetime.datetime.now(TIMEZONE)

def today_str_et():
    """Returns current date in ET as YYYY-MM-DD."""
    return now_et().strftime('%Y-%m-%d')

def now_iso():
    """Returns current datetime in ISO format."""
    return now_et().isoformat()

def get_week_start(date_str):
    """Returns the Sunday of the week for the given date string (YYYY-MM-DD)."""
    dt = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    # weekday(): Mon=0, Sun=6. 
    # If today is Sunday (6), we want today.
    # If today is Monday (0), we want yesterday (-1).
    # We want Sunday to be the start.
    # (dt.weekday() + 1) % 7 gives: Sun=0, Mon=1, ..., Sat=6
    days_to_subtract = (dt.weekday() + 1) % 7
    start_date = dt - datetime.timedelta(days=days_to_subtract)
    return start_date.strftime('%Y-%m-%d')

def get_week_end(date_str):
    """Returns the Saturday of the week for the given date string (YYYY-MM-DD)."""
    start_date_str = get_week_start(date_str)
    start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = start_date + datetime.timedelta(days=6)
    return end_date.strftime('%Y-%m-%d')
