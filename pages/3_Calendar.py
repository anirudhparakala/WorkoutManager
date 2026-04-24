import streamlit as st
import calendar
import datetime
from core.timeutil import today_str_et
from repos.planner_repo import get_range

st.set_page_config(page_title="Calendar", page_icon="📅", layout="wide")

from core.security import require_login
require_login()

# --- Monochrome CSS ---
st.markdown("""
<style>
    .stAlert > div[data-testid="stNotification"] {
        background-color: #1a1a1a !important;
        border-color: #333 !important;
        color: #e0e0e0 !important;
    }
    hr { border-color: #222 !important; }
    div[data-testid="stMetric"] label { color: #888 !important; }
    .cal-workout-done {
        background-color: #1a1a1a; color: #ccc; padding: 10px; border-radius: 6px;
        border-left: 3px solid #555; margin-bottom: 8px;
    }
    .cal-workout-active {
        background-color: #1a1a1a; color: #ccc; padding: 10px; border-radius: 6px;
        border-left: 3px solid #888; margin-bottom: 8px;
    }
    .cal-workout-planned {
        background-color: #141414; color: #999; padding: 10px; border-radius: 6px;
        border-left: 3px solid #333; margin-bottom: 8px;
    }
    .cal-rest {
        background-color: #111; color: #666; padding: 10px; border-radius: 6px;
        margin-bottom: 8px;
    }
    .cal-empty {
        padding: 10px; opacity: 0.3;
    }
</style>
""", unsafe_allow_html=True)

st.title("Calendar")

from services.consistency_service import calculate_current_streak

# --- Weekly KPI Panel ---
today_dt = datetime.datetime.strptime(today_str_et(), '%Y-%m-%d')
week_start = today_dt - datetime.timedelta(days=today_dt.weekday())
week_end = week_start + datetime.timedelta(days=6)

week_plans = get_range(week_start.strftime('%Y-%m-%d'), week_end.strftime('%Y-%m-%d'))

planned_days = len(week_plans)
planned_workouts = sum(1 for p in week_plans if p['plan_type'] == 'WORKOUT')
completed_workouts = sum(1 for p in week_plans if p['plan_type'] == 'WORKOUT' and p.get('status') == 'COMPLETED')
remaining_workouts = max(0, planned_workouts - completed_workouts)

# Streak
current_streak = calculate_current_streak(today_str_et())

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("Planned", planned_days)
kpi2.metric("Workouts", planned_workouts)
kpi3.metric("Done", completed_workouts)
kpi4.metric("Remaining", remaining_workouts)
kpi5.metric("Streak", f"{current_streak}w")

st.divider()

# --- State Management (Month Navigation) ---
if "cal_year" not in st.session_state:
    today = datetime.datetime.strptime(today_str_et(), '%Y-%m-%d')
    st.session_state["cal_year"] = today.year
    st.session_state["cal_month"] = today.month

def prev_month():
    if st.session_state["cal_month"] == 1:
        st.session_state["cal_month"] = 12
        st.session_state["cal_year"] -= 1
    else:
        st.session_state["cal_month"] -= 1

def next_month():
    if st.session_state["cal_month"] == 12:
        st.session_state["cal_month"] = 1
        st.session_state["cal_year"] += 1
    else:
        st.session_state["cal_month"] += 1

def go_today():
    today = datetime.datetime.strptime(today_str_et(), '%Y-%m-%d')
    st.session_state["cal_year"] = today.year
    st.session_state["cal_month"] = today.month

# --- Navigation Header ---
col1, col2, col3, col4 = st.columns([1, 2, 0.5, 0.5])
with col1:
    st.button("Today", on_click=go_today)
with col3:
    st.button("‹", on_click=prev_month)
with col4:
    st.button("›", on_click=next_month)

current_year = st.session_state["cal_year"]
current_month = st.session_state["cal_month"]
month_name = calendar.month_name[current_month]

with col2:
    st.markdown(f"### {month_name} {current_year}")

# --- Fetch Data ---
# Get first and last day of month
_, last_day = calendar.monthrange(current_year, current_month)
start_date = f"{current_year}-{current_month:02d}-01"
end_date = f"{current_year}-{current_month:02d}-{last_day:02d}"

plans = get_range(start_date, end_date)
plans_map = {p['date']: p for p in plans}

# --- Render Grid ---
# Days Header
cols = st.columns(7)
days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
for i, day in enumerate(days):
    cols[i].write(f"**{day}**")

# Calendar Matrix
cal_matrix = calendar.monthcalendar(current_year, current_month)

for week in cal_matrix:
    cols = st.columns(7)
    for i, day_num in enumerate(week):
        with cols[i]:
            if day_num == 0:
                st.write("") # Empty cell
            else:
                current_date_str = f"{current_year}-{current_month:02d}-{day_num:02d}"
                plan = plans_map.get(current_date_str)
                
                label = f"<span style='font-weight:700;font-size:1rem'>{day_num}</span>"
                
                if plan:
                    if plan['plan_type'] == 'WORKOUT':
                        status = plan.get('status', 'PLANNED')
                        if status == 'COMPLETED':
                            st.markdown(f"<div class='cal-workout-done'>{label}<br><small>✓ {plan['name']}</small></div>", unsafe_allow_html=True)
                        elif status == 'ACTIVE':
                            st.markdown(f"<div class='cal-workout-active'>{label}<br><small>● {plan['name']}</small></div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<div class='cal-workout-planned'>{label}<br><small>{plan['name']}</small></div>", unsafe_allow_html=True)
                    elif plan['plan_type'] == 'REST':
                         st.markdown(f"<div class='cal-rest'>{label}<br><small>rest</small></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='cal-empty'>{label}</div>", unsafe_allow_html=True)
    
    st.divider()
