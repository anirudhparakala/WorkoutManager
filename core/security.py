import hashlib
import secrets
import hmac

def hash_pin(pin: str) -> str:
    """Returns a salted hash of the PIN. Format: salt$hash"""
    salt = secrets.token_hex(16)
    # Use PBKDF2 for secure hashing
    key = hashlib.pbkdf2_hmac(
        'sha256',
        pin.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"{salt}${key.hex()}"

def verify_pin(pin: str, hashed_pin: str) -> bool:
    """Verifies the PIN against the salted hash safely."""
    try:
        salt, key_hex = hashed_pin.split('$')
        new_key = hashlib.pbkdf2_hmac(
            'sha256',
            pin.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        # Constant time comparison
        return hmac.compare_digest(key_hex, new_key.hex())
    except (ValueError, AttributeError):
        return False

import streamlit as st
import time

def login():
    """Renders the login screen."""
    st.title("Locked")
    
    with st.form("login_form"):
        entered_pin = st.text_input("Enter Access PIN", type="password")
        submitted = st.form_submit_button("Unlock")
        
        if submitted:
            try:
                stored_hash = st.secrets["APP_PIN_HASH"]
            except KeyError:
                st.error("Configuration Error: APP_PIN_HASH not found in secrets.")
                return

            if verify_pin(entered_pin, stored_hash):
                st.session_state["authenticated"] = True
                st.success("Unlocked!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Incorrect PIN")

def require_login():
    """Stops execution if not authenticated."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
        
    if not st.session_state["authenticated"]:
        login()
        st.stop()
