
import os
import sys
import importlib
import uuid

import streamlit as st

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from components.sidebar import render_sidebar  # noqa: E402
from frontend_pages import home, crop, soil_report, chatbot, dashboard  # noqa: E402

yield_page = importlib.import_module("frontend_pages.yield")


def ensure_session_id():
    """
    Ensure a single session_id exists for this browser session and is
    shared by every page that needs it (Soil Health Analyzer + Chatbot).
    This is what lets the chatbot answer using THIS farmer's soil values
    without ever mixing them up with another farmer's session.
    """
    if "session_id" not in st.session_state:
        st.session_state.session_id = uuid.uuid4().hex


def load_css():
    """Load and inject the custom stylesheet from frontend/assets/style.css."""
    css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "style.css")
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("Custom stylesheet not found - using default Streamlit theme.")


def main():
    """Configure the page, apply styling, and route to the selected page."""
    st.set_page_config(
        page_title="AgriSense-AI",
        page_icon="🌿",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    load_css()
    ensure_session_id()

    selected_page = render_sidebar()

    page_renderers = {
        "home": home.render,
        "dashboard": dashboard.render,
        "crop": crop.render,
        "yield": yield_page.render,
        "soil_report": soil_report.render,
        "chatbot": chatbot.render,
    }

    renderer = page_renderers.get(selected_page, home.render)
    renderer()


if __name__ == "__main__":
    main()
