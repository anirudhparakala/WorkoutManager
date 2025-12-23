import streamlit as st
import calendar
import datetime
from core.timeutil import today_str_et
from repos.planner_repo import get_range

st.set_page_config(page_title="Calendar", page_icon="📅", layout="wide")

from core.security import require_login
require_login()

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
kpi1.metric("Planned Days", planned_days)
kpi2.metric("Planned Workouts", planned_workouts)
kpi3.metric("Completed", completed_workouts)
kpi4.metric("Remaining", remaining_workouts)
kpi5.metric("Consistency Streak", f"🔥 {current_streak}")

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
    st.button("<", on_click=prev_month)
with col4:
    st.button(">", on_click=next_month)

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
# calendar.monthcalendar returns list of weeks (lists of 7 days). 0 means other month.
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
                
                # Card Styling
                # We can't style individual containers easily in Streamlit without CSS hacks,
                # but we can use st.info/success/warning as the container background implicitly.
                
                label = f"**{day_num}**"
                
                if plan:
                    if plan['plan_type'] == 'WORKOUT':
                        status = plan.get('status', 'PLANNED')
                        if status == 'COMPLETED':
                            st.success(f"{label}\n\n✅ {plan['name']}")
                        elif status == 'ACTIVE':
                            st.warning(f"{label}\n\n⚡ {plan['name']}")
                        else:
                            st.info(f"{label}\n\n🏋️ {plan['name']}")
                    elif plan['plan_type'] == 'REST':
                         # Using a neutral container? selection is limited. 
                         # st.secondary is not a thing. st.markdown with style maybe?
                         # Let's use st.success for rest but maybe different icon.
                         st.markdown(f"""
                            <div style="background-color: #f0f2f6; color: #31333f; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                                {label}<br><br>💤 Rest
                            </div>
                         """, unsafe_allow_html=True)
                else:
                    # Empty day
                    st.markdown(f"""
                        <div style="padding: 10px; opacity: 0.5;">
                            {label}
                        </div>
                    """, unsafe_allow_html=True)
    
    st.divider() # Separator between weeks
