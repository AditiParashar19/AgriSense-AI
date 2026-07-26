"""
crop.py
-------
Streamlit page for the Crop Recommendation feature.
"""

import sys
import os

import streamlit as st
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.crop_api import predict_crop  # noqa: E402


def render():
    """Render the Crop Recommendation page."""
    st.markdown(
        """
        <div class="sa-hero">
            <h1>🌱 Crop Recommendation</h1>
            <p>Enter your soil nutrients and local climate conditions to get an AI-recommended crop.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("crop_form"):
        st.markdown("#### Soil Nutrients (kg/ha)")
        c1, c2, c3 = st.columns(3)
        with c1:
            nitrogen = st.number_input("Nitrogen (N)", min_value=0.0, max_value=500.0, value=90.0, step=1.0)
        with c2:
            phosphorus = st.number_input("Phosphorus (P)", min_value=0.0, max_value=500.0, value=42.0, step=1.0)
        with c3:
            potassium = st.number_input("Potassium (K)", min_value=0.0, max_value=500.0, value=43.0, step=1.0)

        st.markdown("#### Climate Conditions")
        c4, c5 = st.columns(2)
        with c4:
            temperature = st.number_input("Temperature (°C)", min_value=-10.0, max_value=60.0, value=25.0, step=0.5)
            humidity = st.number_input("Humidity (%)", min_value=0.0, max_value=100.0, value=80.0, step=1.0)
        with c5:
            ph = st.number_input("Soil pH", min_value=0.0, max_value=14.0, value=6.5, step=0.1)
            rainfall = st.number_input("Rainfall (mm)", min_value=0.0, max_value=5000.0, value=200.0, step=5.0)

        submitted = st.form_submit_button("🌱 Recommend Crop", use_container_width=True)

    if submitted:
        with st.spinner("Analyzing soil and climate data..."):
            try:
                result = predict_crop(
                    nitrogen=nitrogen,
                    phosphorus=phosphorus,
                    potassium=potassium,
                    temperature=temperature,
                    humidity=humidity,
                    ph=ph,
                    rainfall=rainfall,
                )
                st.markdown(
                    f"""
                    <div class="sa-result">
                        <h3>✅ Recommended Crop: {result['predicted_crop']}</h3>
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
