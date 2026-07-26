"""
chatbot_api.py
--------------
Thin HTTP client wrapper around the backend AI Chatbot (RAG) API.
"""

import os
import requests
from typing import Dict, Any, Optional

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
TIMEOUT = 60  # LLM generation can take a little longer than other requests


def ask_chatbot(question: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Send a question to the RAG-powered chatbot and return the parsed
    JSON response, which includes the answer and session id.
    """
    payload = {"question": question, "session_id": session_id}
    response = requests.post(f"{BACKEND_URL}/api/chatbot/chat", json=payload, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def get_chat_history(session_id: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    """Fetch chat history from the backend, optionally for a single session."""
    params = {"limit": limit}
    if session_id:
        params["session_id"] = session_id
    response = requests.get(f"{BACKEND_URL}/api/chatbot/history", params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()
