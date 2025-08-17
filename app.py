import os
import streamlit as st
from dotenv import load_dotenv
from canvas_client import CanvasClient
from llm import list_ollama_models, ollama_chat
from actions import dispatch_action

load_dotenv()

st.set_page_config(page_title="CanvasAgent", page_icon="🎓", layout="wide")

# Sidebar configuration
st.sidebar.title("Settings")
models = list_ollama_models()
selected_model = st.sidebar.selectbox("Ollama Model", options=models if models else ["(none detected)"])
canvas_base_url = st.sidebar.text_input("Canvas Base URL", value=os.getenv('CANVAS_BASE_URL', 'https://canvas.instructure.com'))
canvas_token = st.sidebar.text_input("Canvas API Token", value=os.getenv('CANVAS_API_TOKEN', ''), type='password')

if not canvas_token:
    st.sidebar.info("Enter your Canvas API token to enable actions.")

# Initialize client if possible
client = None
if canvas_token and canvas_base_url:
    client = CanvasClient(canvas_base_url, canvas_token)

st.title("CanvasAgent Chat")

if 'history' not in st.session_state:
    st.session_state.history = []

for role, content in st.session_state.history:
    with st.chat_message(role):
        st.markdown(content)

user_input = st.chat_input("Ask something or issue an action (e.g., 'list courses')")

if user_input:
    st.session_state.history.append(("user", user_input))
    # Try to dispatch action
    action_response = None
    if client:
        action_response = dispatch_action(client, user_input)
    if action_response:
        reply = action_response
    else:
        system_prompt = "You are a helpful assistant for interacting with Canvas LMS. If the user issues an action you cannot perform, politely suggest an actionable command starting with one of: list courses, list assignments <course_id>, list files <course_id>, download file <file_id>, upload file <course_id> <path>."
        reply = ollama_chat(selected_model, user_input, system=system_prompt)
    st.session_state.history.append(("assistant", reply))
    with st.chat_message("assistant"):
        st.markdown(reply)
