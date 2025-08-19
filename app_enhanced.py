"""Enhanced Streamlit app with improved Canvas LMS integration and LLM-powered natural language processing."""
import os
import streamlit as st
from dotenv import load_dotenv
import json
import time
from datetime import datetime

# Import enhanced modules
from canvas_client_enhanced import CanvasClientEnhanced
from llm_enhanced import list_ollama_models, check_ollama_service, ollama_chat_api
from action_dispatcher import CanvasActionDispatcher

# Load environment variables
load_dotenv()

def get_env_value(key: str, default: str = "") -> str:
    """Get value from Streamlit secrets, environment, or default."""
    try:
        if hasattr(st, 'secrets') and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)

def init_session_state():
    """Initialize session state variables."""
    if 'history' not in st.session_state:
        st.session_state.history = []
    if 'courses_cache' not in st.session_state:
        st.session_state.courses_cache = []
    if 'last_course_fetch' not in st.session_state:
        st.session_state.last_course_fetch = 0
    if 'selected_course' not in st.session_state:
        st.session_state.selected_course = None

def configure_page():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title="CanvasAgent Enhanced",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded"
    )

def setup_sidebar():
    """Setup and render sidebar with configuration options."""
    st.sidebar.title("🎓 CanvasAgent Settings")
    
    # Ollama Configuration
    st.sidebar.subheader("🤖 LLM Configuration")
    
    # Check Ollama service status
    service_status = check_ollama_service()
    if service_status["running"]:
        st.sidebar.success(f"✅ {service_status['message']}")
        models = list_ollama_models()
        if models:
            selected_model = st.sidebar.selectbox("Ollama Model", options=models)
        else:
            st.sidebar.warning("No models found. Pull a model first: `ollama pull llama3`")
            selected_model = None
    else:
        st.sidebar.error(f"❌ {service_status['message']}")
        st.sidebar.info("Start Ollama service and refresh the page")
        selected_model = None
    
    # Canvas Configuration
    st.sidebar.subheader("🎯 Canvas LMS Configuration")
    
    canvas_base_url = st.sidebar.text_input(
        "Canvas Base URL",
        value=get_env_value('CANVAS_BASE_URL', 'https://canvas.instructure.com'),
        help="Your Canvas instance URL"
    )
    
    canvas_token = st.sidebar.text_input(
        "Canvas API Token",
        value=get_env_value('CANVAS_API_TOKEN', ''),
        type='password',
        help="Generate from Canvas Account > Settings > New Access Token"
    )
    
    # Token source indicator
    try:
        token_source = 'secrets' if 'CANVAS_API_TOKEN' in st.secrets else 'input/env'
    except:
        token_source = 'input/env'
    
    if canvas_token:
        st.sidebar.caption(f"📍 Token source: {token_source}")
    else:
        st.sidebar.warning("⚠️ Canvas API token required for Canvas operations")
    
    return selected_model, canvas_base_url, canvas_token

def test_canvas_connection(client: CanvasClientEnhanced):
    """Test Canvas connection and cache courses."""
    try:
        with st.sidebar:
            with st.spinner("Testing Canvas connection..."):
                courses = client.list_courses()
                st.session_state.courses_cache = courses
                st.session_state.last_course_fetch = time.time()
                st.success(f"✅ Connected! Found {len(courses)} courses")
                
                # Course selector
                if courses:
                    course_options = ["All Courses"] + [f"{c.get('name')} (ID: {c.get('id')})" for c in courses]
                    selected_idx = st.selectbox("Quick Course Select", range(len(course_options)), 
                                              format_func=lambda x: course_options[x])
                    if selected_idx > 0:
                        st.session_state.selected_course = courses[selected_idx - 1]
                    else:
                        st.session_state.selected_course = None
                        
        return True
    except Exception as e:
        st.sidebar.error(f"❌ Connection failed: {e}")
        return False

def render_course_context():
    """Render current course context in sidebar."""
    if st.session_state.selected_course:
        st.sidebar.subheader("📚 Current Course Context")
        course = st.session_state.selected_course
        st.sidebar.info(f"**{course.get('name')}**\\nID: {course.get('id')}")
        
        if st.sidebar.button("Clear Course Context"):
            st.session_state.selected_course = None
            st.rerun()

def render_chat_interface(dispatcher: CanvasActionDispatcher):
    """Render the main chat interface."""
    st.title("🎓 CanvasAgent Enhanced")
    st.markdown("Ask me anything about your Canvas courses using natural language!")
    
    # Display conversation history
    for role, content in st.session_state.history:
        with st.chat_message(role):
            st.markdown(content)
    
    # Chat input
    user_input = st.chat_input("Ask me to do something with Canvas... (e.g., 'Create a module called Week 1 in my Math course')")
    
    if user_input:
        # Add user message to history
        st.session_state.history.append(("user", user_input))
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Process request and generate response
        with st.chat_message("assistant"):
            with st.spinner("Processing your request..."):
                # Add course context if available
                enhanced_request = user_input
                if st.session_state.selected_course:
                    course_info = f" [Current course context: {st.session_state.selected_course.get('name')} (ID: {st.session_state.selected_course.get('id')})]"
                    enhanced_request += course_info
                
                # Execute the request
                response = dispatcher.execute_natural_language_request(
                    enhanced_request, 
                    st.session_state.courses_cache
                )
                
                st.markdown(response)
                
                # Add response to history
                st.session_state.history.append(("assistant", response))

