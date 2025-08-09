import streamlit as st
import requests

# Base URL of your FastAPI backend
API_BASE = "http://localhost:8000"

# ---------- API calls ----------
# ---------- Function to send signup request ----------
def signup_request(username: str, email: str, full_name: str, password: str):
    """
    Sends a POST request to the /signup endpoint with JSON payload.
    The payload structure must match the UserCreate model in the backend.
    """
    payload = {
        "username": username,
        "email": email,
        "password": password,
        "full_name": full_name
    }
    # requests.post with 'json=payload' automatically sets Content-Type to application/json
    return requests.post(
        f"{API_BASE}/signup",
        json=payload,
        timeout=10  # seconds to wait before giving up (prevents hanging forever)
    )

# ---------- Function to send login request ----------
def login_request(username: str, password: str):
    """
    Sends POST request to /token to authenticate user.
    Uses form-encoded data because backend expects OAuth2PasswordRequestForm.
    """
    payload = {
        "username": username,
        "password": password,
    }
    
    # requests.post with 'json=payload' automatically sets Content-Type to application/json
    return requests.post(
        f"{API_BASE}/token",
        data=payload,  # NOTE: OAuth2PasswordRequestForm requires form data, not JSON
        timeout=10  # seconds to wait before giving up (prevents hanging forever)
    )
