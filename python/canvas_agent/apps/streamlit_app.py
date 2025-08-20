"""Streamlit application for CanvasAgent (packaged version).

Differences from legacy app_enhanced.py:
 - Uses package-relative imports
 - Centralized configuration via canvas_agent.config.load_settings
 - Graceful handling when dependencies (Ollama / token) missing
 - Structured into smaller helper functions for easier testing
"""
from __future__ import annotations
import time
import streamlit as st
from typing import Optional, List, Dict, Tuple

from canvas_agent.config import load_settings
from canvas_agent.canvas_client_enhanced import CanvasClientEnhanced
from canvas_agent.llm_enhanced import (
    list_ollama_models,
    check_ollama_service,
)
from canvas_agent.action_dispatcher import CanvasActionDispatcher


# ------------------------- Session State Helpers ------------------------- #
def init_session_state() -> None:
    if "history" not in st.session_state:
        # (role, content) tuples
        st.session_state.history = []
    if "courses_cache" not in st.session_state:
        st.session_state.courses_cache = []
    if "last_course_fetch" not in st.session_state:
        st.session_state.last_course_fetch = 0.0
    if "selected_course" not in st.session_state:
        st.session_state.selected_course = None


def configure_page() -> None:
    st.set_page_config(
        page_title="CanvasAgent",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded",
    )


# ------------------------- Sidebar Components --------------------------- #
def sidebar_llm_section() -> Optional[str]:
    st.sidebar.subheader("🤖 LLM Configuration")
    status = check_ollama_service()
    if not status["running"]:
        st.sidebar.error(f"❌ {status['message']}")
        return None
    st.sidebar.success(f"✅ {status['message']}")
    models = list_ollama_models()
    if not models:
        st.sidebar.warning("No models found. Pull a model first: `ollama pull llama3`")
        return None
    return st.sidebar.selectbox("Ollama Model", options=models)


def sidebar_canvas_section(canvas_client: Optional[CanvasClientEnhanced]) -> None:
    st.sidebar.subheader("🎯 Canvas LMS")
    if canvas_client:
        if st.sidebar.button("🔍 Test Canvas Connection"):
            test_canvas_connection(canvas_client)
    else:
        st.sidebar.warning("Provide CANVAS_TOKEN to enable Canvas features.")


def test_canvas_connection(client: CanvasClientEnhanced) -> bool:
    try:
        with st.spinner("Testing Canvas connection..."):
            courses = client.list_courses()
            st.session_state.courses_cache = courses
            st.session_state.last_course_fetch = time.time()
            st.sidebar.success(f"✅ Connected! Found {len(courses)} courses")
            if courses:
                course_options = ["All Courses"] + [f"{c.get('name')} (ID: {c.get('id')})" for c in courses]
                sel = st.sidebar.selectbox(
                    "Quick Course Select", list(range(len(course_options))), format_func=lambda i: course_options[i]
                )
                st.session_state.selected_course = courses[sel - 1] if sel > 0 else None
        return True
    except Exception as e:  # pragma: no cover - UI feedback
        st.sidebar.error(f"❌ Connection failed: {e}")
        return False


def render_course_context() -> None:
    if not st.session_state.selected_course:
        return
    st.sidebar.subheader("📚 Current Course")
    c = st.session_state.selected_course
    st.sidebar.info(f"**{c.get('name')}**\nID: {c.get('id')}")
    if st.sidebar.button("Clear Course Context"):
        st.session_state.selected_course = None
        st.rerun()


def quick_actions(client: CanvasClientEnhanced) -> None:
    st.sidebar.subheader("⚡ Quick Actions")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("📋 List Courses"):
            try:
                courses = client.list_courses()
                msg = "**Your Courses:**\n" + "\n".join(
                    f"• **{c.get('name')}** (ID: {c.get('id')})" for c in courses
                )
                st.session_state.history.append(("assistant", msg))
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Failed: {e}")
    with col2:
        if st.button("👤 My Profile"):
            try:
                profile = client.get_user_profile()
                msg = f"**Your Profile:**\n**Name:** {profile.get('name')}\n**Email:** {profile.get('primary_email')}"
                st.session_state.history.append(("assistant", msg))
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Failed: {e}")
    if st.session_state.selected_course:
        cid = st.session_state.selected_course.get("id")
        if st.button("📝 List Assignments"):
            try:
                assignments = client.list_assignments(cid)
                msg = f"**Assignments:**\n" + "\n".join(
                    f"• **{a.get('name')}** ({a.get('points_possible',0)} pts)" for a in assignments
                )
                st.session_state.history.append(("assistant", msg))
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Failed: {e}")
        if st.button("📚 List Modules"):
            try:
                modules = client.list_modules(cid)
                msg = f"**Modules:**\n" + "\n".join(
                    f"• **{m.get('name')}** ({m.get('items_count',0)} items)" for m in modules
                )
                st.session_state.history.append(("assistant", msg))
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Failed: {e}")


