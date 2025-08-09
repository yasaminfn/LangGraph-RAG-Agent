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

# ---------- Tabs ----------
tab_login, tab_signup = st.tabs(["Login", "Signup"])

# ---------- Streamlit UI ----------

# ---------- Login Tab ----------
with tab_login:
    st.subheader("Login to your account")
    #st.markdown("Enter your credentials to access your account.")

    # Input fields
    username = st.text_input("Username", placeholder="username",key="login_username")
    password = st.text_input("Password", placeholder="****", type="password",key="login_password")

    # Submit button
    if st.button("Login", key="login_button"):
        # Basic client-side validation before sending request
        if not username or not password:
            st.warning("Please fill in all required fields.")
        else:
            with st.spinner("Loging in..."):
                try:
                    # Send request to backend
                    res = login_request(username, password)
                except requests.RequestException as e:
                    # Network error or timeout
                    st.error(f"Network error: {e}")
                else:
                    if res.status_code == 200:
                            data = res.json()
                            # Save JWT in session state so other pages can use it
                            st.session_state["access_token"] = data.get("access_token")
                            st.session_state["token_type"] = data.get("token_type", "bearer")
                            st.session_state["logged_in"] = True
                            st.success("Logged in successfully!")
                            st.switch_page("pages/chatbot_app.py") 
                    else:
                        st.error(f"Login failed ({res.status_code}): {res.text}")
                        
# ---------- Signup Tab ----------
with tab_signup:
    st.subheader("Create a new account")
    
    # Input fields
    username = st.text_input("Username", placeholder="username", key="signup_username")
    email = st.text_input("Email", placeholder="email", key="signup_email")
    password = st.text_input("Password", placeholder="*******", type="password", key="signup_password")
    full_name = st.text_input("Full name", placeholder="full name", key="signup_fullname")

    # Submit button
    if st.button("Create account", key="signup_button"):
        # Basic client-side validation before sending request
        if not username or not email or not password or not full_name:
            st.warning("Please fill in all required fields: username, email, password, and full name.")
        else:
            with st.spinner("Creating account..."):
                try:
                    # Send request to backend
                    res = signup_request(username, email, full_name, password)
                except requests.RequestException as e:
                    # Network error or timeout
                    st.error(f"Network error: {e}")
                else:
                    # Check server response status code
                    if res.status_code in (200, 201):
                        st.success("Account created successfully! You can log in now.")
                    else:
                        # Show full server response for debugging
                        st.error(f"Signup failed ({res.status_code}): {res.text}")