def render_quick_actions(client: CanvasClientEnhanced):
    """Render quick action buttons."""
    st.sidebar.subheader("⚡ Quick Actions")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("📋 List Courses", key="quick_courses"):
            try:
                courses = client.list_courses()
                response = "**Your Courses:**\\n" + "\\n".join([
                    f"• **{c.get('name')}** (ID: {c.get('id')})" for c in courses
                ])
                st.session_state.history.append(("assistant", response))
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Failed to fetch courses: {e}")
    
    with col2:
        if st.button("👤 My Profile", key="quick_profile"):
            try:
                profile = client.get_user_profile()
                response = f"**Your Profile:**\\n**Name:** {profile.get('name')}\\n**Email:** {profile.get('primary_email')}"
                st.session_state.history.append(("assistant", response))
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Failed to fetch profile: {e}")
    
    if st.session_state.selected_course:
        course_id = st.session_state.selected_course.get('id')
        
        if st.button("📝 List Assignments", key="quick_assignments"):
            try:
                assignments = client.list_assignments(course_id)
                response = f"**Assignments in {st.session_state.selected_course.get('name')}:**\\n" + "\\n".join([
                    f"• **{a.get('name')}** ({a.get('points_possible', 0)} pts)" for a in assignments
                ])
                st.session_state.history.append(("assistant", response))
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Failed to fetch assignments: {e}")
        
        if st.button("📚 List Modules", key="quick_modules"):
            try:
                modules = client.list_modules(course_id)
                response = f"**Modules in {st.session_state.selected_course.get('name')}:**\\n" + "\\n".join([
                    f"• **{m.get('name')}** ({m.get('items_count', 0)} items)" for m in modules
                ])
                st.session_state.history.append(("assistant", response))
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Failed to fetch modules: {e}")

def render_debug_info(client: CanvasClientEnhanced):
    """Render debug information."""
    with st.sidebar.expander("🔧 Debug Info"):
        st.write("**Cache Stats:**")
        cache_stats = client.get_cache_stats()
        st.json(cache_stats)
        
        if st.button("Clear Cache"):
            client.clear_cache()
            st.success("Cache cleared!")
        
        st.write("**Session State:**")
        st.write(f"Courses cached: {len(st.session_state.courses_cache)}")
        st.write(f"Selected course: {st.session_state.selected_course.get('name') if st.session_state.selected_course else 'None'}")
        st.write(f"Chat history: {len(st.session_state.history)} messages")

def main():
    """Main application function."""
    configure_page()
    init_session_state()
    
    # Setup sidebar
    selected_model, canvas_base_url, canvas_token = setup_sidebar()
    
    # Initialize Canvas client
    client = None
    dispatcher = None
    
    if canvas_token and canvas_base_url:
        client = CanvasClientEnhanced(canvas_base_url, canvas_token)
        dispatcher = CanvasActionDispatcher(client, selected_model)
        
        # Test connection button
        if st.sidebar.button("🔍 Test Canvas Connection"):
            test_canvas_connection(client)
        
        # Auto-fetch courses if cache is old (5 minutes)
        if time.time() - st.session_state.last_course_fetch > 300:
            try:
                st.session_state.courses_cache = client.list_courses()
                st.session_state.last_course_fetch = time.time()
            except Exception:
                pass  # Fail silently, user can manually test connection
        
        # Render additional sidebar components
        render_course_context()
        render_quick_actions(client)
        render_debug_info(client)
    
    # Main chat interface
    if not canvas_token:
        st.title("🎓 CanvasAgent Enhanced")
        st.info("👈 Please enter your Canvas API token in the sidebar to get started.")
        st.markdown("""
        ### Getting Started:
        1. Get your Canvas API token from: Account → Settings → New Access Token
        2. Enter it in the sidebar
        3. Test the connection
        4. Start chatting with your Canvas data!
        
        ### Example requests:
        - "Show me my courses"
        - "Create a module called Week 1 in my Math course"
        - "List all assignments in course 12345"
        - "Upload a file to my English course"
        """)
    elif not selected_model:
        st.title("🎓 CanvasAgent Enhanced")
        st.warning("🤖 Ollama service not available. You can still perform Canvas actions, but AI assistance is limited.")
        if dispatcher:
            render_chat_interface(dispatcher)
    else:
        render_chat_interface(dispatcher)
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("*CanvasAgent Enhanced v2.0*")

if __name__ == "__main__":
    main()