def debug_panel(client: Optional[CanvasClientEnhanced]) -> None:
    with st.sidebar.expander("🔧 Debug"):
        if client:
            st.json(client.get_cache_stats())
            if st.button("Clear Cache"):
                client.clear_cache()
                st.success("Cache cleared")
        st.write(f"Courses cached: {len(st.session_state.courses_cache)}")
        st.write(
            f"Selected course: {st.session_state.selected_course.get('name') if st.session_state.selected_course else 'None'}"
        )
        st.write(f"Messages: {len(st.session_state.history)}")


# --------------------------- Chat Interface ------------------------------ #
def render_history() -> None:
    for role, content in st.session_state.history:
        with st.chat_message(role):
            st.markdown(content)


def handle_user_input(dispatcher: CanvasActionDispatcher, text: str) -> None:
    st.session_state.history.append(("user", text))
    with st.chat_message("user"):
        st.markdown(text)
    with st.chat_message("assistant"):
        with st.spinner("Processing..."):
            req = text
            if st.session_state.selected_course:
                c = st.session_state.selected_course
                req += f" [Course Context: {c.get('name')} (ID: {c.get('id')})]"
            response = dispatcher.execute_natural_language_request(
                req, st.session_state.courses_cache
            )
            st.markdown(response)
            st.session_state.history.append(("assistant", response))


def chat_ui(dispatcher: Optional[CanvasActionDispatcher], need_token: bool, have_model: bool) -> None:
    st.title("🎓 CanvasAgent")
    if need_token:
        st.info(
            "👈 Enter your Canvas token (CANVAS_TOKEN env var or secrets) to enable LMS interactions."
        )
    render_history()
    if dispatcher:
        user_text = st.chat_input("Ask CanvasAgent...")
        if user_text:
            handle_user_input(dispatcher, user_text)
    else:
        st.caption("Canvas features disabled.")
    if dispatcher and not have_model:
        st.warning("LLM not available; falling back to rule-based intent parsing.")


# ------------------------------ Main ------------------------------------ #
def main() -> None:  # pragma: no cover - UI wiring
    configure_page()
    init_session_state()
    settings = load_settings(getattr(st, "secrets", None))

    st.sidebar.title("🎓 CanvasAgent Settings")

    # Canvas client initialization
    canvas_client: Optional[CanvasClientEnhanced] = None
    if settings.canvas.token:
        canvas_client = CanvasClientEnhanced(settings.canvas.base_url, settings.canvas.token)
    else:
        st.sidebar.warning("Missing CANVAS_TOKEN (or CANVAS_API_TOKEN).")

    # LLM section
    selected_model = sidebar_llm_section() if settings.ollama.enabled else None

    # Canvas section
    sidebar_canvas_section(canvas_client)

    # Auto refresh courses every 5 minutes
    if canvas_client and time.time() - st.session_state.last_course_fetch > 300:
        try:
            st.session_state.courses_cache = canvas_client.list_courses()
            st.session_state.last_course_fetch = time.time()
        except Exception:
            pass

    render_course_context()
    if canvas_client:
        quick_actions(canvas_client)
    debug_panel(canvas_client)

    dispatcher: Optional[CanvasActionDispatcher] = None
    if canvas_client:
        dispatcher = CanvasActionDispatcher(canvas_client, selected_model)

    chat_ui(dispatcher, need_token=not bool(settings.canvas.token), have_model=bool(selected_model))

    st.sidebar.markdown("---")
    st.sidebar.caption("CanvasAgent Streamlit App")


if __name__ == "__main__":  # pragma: no cover
    main()
