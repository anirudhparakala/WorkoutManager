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

# --- Helpers ---
def render_timer(label, start_time_iso, color="#333", key_prefix="timer"):
    """Injects a client-side JS timer using an iframe component."""
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
            border: 1px solid #ddd; 
            border-radius: 8px; 
            padding: 10px; 
            background-color: #f9f9f9; 
            width: 100%; 
            text-align: center;
            box-sizing: border-box;
        }}
        .timer-label {{
            color: #666; 
            text-transform: uppercase; 
            font-weight: bold; 
            font-size: 0.75rem;
            margin-bottom: 4px;
        }}
        .timer-val {{
            font-size: 24px; 
            font-family: monospace; 
            font-weight: bold; 
            color: {color};
        }}
    </style>
    </head>
    <body>
        <div class="timer-box">
            <div class="timer-label">{label}</div>
            <div id="timer_val" class="timer-val">--:--</div>
        </div>
        <script>
            console.log("Timer initialized: {label}");
            var start = {start_ts_ms}; 
            var el = document.getElementById("timer_val");
            
            function update() {{
                var now = new Date().getTime();
                var diff = now - start;
                if (diff < 0) diff = 0;
                
                var m = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
                var s = Math.floor((diff % (1000 * 60)) / 1000);
                
                m = (m < 10) ? "0" + m : m;
                s = (s < 10) ? "0" + s : s;
                
                el.innerText = m + ":" + s;
            }}
            
            setInterval(update, 1000);
            update();
        </script>
    </body>
    </html>
    """
    
    # Render component with fixed height to match content
    components.html(html_code, height=85)

# --- Header ---
today_str = today_str_et()
display_date = datetime.datetime.strptime(today_str, '%Y-%m-%d').strftime('%A, %b %d')

st.title(f"Today: {display_date}")

# --- Check for Active Session (Snapshot) ---
active_session = get_active_session(today_str)

if active_session:
    # --- ACTIVE RUNNER MODE ---
    st.info(f"⚡ Active Session: {active_session['name']}")
    
    if active_session['status'] == 'COMPLETED':
        st.success("🎉 Workout Completed! Great job.")
        st.balloons()
        # Could show summary here
    else:
        # Fetch Progression
        progression = runner_service.get_workout_progression(active_session['id'])
        
        if progression['is_completed']:
            st.success("All sets completed!")
            
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
            
            # --- Workout Timer ---
            if active_session['started_at']:
                 render_timer("Total Workout Time", active_session['started_at'], color="#4CAF50", key_prefix="workout_total")

            # --- Runner Card ---
            with st.container():
                st.markdown(f"### {active_ex['name']}")
                st.caption(f"Set {current_set['set_number']} - {state}")
                
                # --- State Machine UI ---
                if state == "READY" or state == "REST":
                    # Show Rest Timer if applicable
                    if progression.get('timer_base'):
                         render_timer("Rest Time", progression['timer_base'], color="#2196F3", key_prefix="rest_timer")
                    
                    st.info(f"Target: {current_set['planned_reps']} reps @ {current_set['planned_weight']} lbs")
                    
                    if st.button(f"⏱️ Start Set {current_set['set_number']}", type="primary", use_container_width=True):
                        # Start Timer
                        runner_service.start_set(
                            active_session['id'],
                            active_ex['order_index'],
                            current_set['set_number']
                        )
                        st.rerun()
                        
                elif state == "IN_SET":
                    # Show Set Timer
                    render_timer("Set Duration", progression['timer_base'], color="#FF5722", key_prefix="set_timer")
                
                    c1, c2, c3 = st.columns([2, 2, 2])
                    
                    # Defaults
                    default_reps = current_set['planned_reps'] or 0
                    default_weight = current_set['planned_weight'] or 0.0
                    
                    with c1:
                        st.markdown(f"**Target**: {default_reps} x {default_weight} lbs")
                    
                    with c2:
                        actual_reps = st.number_input("Reps", value=default_reps, key=f"curr_reps_{current_set['id']}")
                    with c3:
                        actual_weight = st.number_input("Weight", value=default_weight, step=2.5, key=f"curr_weight_{current_set['id']}")
                    
                    st.write("")
                    if st.button("✅ Finish Set", type="primary", use_container_width=True):
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
                st.subheader("Set History")
                for h in history:
                    with st.expander(f"Set {h['set_number']} - {h['actual_reps']} x {h['actual_weight']}", expanded=False):
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
                                runner_service.update_completed_set(h['id'], new_reps, new_weight)
                                st.success("Saved")
                                st.rerun()

else:
    # --- PLANNED / TEMPLATE MODE ---
    # Fetch Plan
    plan = get_day_plan(today_str)

    if not plan:
        st.info("No workout scheduled for today. Go to 'Workouts' to assign one.")

    elif plan['plan_type'] == 'REST':
        st.success("💤 Rest Day. Enjoy your recovery!")

    elif plan['plan_type'] == 'WORKOUT':
        # Check status from plan (Planner View)
        if plan.get('status') == 'COMPLETED':
            st.success(f"✅ Workout Completed: {plan['name']}")
            st.caption("Great job! See you tomorrow.")
            
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
                with st.expander(f"🏋️ {template['name']} (Preview)", expanded=True):
                    
                    # START WORKOUT (Creates Snapshot)
                    if st.button("Start Workout", type="primary"):
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
                                    st.caption(f"S{s['set_number']}: {s['reps']} x {s['weight']}")
                        
                        # Reorder Controls
                        with c_up:
                            if i > 0:
                                if st.button("⬇️", key=f"up_{i}_{ex['id']}"):
                                    current_order = [x['id'] for x in template['exercises']]
                                    current_order[i], current_order[i-1] = current_order[i-1], current_order[i]
                                    reorder_exercises(template['id'], current_order)
                                    st.rerun()
                        with c_down:
                            if i < len(template['exercises']) - 1:
                                if st.button("⬇️", key=f"down_{i}_{ex['id']}"):
                                    current_order = [x['id'] for x in template['exercises']]
                                    current_order[i], current_order[i+1] = current_order[i+1], current_order[i]
                                    reorder_exercises(template['id'], current_order)
                                    st.rerun()
                    
                    if i < len(template['exercises']) - 1:
                        st.divider()
