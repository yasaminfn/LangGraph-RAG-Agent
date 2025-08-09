import streamlit as st
import requests
import time
import uuid

# --- If the user is not logged in, show warning and login button ---
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Please login first.")

    # Login button (redirect to auth page)
    if st.button("Log in", icon = ":material/login:" ):
        st.switch_page("auth_app.py") 
    
    # Stop rendering the rest of the page    
    st.stop()    
    
# --- Top bar: Title + Logout button ---
col1, col2 = st.columns([5, 1])
with col1:
    #page title
    st.title('AI Chat Assistant')
with col2:
    # Logout button
    if st.session_state.get("logged_in", False): 
        if st.button("Logout", icon = ":material/account_circle_off:" ):
            for key in ["access_token", "token_type", "logged_in", "session_id"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun() # Refresh page after logout

# --- Initialize session_id in Streamlit state ---
# This ensures all messages in the same session share the same ID
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4()) # Generate a unique session ID
    
#input box for user query    
user_input = st.text_input("Enter your question:", placeholder="Type here...")

# --- API endpoint configuration ---
url = "http://localhost:8000/chat/stream"
data = {
        "query": user_input,
        "session_id": st.session_state.session_id
    }
headers = {
    "Authorization": f"Bearer {st.session_state['access_token']}"
}   
placeholder = st.empty() #create an empty space

# --- Send the request and stream the response ---
r = requests.post(url, json = data,headers=headers, stream=True)
response_text  = ""
for chunk in r.iter_content(chunk_size=1024):
    if chunk:
        # Decode each chunk from bytes to string
        text = chunk.decode("utf-8")
        # Append the chunk to the response text
        response_text += text
        # Update the Streamlit placeholder in real-time
        placeholder.write(response_text)
        time.sleep(0.1) # Small delay for smoother streaming effect