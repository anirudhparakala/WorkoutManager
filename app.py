import streamlit as st
import streamlit.components.v1 as components
import datetime
from services.planner_service import get_day_plan, PlannerError
from services.templates_service import get_template, update_set, reorder_exercises, ValidationError
from services import runner_service
from repos.runner_repo import get_active_session 
from core.timeutil import today_str_et

st.set_page_config(
    page_title="Workout Manager",
    page_icon="💪",
    layout="wide"
)

from core.security import require_login
require_login()

# Run migrations
from db.migrations import migrate
migrate()

# --- Custom CSS: Monochrome overrides ---
st.markdown("""
<style>
    /* Override Streamlit's colorful alert boxes to monochrome */
    .stAlert > div[data-testid="stNotification"] {
        background-color: #1a1a1a !important;
        border-color: #333 !important;
        color: #e0e0e0 !important;
    }
    
    /* Subtle borders on containers */
    div[data-testid="stExpander"] {
        border-color: #222 !important;
    }
    
    /* Cleaner dividers */
    hr {
        border-color: #222 !important;
    }
    
    /* Ghost text styling for "last time" display */
    .ghost-text {
        color: #555;
        font-size: 0.8rem;
        font-style: italic;
        margin-top: -8px;
        padding-left: 2px;
    }
    
    /* Overload suggestion styling */
    .overload-badge {
        color: #aaa;
        font-weight: 600;
        font-size: 0.85rem;
    }
    
    /* Monochrome metrics */
    div[data-testid="stMetric"] label {
        color: #888 !important;
    }
    
    /* Buttons - cleaner */
    .stButton > button {
        border-color: #333 !important;
    }
    .stButton > button[kind="primary"] {
        background-color: #fff !important;
        color: #000 !important;
        border-color: #fff !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #ddd !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Helpers ---
def render_timer(label, start_time_iso, key_prefix="timer"):
    """Injects a client-side JS timer using an iframe component. Monochrome design."""
    if not start_time_iso:
        return
    
    # Clean and parse time
    try:
        safe_iso = start_time_iso.replace(" ", "T")
        dt = datetime.datetime.fromisoformat(safe_iso)
        start_ts_ms = int(dt.timestamp() * 1000)
    except Exception as e:
        st.error(f"Timer Error: {e}")
        return
    
    # Use HTML Component (Iframe) to guarantee JS execution
    html_code = f"""
    <!DOCTYPE html>
    <html style="margin: 0; padding: 0; overflow: hidden;">
    <head>
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
            margin: 0; 
            padding: 0; 
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100%;
            background-color: transparent; 
        }}
        .timer-box {{
            border: 1px solid #333; 
            border-radius: 8px; 
            padding: 10px; 
            background-color: #111; 
            width: 100%; 
            text-align: center;
            box-sizing: border-box;
        }}
        .timer-label {{
            color: #666; 
            text-transform: uppercase; 
            font-weight: bold; 
            font-size: 0.7rem;
            letter-spacing: 0.05em;
            margin-bottom: 4px;
        }}
        .timer-val {{
            font-size: 24px; 
            font-family: monospace; 
            font-weight: bold; 
            color: #e0e0e0;
        }}
    </style>
    </head>
    <body>
        <div class="timer-box">
            <div class="timer-label">{label}</div>
            <div id="timer_val" class="timer-val">-:--:--</div>
        </div>
        <script>
            var start = {start_ts_ms}; 
            var el = document.getElementById("timer_val");
            
            function update() {{
                var now = new Date().getTime();
                var diff = now - start;
                if (diff < 0) diff = 0;
                
                var h = Math.floor(diff / (1000 * 60 * 60));
                var m = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
                var s = Math.floor((diff % (1000 * 60)) / 1000);
                
                m = (m < 10) ? "0" + m : m;
                s = (s < 10) ? "0" + s : s;
                
                el.innerText = h + ":" + m + ":" + s;
            }}
            
            setInterval(update, 1000);
            update();
        </script>
    </body>
    </html>
    """
    
    # Render component with fixed height to match content
    components.html(html_code, height=85)


def get_last_time_data(workout_id):
    """Fetches last completed workout data for inline 'last time' display."""
    from db.conn import query_one
    w_row = query_one("SELECT template_id FROM workouts WHERE id = ?", (workout_id,))
    if not w_row or not w_row[0]:
        return {}
    
    from repos.runner_repo import get_last_completed_workout_for_template
    last_exercises = get_last_completed_workout_for_template(w_row[0], exclude_workout_id=workout_id)
    if not last_exercises:
        return {}
    
    # Build lookup: (exercise_id, set_number) -> {actual_reps, actual_weight}
    lookup = {}
    for ex in last_exercises:
        for s in ex['sets']:
            if s['completed'] and s['actual_reps'] is not None:
                lookup[(ex['exercise_id'], s['set_number'])] = {
                    'reps': s['actual_reps'],
                    'weight': s['actual_weight']
                }
    return lookup


# --- Header ---
today_str = today_str_et()
display_date = datetime.datetime.strptime(today_str, '%Y-%m-%d').strftime('%A, %b %d')

st.title(f"Today: {display_date}")

# --- Check for Active Session (Snapshot) ---
active_session = get_active_session(today_str)

if active_session:
    # --- ACTIVE RUNNER MODE ---
    st.markdown(f"**Active Session:** {active_session['name']}")
    
    if active_session['status'] == 'COMPLETED':
        st.markdown("### ✓ Workout Completed")
    else:
        # Fetch Progression
        progression = runner_service.get_workout_progression(active_session['id'])
        
        if progression['is_completed']:
            st.markdown("### All sets completed")
            
            # Calculate Total Duration
            if active_session.get('started_at'):
                try:
                    start_dt = datetime.datetime.fromisoformat(active_session['started_at'].replace(" ", "T"))
                    end_dt = datetime.datetime.now()
                    duration = end_dt - start_dt
                    
                    # Format as H:M:S
                    total_seconds = int(duration.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    
                    time_str = f"{minutes}m {seconds}s"
                    if hours > 0:
                        time_str = f"{hours}h {time_str}"
                    
                    st.metric("Total Workout Time", time_str)
                except Exception as e:
                    st.warning(f"Could not calculate duration: {e}")

            if st.button("Finish Workout & Save", type="primary"):
                runner_service.complete_session(active_session['id'])
                st.rerun()
        else:
            current_set = progression['current_set']
            active_ex = progression['active_exercise']
            state = progression['state'] # READY, IN_SET, REST
            
            # --- Progressive Overload Targets ---
            overload_targets = runner_service.get_progressive_overload_targets(active_session['id'])
            overload_key = (active_ex['exercise_id'], current_set['set_number'])
            overload = overload_targets.get(overload_key)
            
            # --- "Last Time" Data ---
            last_time_data = get_last_time_data(active_session['id'])
            last_time_key = (active_ex['exercise_id'], current_set['set_number'])
            last_time = last_time_data.get(last_time_key)
            
            # --- Workout Timer ---
            if active_session['started_at']:
                 render_timer("Total Workout Time", active_session['started_at'], key_prefix="workout_total")

            # --- Runner Card ---
            with st.container():
                st.markdown(f"### {active_ex['name']}")
                st.caption(f"Set {current_set['set_number']} · {state}")
                
                # --- "Last Time" ghost text ---
                if last_time:
                    st.markdown(f"<div class='ghost-text'>last time: {last_time['reps']} × {last_time['weight']} lbs</div>", unsafe_allow_html=True)
                
                # --- State Machine UI ---
                if state == "READY" or state == "REST":
                    # Show Rest Timer if applicable
                    if progression.get('timer_base'):
                         render_timer("Rest", progression['timer_base'], key_prefix="rest_timer")
                    
                    if overload:
                        st.markdown(f"**Target: {overload['suggested_reps']} reps ⬆ (was {overload['last_reps']}) @ {current_set['planned_weight']} lbs**")
                    else:
                        st.markdown(f"**Target: {current_set['planned_reps']} reps @ {current_set['planned_weight']} lbs**")
                    
                    if st.button(f"Start Set {current_set['set_number']}", type="primary", use_container_width=True):
                        # Start Timer
                        runner_service.start_set(
                            active_session['id'],
                            active_ex['order_index'],
                            current_set['set_number']
                        )
                        st.rerun()
                        
                elif state == "IN_SET":
                    # Show Set Timer
                    render_timer("Set Duration", progression['timer_base'], key_prefix="set_timer")
                
                    c1, c2, c3 = st.columns([2, 2, 2])
                    
                    # Defaults — use overload suggestion if available
                    if overload:
                        default_reps = overload['suggested_reps']
                    else:
                        default_reps = current_set['planned_reps'] or 0
                    default_weight = current_set['planned_weight'] or 0.0
                    
                    with c1:
                        if overload:
                            st.markdown(f"**Target**: {overload['suggested_reps']} ⬆ (was {overload['last_reps']}) × {default_weight} lbs")
                        else:
                            st.markdown(f"**Target**: {default_reps} × {default_weight} lbs")
                        # Ghost text for "last time" in IN_SET state too
                        if last_time:
                            st.markdown(f"<div class='ghost-text'>last: {last_time['reps']} × {last_time['weight']}</div>", unsafe_allow_html=True)
                    
                    with c2:
                        actual_reps = st.number_input("Reps", value=default_reps, key=f"curr_reps_{current_set['id']}")
                    with c3:
                        actual_weight = st.number_input("Weight", value=default_weight, step=2.5, key=f"curr_weight_{current_set['id']}")
                    
                    st.write("")
                    if st.button("Finish Set", type="primary", use_container_width=True):
                        runner_service.complete_set(
                            active_session['id'], 
                            active_ex['order_index'], 
                            current_set['set_number'], 
                            actual_reps, 
                            actual_weight
                        )
                        st.rerun()

            st.divider()
            
            # --- History (Current Exercise) ---
            history = progression['active_exercise_history']
            if history:
                st.markdown("**Set History**")
                for h in history:
                    with st.expander(f"Set {h['set_number']} — {h['actual_reps']} × {h['actual_weight']}", expanded=False):
                        # Edit Controls
                        hc1, hc2, hc3 = st.columns([2, 2, 1])
                        with hc1:
                            new_reps = st.number_input("Reps", value=h['actual_reps'], key=f"h_reps_{h['id']}")
                        with hc2:
                            new_weight = st.number_input("Weight", value=h['actual_weight'], step=2.5, key=f"h_weight_{h['id']}")
                        with hc3:
                            st.write("")
                            st.write("")
                            if st.button("Update", key=f"h_save_{h['id']}"):
                                runner_service.update_completed_set(h['id'], new_reps, new_weight)
                                st.success("Saved")
                                st.rerun()

else:
    # --- PLANNED / TEMPLATE MODE ---
    # Fetch Plan
    plan = get_day_plan(today_str)

    if not plan:
        st.markdown("No workout scheduled for today.")
        st.caption("Go to **Workouts** → **Assign** to set one up.")

    elif plan['plan_type'] == 'REST':
        st.markdown("### Rest Day")
        st.caption("Enjoy your recovery.")

    elif plan['plan_type'] == 'WORKOUT':
        # Check status from plan (Planner View)
        if plan.get('status') == 'COMPLETED':
            st.markdown(f"### ✓ {plan['name']}")
            st.caption("Completed. See you tomorrow.")
            
            with st.expander("View Details", expanded=False):
                template_id = plan['template_id']
                template = get_template(template_id)
                if template:
                     for i, ex in enumerate(template['exercises']):
                        st.write(f"{i+1}. {ex['name']}")
            
        else:
            # PLANNED
            template_id = plan['template_id']
            template = get_template(template_id)
            
            if not template:
                st.error("Assigned template not found.")
            else:
                # --- Workout Card (Planned) ---
                st.markdown(f"### {template['name']}")
                
                # START WORKOUT (Creates Snapshot)
                if st.button("Start Workout", type="primary", use_container_width=True):
                    try:
                        runner_service.start_workout(today_str, template_id)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error starting session: {e}")
                
                st.divider()
                
                # Exercises List with Reordering (Only available BEFORE start)
                if not template['exercises']:
                    st.write("No exercises in this template.")
                
                for i, ex in enumerate(template['exercises']):
                    with st.container():
                        c_name, c_up, c_down = st.columns([4, 0.5, 0.5])
                        
                        with c_name:
                            st.markdown(f"**{i+1}. {ex['name']}**")
                            # Show targets (Editable for Template)
                            if ex['sets']:
                                for s in ex['sets']:
                                    st.caption(f"S{s['set_number']}: {s['reps']} × {s['weight']}")
                        
                        # Reorder Controls
                        with c_up:
                            if i > 0:
                                if st.button("↑", key=f"up_{i}_{ex['id']}"):
                                    current_order = [x['id'] for x in template['exercises']]
                                    current_order[i], current_order[i-1] = current_order[i-1], current_order[i]
                                    reorder_exercises(template['id'], current_order)
                                    st.rerun()
                        with c_down:
                            if i < len(template['exercises']) - 1:
                                if st.button("↓", key=f"down_{i}_{ex['id']}"):
                                    current_order = [x['id'] for x in template['exercises']]
                                    current_order[i], current_order[i+1] = current_order[i+1], current_order[i]
                                    reorder_exercises(template['id'], current_order)
                                    st.rerun()
                    
                    if i < len(template['exercises']) - 1:
                        st.divider()
