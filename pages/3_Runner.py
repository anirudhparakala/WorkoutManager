import streamlit as st
from services.templates_service import get_template

st.set_page_config(page_title="Workout Runner", page_icon="🏃")

from core.security import require_login
require_login()

if 'runner_state' in st.session_state and st.session_state['runner_state']:
    state = st.session_state['runner_state']
    template_id = state.get('template_id')
    start_index = state.get('start_exercise_index', 0)
    current_set_idx = state.get('current_set_index', 0)
    
    # Fetch template details
    template = get_template(template_id)
    
    if not template:
        st.error("Template not found.")
        if st.button("Back to Today"):
            st.switch_page("pages/1_Today.py")
    else:
        st.title(f"Run: {template['name']}")
        
        # Get current exercise
        exercises = template['exercises']
        if start_index < len(exercises):
            current_exercise = exercises[start_index]
            sets = current_exercise['sets']
            
            st.subheader(f"Current: {current_exercise['name']}")
            
            # --- Check if we have sets left ---
            if not sets:
                st.info("No sets defined for this exercise.")
                if st.button("Mark Completed", type="primary"):
                    if 'completed_exercises' not in st.session_state:
                         st.session_state['completed_exercises'] = set()
                    st.session_state['completed_exercises'].add(start_index)
                    st.switch_page("pages/1_Today.py")
            
            elif current_set_idx < len(sets):
                # Display Current Set
                current_set = sets[current_set_idx]
                
                # Display Progress
                st.progress((current_set_idx) / len(sets))
                st.write(f"**Set {current_set_idx + 1} of {len(sets)}**")
                
                st.markdown(f"### Target: {current_set['reps']} reps @ {current_set['weight']} lbs")
                
                st.caption("Perform the set above.")
                
                st.divider()
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    # Mark Done -> Go to next set OR Finish
                    if st.button("✅ Done", type="primary", use_container_width=True):
                        # Increment Set
                        state['current_set_index'] = current_set_idx + 1
                        st.session_state['runner_state'] = state # Ensure update
                        st.rerun()
                        
                with col2:
                    if st.button("Back", use_container_width=True):
                        st.switch_page("pages/1_Today.py")
            
            else:
                # All sets done for this exercise
                # Auto-complete logic or quick confirmation
                # Since user clicked Done on last set, we can just finish.
                # But 'current_set_idx' increments *after* the click, so we land here on rerun.
                
                # Add to completed list
                if 'completed_exercises' not in st.session_state:
                    st.session_state['completed_exercises'] = set()
                
                st.session_state['completed_exercises'].add(start_index)
                
                # Automatically return or show success
                st.success("Exercise Completed! Returning to menu...")
                # Using a spinner or simple redirect
                st.switch_page("pages/1_Today.py")

        else:
            st.success("All exercises in this sequence completed!")
            if st.button("Finish Workout"):
                st.switch_page("pages/1_Today.py")

else:
    st.warning("No active session. Go to 'Today' to start a workout.")
