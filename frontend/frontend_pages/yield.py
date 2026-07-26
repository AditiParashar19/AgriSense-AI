import sys
import os

import streamlit as st
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.yield_api import predict_yield  # noqa: E402


def render():
    """Render the Yield Prediction page."""
    st.markdown(
        """
        <div class="sa-hero">
            <h1>🌾 Crop Yield Prediction</h1>
            <p>Estimate expected crop yield based on region, crop type, weather, and farming inputs.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("yield_form"):
        c1, c2 = st.columns(2)
        with c1:
            area = st.text_input("Area / Region", value="India")
            item = st.text_input("Crop Item", value="Wheat")
            year = st.number_input("Year", min_value=1990, max_value=2100, value=2024, step=1)
        with c2:
            rainfall = st.number_input("Average Rainfall (mm/year)", min_value=0.0, max_value=5000.0, value=600.0, step=5.0)
            pesticides = st.number_input("Pesticide Usage (tonnes)", min_value=0.0, max_value=100000.0, value=1200.0, step=10.0)
            temperature = st.number_input("Average Temperature (°C)", min_value=-10.0, max_value=60.0, value=22.0, step=0.5)

        submitted = st.form_submit_button("🌾 Predict Yield", use_container_width=True)

    if submitted:
        if not area.strip() or not item.strip():
            st.warning("Please enter both Area and Crop Item.")
            return

        with st.spinner("Calculating expected yield..."):
            try:
                result = predict_yield(
                    area=area.strip(),
                    item=item.strip(),
                    year=int(year),
                    rainfall=rainfall,
                    pesticides=pesticides,
                    temperature=temperature,
                )
                st.markdown(
                    f"""
                    <div class="sa-result">
                        <h3>✅ Predicted Yield: {result['predicted_yield']} {result['unit']}</h3>
                        <p>{result['message']}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.balloons()
            except requests.exceptions.ConnectionError:
                st.error("⚠️ Could not connect to the backend API. Please make sure it is running.")
            except requests.exceptions.HTTPError as e:
                detail = e.response.json().get("detail", str(e)) if e.response is not None else str(e)
                st.error(f"⚠️ {detail}")
            except Exception as e:
                st.error(f"⚠️ Something went wrong: {str(e)}")
