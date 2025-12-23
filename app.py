import streamlit as st

st.set_page_config(
    page_title="Workout Manager",
    page_icon="💪",
    layout="wide"
)

from core.security import require_login
require_login()

st.title("Workout Manager")

# Run migrations
from db.migrations import migrate
migrate()

st.write("Welcome to your Strength Training Tracker.")
st.sidebar.success("Select a page above.")
