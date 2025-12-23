import streamlit as st
import os

def get_config(key, default=None):
    """Retrieves configuration from Streamlit secrets or environment variables."""
    if key in st.secrets:
        return st.secrets[key]
    return os.environ.get(key, default)
