
"""
soil_report.py
---------------
Streamlit page for the Soil Health Analyzer.

REPLACES the previous OCR-based upload page. The farmer manually enters
six soil test values; results (nutrient status, health score, fertilizer
recommendations, improvement tips, suitable crops, warnings) come from
the backend Soil Health Analyzer, and a PDF report can be downloaded.

Every request is tagged with this browser's session_id (see app.py),
so results are scoped to this farmer only.
"""

import os
import sys

import requests
import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.soil_report_api import analyze_soil, download_soil_report_pdf  # noqa: E402

STATUS_COLORS = {
    "Low": "#e57373", "High": "#ffb74d", "Medium": "#81c784", "Optimal": "#66bb6a",
    "Acidic": "#e57373", "Neutral": "#66bb6a", "Alkaline": "#ffb74d",
}


def _status_badge(status: str) -> str:
    color = STATUS_COLORS.get(status, "#90a4ae")
    return f'<span style="background:{color}; color:white; padding:0.2rem 0.6rem; border-radius:999px; font-weight:600; font-size:0.82rem;">{status}</span>'


def _nutrient_cards(nutrient_status: dict):
    """Render a row of cards, one per soil parameter, with its value and status badge."""
    labels = {
        "nitrogen": ("🟢", "Nitrogen", "kg/ha"),
        "phosphorus": ("🟠", "Phosphorus", "kg/ha"),
        "potassium": ("🟣", "Potassium", "kg/ha"),
        "ph": ("💧", "pH", ""),
        "organic_carbon": ("🟤", "Organic Carbon", "%"),
        "ec": ("⚡", "EC", "dS/m"),
    }
    cols = st.columns(len(labels))
    for col, (key, (icon, label, unit)) in zip(cols, labels.items()):
        entry = nutrient_status.get(key, {})
        with col:
            st.markdown(
                f"""
                <div class="sa-metric">
                    <div class="sa-metric-icon">{icon}</div>
                    <div class="sa-metric-value">{entry.get('value', 'N/A')}{unit}</div>
                    <div class="sa-metric-label">{label}</div>
                    <div style="margin-top:0.4rem;">{_status_badge(entry.get('status', 'N/A'))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _health_score_block(score: float, rating: str):
    rating_colors = {"Excellent": "#2e7d32", "Good": "#66bb6a", "Moderate": "#ffb74d", "Poor": "#e57373"}
    color = rating_colors.get(rating, "#66bb6a")
    st.markdown(
        f"""
        <div class="sa-result">
            <h3>🩺 Soil Health Score</h3>
            <div style="display:flex; align-items:baseline; gap:1rem;">
                <span style="font-size:2.6rem; font-weight:800; color:{color};">{score}/100</span>
                <span style="background:{color}; color:white; padding:0.2rem 0.6rem; border-radius:999px; font-weight:600; font-size:0.82rem;">{rating}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(min(int(score), 100) / 100)


def render():
    """Render the Soil Health Analyzer page."""
    st.markdown(
        """
        <div class="sa-hero">
            <h1>🧪 Soil Health Analyzer</h1>
            <p>Manually enter your soil test values to get an instant health score, fertilizer plan, and crop suitability.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("soil_analyzer_form"):
        st.markdown("#### Enter Your Soil Test Values")
        c1, c2, c3 = st.columns(3)
        with c1:
            nitrogen = st.number_input("Nitrogen - N (kg/ha)", min_value=0.0, max_value=1000.0, value=245.0, step=5.0)
            ph = st.number_input("pH", min_value=0.0, max_value=14.0, value=6.8, step=0.1)
        with c2:
            phosphorus = st.number_input("Phosphorus - P (kg/ha)", min_value=0.0, max_value=500.0, value=18.0, step=1.0)
            organic_carbon = st.number_input("Organic Carbon (%)", min_value=0.0, max_value=10.0, value=0.45, step=0.05)
        with c3:
            potassium = st.number_input("Potassium - K (kg/ha)", min_value=0.0, max_value=1000.0, value=130.0, step=5.0)
            ec = st.number_input("Electrical Conductivity (dS/m)", min_value=0.0, max_value=20.0, value=0.6, step=0.1)

        submitted = st.form_submit_button("🩺 Analyze Soil Health", use_container_width=True)

    if submitted:
        with st.spinner("Analyzing soil health..."):
            try:
                result = analyze_soil(
                    session_id=st.session_state.session_id,
                    nitrogen=nitrogen, phosphorus=phosphorus, potassium=potassium,
                    ph=ph, organic_carbon=organic_carbon, ec=ec,
                )
                st.session_state.last_soil_analysis = result
            except requests.exceptions.ConnectionError:
                st.error("⚠️ Could not connect to the backend API. Please make sure it is running.")
                return
            except requests.exceptions.HTTPError as e:
                detail = e.response.json().get("detail", str(e)) if e.response is not None else str(e)
                st.error(f"⚠️ {detail}")
                return
            except Exception as e:
                st.error(f"⚠️ Something went wrong: {str(e)}")
                return

    result = st.session_state.get("last_soil_analysis")
    if not result:
        st.info("👆 Enter your soil values above and click Analyze to get started.")
        return

    st.success("✅ Analysis complete!")

    st.markdown("#### Nutrient Status")
    _nutrient_cards(result["nutrient_status"])

    _health_score_block(result["health_score"], result["health_rating"])

    if result.get("warnings"):
        st.markdown("#### ⚠️ Warnings")
        for w in result["warnings"]:
            st.warning(w)

    st.markdown("#### 🧴 Fertilizer Recommendations")
    if result.get("fertilizer_recommendations"):
        for rec in result["fertilizer_recommendations"]:
            st.markdown(
                f"""
                <div class="sa-card">
                    <h3>{rec['nutrient']} - {rec['status']}</h3>
                    <p><b>Recommended:</b> {', '.join(rec['recommended'])}</p>
                    <p><b>Reason:</b> {rec['reason']}</p>
                    <p><b>Application:</b> {rec['application']}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            """<div class="sa-card"><p>✅ Nutrient levels are sufficient - no additional fertilizer is required.</p></div>""",
            unsafe_allow_html=True,
        )

    st.markdown("#### 🌾 Suitable Crops")
    crops = result["suitable_crops"]
    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        st.markdown(
            f"""<div class="sa-card"><h3>✅ Highly Suitable</h3><p>{', '.join(crops['highly_suitable']) or 'None'}</p></div>""",
            unsafe_allow_html=True,
        )
    with cc2:
        st.markdown(
            f"""<div class="sa-card"><h3>🟡 Moderately Suitable</h3><p>{', '.join(crops['moderately_suitable']) or 'None'}</p></div>""",
            unsafe_allow_html=True,
        )
    with cc3:
        st.markdown(
            f"""<div class="sa-card"><h3>🚫 Not Recommended</h3><p>{', '.join(crops['not_recommended']) or 'None'}</p></div>""",
            unsafe_allow_html=True,
        )

    st.markdown("#### 🛠️ Soil Improvement Tips")
    for tip in result.get("improvement_tips", []):
        st.markdown(f"- {tip}")

    st.markdown("#### 📄 Download Report")
    try:
        pdf_bytes = download_soil_report_pdf(st.session_state.session_id)
        st.download_button(
            "⬇️ Download PDF Report",
            data=pdf_bytes,
            file_name="soil_health_report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    except requests.exceptions.RequestException:
        st.caption("PDF report will be available once the backend confirms this analysis.")