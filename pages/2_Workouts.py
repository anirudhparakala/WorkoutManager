import streamlit as st
from services.templates_service import (
    get_all_templates, create_template, get_template, update_template, delete_template,
    add_exercise, remove_exercise, reorder_exercises, add_set, update_set, delete_set,
    ValidationError
)
from services.planner_service import assign_workout, assign_rest, assign_off, get_week_schedule, PlannerError
from repos.exercises_repo import get_all_exercises, create_exercise
from core.timeutil import today_str_et
import datetime

st.set_page_config(page_title="Manage Workouts", page_icon="🏋️", layout="wide")

from core.security import require_login
require_login()

st.title("Manage Workouts")

tab_templates, tab_schedule = st.tabs(["Templates", "Assign"])

with tab_templates:
    # --- Sidebar: Template List ---
    st.sidebar.header("Templates")
    templates = get_all_templates()

    # Create New Template
    with st.sidebar.expander("Create New Template"):
        new_template_name = st.text_input("Template Name")
        if st.button("Create"):
            if new_template_name:
                try:
                    new_id = create_template(new_template_name)
                    st.session_state["selected_template_id"] = new_id
                    st.rerun()
                except ValidationError as e:
                    st.sidebar.error(str(e))
            else:
                st.sidebar.error("Name required")
    
    # --- Backup & Data ---
    with st.sidebar.expander("Backup & Data"):
        st.write("Export your data to JSON.")
        from repos.backup_repo import export_data
        import json
        
        if st.button("Prepare Backup"):
            data = export_data()
            json_str = json.dumps(data, indent=2, default=str)
            st.download_button(
                label="⬇️ Download JSON",
                data=json_str,
                file_name="workout_manager_backup.json",
                mime="application/json"
            )

    # Select Template

    # Select Template
    # Ensure selected_template_id is in options, otherwise default to first
    if "selected_template_id" not in st.session_state or st.session_state["selected_template_id"] not in [t['id'] for t in templates]:
        if templates:
            st.session_state["selected_template_id"] = templates[0]['id']
        else:
            st.session_state["selected_template_id"] = None

    selected_template_id = st.sidebar.radio(
        "Select Template",
        options=[t['id'] for t in templates],
        format_func=lambda x: next((t['name'] for t in templates if t['id'] == x), "Unknown"),
        key="selected_template_id"
    )

    if not selected_template_id:
        st.info("Create or select a template to get started.")
    else:
        # --- Main: Template Editor ---
        template = get_template(selected_template_id)

        if not template:
            st.error("Template not found.")
        else:
            # Header / Rename / Delete
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                # Use a unique key per template to avoid state bleeding
                new_name = st.text_input("Template Name", value=template['name'], key=f"template_name_{template['id']}")
                if new_name != template['name']:
                    try:
                        update_template(template['id'], new_name)
                        st.rerun()
                    except ValidationError as e:
                        st.error(str(e))
            with col3:
                if st.button("Delete Template", type="primary"):
                    delete_template(template['id'])
                    st.rerun()

            st.divider()

            # --- Exercises List ---
            st.subheader("Exercises")

            if not template['exercises']:
                st.info("No exercises in this template yet.")

            for i, ex in enumerate(template['exercises']):
                with st.expander(f"{i+1}. {ex['name']}", expanded=True):
                    # Controls Row
                    c1, c2, c3, c4 = st.columns([1, 1, 4, 1])
                    with c1:
                        if i > 0:
                            if st.button("⬆️", key=f"up_{ex['id']}"):
                                # Swap with previous
                                current_order = [x['id'] for x in template['exercises']]
                                current_order[i], current_order[i-1] = current_order[i-1], current_order[i]
                                reorder_exercises(template['id'], current_order)
                                st.rerun()
                    with c2:
                        if i < len(template['exercises']) - 1:
                            if st.button("⬇️", key=f"down_{ex['id']}"):
                                # Swap with next
                                current_order = [x['id'] for x in template['exercises']]
                                current_order[i], current_order[i+1] = current_order[i+1], current_order[i]
                                reorder_exercises(template['id'], current_order)
                                st.rerun()
                    with c4:
                        if st.button("Remove", key=f"remove_{ex['id']}", type="primary"):
                            remove_exercise(ex['id'])
                            st.rerun()
                    
                    # Sets Editor
                    st.markdown("**Sets**")
                    if not ex['sets']:
                        st.caption("No sets defined.")
                    
                    for s in ex['sets']:
                        sc1, sc2, sc3, sc4 = st.columns([1, 2, 2, 1])
                        with sc1:
                            st.write(f"Set {s['set_number']}")
                        with sc2:
                            reps = st.number_input("Reps", value=s['reps'] or 0, key=f"reps_{s['id']}")
                        with sc3:
                            weight = st.number_input("Weight", value=s['weight'] or 0.0, step=2.5, key=f"weight_{s['id']}")
                        with sc4:
                            if st.button("❌", key=f"del_set_{s['id']}"):
                                delete_set(s['id'])
                                st.rerun()
                        
                        # Auto-save on change (Streamlit reruns on input change)
                        if reps != (s['reps'] or 0) or weight != (s['weight'] or 0.0):
                            try:
                                update_set(s['id'], reps, weight)
                            except ValidationError as e:
                                st.error(str(e))
                            # We don't rerun here to avoid jarring UX, but it saves.
                            # Actually, we might need to rerun to refresh the state if we want strict consistency,
                            # but for inputs, it's usually fine.
                    
                    if st.button("Add Set", key=f"add_set_{ex['id']}"):
                        try:
                            add_set(ex['id'], 10, 0) # Default values
                            st.rerun()
                        except ValidationError as e:
                            st.error(str(e))

            st.divider()

            # --- Add Exercise Section ---
            st.subheader("Add Exercise")
            all_exercises = get_all_exercises()
            exercise_options = {e['id']: e['name'] for e in all_exercises}

            c1, c2 = st.columns([3, 1])
            with c1:
                selected_ex_id = st.selectbox("Select Exercise", options=list(exercise_options.keys()), format_func=lambda x: exercise_options[x])
            with c2:
                if st.button("Add to Template"):
                    add_exercise(template['id'], selected_ex_id)
                    st.rerun()

            with st.expander("Create New Exercise"):
                new_ex_name = st.text_input("Exercise Name")
                if st.button("Create Exercise"):
                    if new_ex_name:
                        try:
                            create_exercise(new_ex_name)
                            st.success(f"Created {new_ex_name}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

with tab_schedule:
    st.header("Assign Workouts")

    # --- Assignment Form ---
    # Moved to top for quick access
    st.subheader("Assign Plan")
    
    col1, col2, col3, col4 = st.columns([2, 3, 3, 1])
    
    # 1. Date Picker
    with col1:
        # Default to today
        today_date = datetime.datetime.strptime(today_str_et(), '%Y-%m-%d').date()
        assign_date = st.date_input("Date", value=today_date)
    
    # 2. Type Selection
    with col2:
        # OFF / REST / WORKOUT
        plan_type = st.radio("Type", ["OFF", "REST", "WORKOUT"], horizontal=True)
        
    # 3. Template Selection (if WORKOUT)
    with col3:
        template_id_to_assign = None
        if plan_type == "WORKOUT":
            templates_list = get_all_templates()
            if templates_list:
                template_id_to_assign = st.selectbox(
                    "Select Template", 
                    options=[t['id'] for t in templates_list],
                    format_func=lambda x: next((t['name'] for t in templates_list if t['id'] == x), "Unknown")
                )
            else:
                st.warning("No templates available.")
        else:
             st.write("") # Placeholder
                
    # 4. Action Button
    with col4:
        st.write("") # Spacer
        st.write("") # Spacer
        if st.button("Assign", type="primary"):
            try:
                date_str_assign = assign_date.strftime('%Y-%m-%d')
                if plan_type == "WORKOUT":
                    if template_id_to_assign:
                        assign_workout(date_str_assign, template_id_to_assign)
                        st.success(f"Assigned workout to {date_str_assign}")
                        st.rerun()
                    else:
                        st.error("Please select a template.")
                elif plan_type == "REST":
                    assign_rest(date_str_assign)
                    st.success(f"Assigned rest to {date_str_assign}")
                    st.rerun()
                elif plan_type == "OFF":
                    assign_off(date_str_assign)
                    st.success(f"Cleared plan for {date_str_assign}")
                    st.rerun()
                    
            except PlannerError as e:
                st.error(str(e))

    st.divider()

    # --- Week Overview ---
    st.subheader("Week Overview")
    
    # Calculate Monday of the current week (based on 'assign_date' or 'today'?)
    # "Week overview list (Mon–Sun)" usually implies the current week of the date being viewed/assigned,
    # or just the *current* week relative to today.
    # Let's pivot around the selected 'assign_date' so the user sees the week they are scheduling.
    
    pivot_date = assign_date
    # weekday(): Mon=0, Sun=6
    monday_of_week = pivot_date - datetime.timedelta(days=pivot_date.weekday())
    sunday_of_week = monday_of_week + datetime.timedelta(days=6)
    
    # Fetch schedule for this range
    # we need to ensure get_week_schedule supports arbitrary range or we use repo directly?
    # services.planner_service.get_week_schedule uses get_week_start(today) which is hardcoded to some logic.
    # Let's rely on repo get_range since we want a custom range (Mon-Sun)
    from repos.planner_repo import get_range
    
    week_plans = get_range(monday_of_week.strftime('%Y-%m-%d'), sunday_of_week.strftime('%Y-%m-%d'))
    schedule_map = {p['date']: p for p in week_plans}
    
    # Display List
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    for i in range(7):
        current_iter_date = monday_of_week + datetime.timedelta(days=i)
        d_str = current_iter_date.strftime('%Y-%m-%d')
        plan = schedule_map.get(d_str)
        
        # Highlight if it's the selected date
        bg_style = ""
        if current_iter_date == assign_date:
            bg_style = "background-color: #262730; border-radius: 5px; padding: 5px;"
            
        with st.container():
            c1, c2, c3 = st.columns([1, 2, 4])
            with c1:
                st.markdown(f"**{days[i]}**")
            with c2:
                st.caption(d_str)
            with c3:
                if plan:
                    if plan['plan_type'] == 'WORKOUT':
                        if plan.get('status') == 'COMPLETED':
                            st.success(f"✅ {plan['name']}")
                        elif plan.get('status') == 'ACTIVE':
                            st.warning(f"⚡ {plan['name']}")
                        else:
                            st.info(f"🏋️ {plan['name']}")
                    elif plan['plan_type'] == 'REST':
                        st.success("💤 Rest Day")
                else:
                    st.markdown("<span style='color: grey'>OFF</span>", unsafe_allow_html=True)
            
            if i < 6:
                st.write("---") # Thin separator

