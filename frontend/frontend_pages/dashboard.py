"""
dashboard.py
------------
Streamlit page for the Dashboard & Prediction History feature.

Displays aggregate metrics (total crop predictions, yield predictions,
uploaded reports, chat sessions) plus recent activity tables pulled
from the backend's /api/dashboard/summary endpoint.
"""

import os
import pandas as pd
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def _fetch_summary():
    """Fetch the dashboard summary from the backend API."""
    response = requests.get(f"{BACKEND_URL}/api/dashboard/summary", timeout=30)
    response.raise_for_status()
    return response.json()


def _metric_card(icon: str, value, label: str):
    """Render a single styled metric card."""
    st.markdown(
        f"""
        <div class="sa-metric">
            <div class="sa-metric-icon">{icon}</div>
            <div class="sa-metric-value">{value}</div>
            <div class="sa-metric-label">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render():
    """Render the Dashboard page."""
    st.markdown(
        """
        <div class="sa-hero">
            <h1>📊 Dashboard</h1>
            <p>An overview of all crop predictions, yield predictions, soil reports, and chatbot activity.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        summary = _fetch_summary()
    except requests.exceptions.ConnectionError:
        st.error("⚠️ Could not connect to the backend API. Please make sure it is running.")
        return
    except Exception as e:
        st.error(f"⚠️ Failed to load dashboard: {str(e)}")
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _metric_card("🌱", summary["total_crop_predictions"], "Crop Predictions")
    with c2:
        _metric_card("🌾", summary["total_yield_predictions"], "Yield Predictions")
    with c3:
        _metric_card("🧪", summary["total_soil_reports"], "Soil Reports")
    with c4:
        _metric_card("🤖", summary["total_chat_sessions"], "Chat Sessions")

    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["🌱 Recent Crop Predictions", "🌾 Recent Yield Predictions",
         "🧪 Recent Soil Reports", "💬 Recent Chat Questions"]
    )

    with tab1:
        rows = summary.get("recent_crop_predictions", [])
        if rows:
            df = pd.DataFrame(rows)[
                ["created_at", "nitrogen", "phosphorus", "potassium",
                 "temperature", "humidity", "ph", "rainfall", "predicted_crop"]
            ]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No crop predictions yet. Try the Crop Recommendation feature!")

    with tab2:
        rows = summary.get("recent_yield_predictions", [])
        if rows:
            df = pd.DataFrame(rows)[
                ["created_at", "area", "item", "year", "rainfall",
                 "pesticides", "temperature", "predicted_yield"]
            ]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No yield predictions yet. Try the Yield Prediction feature!")

    with tab3:
        rows = summary.get("recent_soil_reports", [])
        if rows:
            df = pd.DataFrame(rows)[
                ["created_at", "nitrogen", "phosphorus",
                 "potassium", "ph", "organic_carbon", "ec", "health_score"]
            ]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No soil analyses yet. Try the Soil Health Analyzer feature!")

    with tab4:
        rows = summary.get("recent_chat_messages", [])
        if rows:
            df = pd.DataFrame(rows)[["created_at", "question", "answer"]]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No chat activity yet. Try asking AgriBot a question!")
