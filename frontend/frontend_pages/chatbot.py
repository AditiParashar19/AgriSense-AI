"""
chatbot.py
----------
Streamlit page for the AI Agriculture Chatbot (RAG-powered).

Uses the single shared st.session_state.session_id (set once in app.py)
so this chatbot can automatically see this same farmer's Soil Health
Analyzer values for context-aware answers - without ever mixing them
up with another farmer's session.
"""

import os
import sys

import requests
import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.chatbot_api import ask_chatbot  # noqa: E402


def _init_session():
    """Initialize chat message history on first load (session_id comes from app.py)."""
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []  # list of (role, text)


def render():
    """Render the AI Chatbot page."""
    _init_session()

    st.markdown(
        """
        <div class="sa-hero">
            <h1>🤖 AgriBot - AI Agriculture Assistant</h1>
            <p>Ask about soil health, fertilizers, crop selection, irrigation, and plant diseases.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("💡 Example questions you can ask"):
        st.markdown(
            "- What fertilizer is best for nitrogen-deficient soil?\n"
            "- How do I improve soil with high salinity?\n"
            "- What irrigation method suits wheat farming?\n"
            "- How do I interpret a high EC value in my soil report?\n"
            "- How can I improve soil fertility?\n"
            "- How can I increase crop yield?\n"
            "- Common diseases in wheat?\n\n"
        )

    chat_container = st.container()
    with chat_container:
        for role, text in st.session_state.chat_messages:
            if role == "user":
                st.markdown(f'<div class="sa-chat-user">🧑‍🌾 {text}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="sa-chat-bot">🤖 {text}</div>', unsafe_allow_html=True)

    question = st.chat_input("Ask AgriBot about soil, fertilizers, crops, irrigation...")

    if question:
        st.session_state.chat_messages.append(("user", question))
        with st.spinner("AgriBot is thinking..."):
            try:
                result = ask_chatbot(question=question, session_id=st.session_state.session_id)
                # The backend echoes back the session_id it used - keep them in sync.
                st.session_state.session_id = result.get("session_id", st.session_state.session_id)
                answer = result.get("answer", "I'm sorry, I couldn't generate a response.")
                sources = result.get("sources") or []
                if sources:
                    answer += f"\n\n*Sources: {', '.join(sources)}*"
            except requests.exceptions.ConnectionError:
                answer = "⚠️ Could not connect to the backend API. Please make sure it is running."
            except requests.exceptions.HTTPError as e:
                detail = e.response.json().get("detail", str(e)) if e.response is not None else str(e)
                answer = f"⚠️ {detail}"
            except Exception as e:
                answer = f"⚠️ Something went wrong: {str(e)}"

        st.session_state.chat_messages.append(("bot", answer))
        st.rerun()

    if st.session_state.chat_messages:
        if st.button("🗑️ Clear Conversation"):
            st.session_state.chat_messages = []
            st.rerun()
