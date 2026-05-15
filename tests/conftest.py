import pytest
import os
import shutil
import db.conn
from db.migrations import migrate

TEST_DB_PATH = "file:test.db"

@pytest.fixture(scope="session", autouse=True)
def mock_db_config():
    """Mock the DB connection to use a local test SQLite DB."""
    # Monkeypatch the config fetcher to use our local test DB
    def _mock_get_config():
        return TEST_DB_PATH, "" # URL, Token
    
    db.conn._get_config = _mock_get_config

@pytest.fixture(autouse=True)
def clean_db():
    """Runs before every test. Ensures a clean database schema."""
    # If using local file, delete it
    if os.path.exists("test.db"):
        os.remove("test.db")
        
    # Re-initialize the client to ensure it connects to the new empty file
    client = db.conn.get_db_client()
    # Actually, get_db_client uses @st.cache_resource, so we need to clear it
    import streamlit as st
    st.cache_resource.clear()
    
    # Run migrations to build the fresh schema
    migrate()
    yield
    
    # Clean up after test
    if os.path.exists("test.db"):
        try:
            os.remove("test.db")
        except:
            pass
