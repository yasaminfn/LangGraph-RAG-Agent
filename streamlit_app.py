import streamlit as st
import requests
import time
import uuid

#page title
st.title('Chat Streaming')
    
#input box for user query    
user_input = st.text_input("Enter your question:", placeholder="Type here...")

# --- API endpoint configuration ---
url = "http://localhost:8000/chat/stream"
data = {
        "query": user_input,
        "session_id": st.session_state.session_id
    }
    
placeholder = st.empty() #create an empty space

# --- Send the request and stream the response ---
r = requests.post(url, json = data, stream=True)
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