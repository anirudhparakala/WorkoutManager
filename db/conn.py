import streamlit as st
import libsql_client
import os
from contextlib import contextmanager
from libsql_client import Statement

def _get_config():
    """Retrieves database configuration from Streamlit secrets."""
    try:
        url = st.secrets["TURSO_DATABASE_URL"]
        token = st.secrets["TURSO_AUTH_TOKEN"]
        return url, token
    except (FileNotFoundError, KeyError):
        st.error("Config error: Missing TURSO_DATABASE_URL or TURSO_AUTH_TOKEN in .streamlit/secrets.toml")
        st.stop()

import atexit

@st.cache_resource
def get_db_client():
    """Creates and turns a persistent database client."""
    url, token = _get_config()
    if url.startswith("libsql://"):
        url = url.replace("libsql://", "https://")
    
    client = libsql_client.create_client_sync(url, auth_token=token)
    
    # Register cleanup to prevent hanging on Ctrl+C
    def _close():
        try:
            client.close()
        except:
            pass
    atexit.register(_close)
    
    return client

def execute(query, params=()):
    """Executes a query and commits changes."""
    # Use global client directly, no 'with' block to keep it open
    client = get_db_client()
    client.batch([Statement(query, params)])

def query_all(query, params=()):
    """Executes a query and returns all rows."""
    client = get_db_client()
    result = client.execute(query, params)
    return result.rows

def query_one(query, params=()):
    """Executes a query and returns a single row."""
    client = get_db_client()
    result = client.execute(query, params)
    if result.rows:
        return result.rows[0]
    return None

@contextmanager
def get_conn():
    """Context manager that yields the cached client. Safe for 'with get_conn() as client:'"""
    client = get_db_client()
    yield client
    # Do NOT close, as it is cached.

@contextmanager
def transaction():
    """Context manager for database transactions."""
    # Pass-through to global client. 
    # Since we can't reliably transact in stateless HTTP single-request flow without batch,
    # we yield the client for sequential ops.
    client = get_db_client()
    yield client
    # Do NOT close() here
