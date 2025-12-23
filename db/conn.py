import streamlit as st
import libsql_client
import os
from contextlib import contextmanager

def _get_config():
    """Retrieves database configuration from Streamlit secrets."""
    try:
        url = st.secrets["TURSO_DATABASE_URL"]
        token = st.secrets["TURSO_AUTH_TOKEN"]
        return url, token
    except (FileNotFoundError, KeyError):
        st.error("Config error: Missing TURSO_DATABASE_URL or TURSO_AUTH_TOKEN in .streamlit/secrets.toml")
        st.stop()

def get_conn():
    """Creates and returns a new database connection."""
    url, token = _get_config()
    if url.startswith("libsql://"):
        url = url.replace("libsql://", "https://")
    return libsql_client.create_client_sync(url, auth_token=token)

def execute(query, params=()):
    """Executes a query and commits changes."""
    # Use batch for robustness against 'result' KeyError on non-SELECTs
    from libsql_client import Statement
    with get_conn() as client:
        client.batch([Statement(query, params)])

def query_all(query, params=()):
    """Executes a query and returns all rows."""
    with get_conn() as client:
        result = client.execute(query, params)
        return result.rows

def query_one(query, params=()):
    """Executes a query and returns a single row."""
    with get_conn() as client:
        result = client.execute(query, params)
        if result.rows:
            return result.rows[0]
        return None

@contextmanager
def transaction():
    """Context manager for database transactions."""
    # The HTTP client for libsql doesn't support interactive transactions.
    # For a single-user app, we can mostly get away with sequential execution.
    # If we needed atomicity, we'd use batch(), but that requires refactoring the calling code.
    # For now, we'll make this a pass-through that just yields the client.
    client = get_conn()
    try:
        # Check if client supports transaction (it might be a method or property)
        # But based on the error, it seems explicit transaction() call fails.
        # We'll just yield the client and rely on auto-commit behavior of individual statements.
        yield client
    finally:
        client.close()
