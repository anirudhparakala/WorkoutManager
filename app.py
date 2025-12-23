import streamlit as st
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
            if st.button("Finish Workout & Save", type="primary"):
                runner_service.complete_session(active_session['id'])
                st.rerun()
        else:
            current_set = progression['current_set']
            active_ex = progression['active_exercise']
            
            # --- Runner Card ---
            with st.container():
                st.markdown(f"### {active_ex['name']}")
                st.caption(f"Set {current_set['set_number']}")
                
                c1, c2, c3 = st.columns([2, 2, 2])
                
                # Defaults from Planned
                default_reps = current_set['planned_reps'] or 0
                default_weight = current_set['planned_weight'] or 0.0
                
                with c1:
                    st.markdown(f"**Target**: {default_reps} x {default_weight} lbs")
                
                with c2:
                    actual_reps = st.number_input("Reps", value=default_reps, key="curr_reps")
                with c3:
                    actual_weight = st.number_input("Weight", value=default_weight, step=2.5, key="curr_weight")
                
                st.write("")
                if st.button("✅ Complete Set", type="primary", use_container_width=True):
                    # Call Service
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
