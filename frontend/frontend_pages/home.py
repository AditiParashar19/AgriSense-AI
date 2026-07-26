import streamlit as st

def render():
    """Render the Home page."""
    st.markdown(
        """
        <div class="sa-hero">
            <h1>🌿 Welcome to AgriSense-AI</h1>
            <p>Your AI-powered precision agriculture assistant — smarter crops, healthier soil, better yields.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### What would you like to do today?")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div class="sa-card">
                <h3>🌱 Crop Recommendation</h3>
                <p>Get the best crop to grow based on your soil nutrients and local climate.</p>
                <span class="sa-badge">Machine Learning</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Go to Crop Recommendation", use_container_width=True, key="home_crop_btn"):
            st.session_state.current_page = "crop"
            st.rerun()

    with col2:
        st.markdown(
            """
            <div class="sa-card">
                <h3>🌾 Yield Prediction</h3>
                <p>Estimate expected crop yield based on region, weather, and farming inputs.</p>
                <span class="sa-badge">Machine Learning</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Go to Yield Prediction", use_container_width=True, key="home_yield_btn"):
            st.session_state.current_page = "yield"
            st.rerun()

    with col3:
        st.markdown(
            """
            <div class="sa-card">
                <h3>🧪 Soil Report Analysis</h3>
                <p>Upload a soil test report (PDF/Image) and get an instant health summary.</p>
                <span class="sa-badge">Soil Health Analysis</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Go to Soil Report Analysis", use_container_width=True, key="home_soil_btn"):
            st.session_state.current_page = "soil_report"
            st.rerun()

    col4, col5 = st.columns(2)

    with col4:
        st.markdown(
            """
            <div class="sa-card">
                <h3>🤖 AI Agriculture Chatbot</h3>
                <p>Ask questions about soil health, fertilizers, irrigation, diseases, and more.</p>
                <span class="sa-badge">RAG + Gemini 2.5 Flash</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Chat with AgriBot", use_container_width=True, key="home_chat_btn"):
            st.session_state.current_page = "chatbot"
            st.rerun()

    with col5:
        st.markdown(
            """
            <div class="sa-card">
                <h3>📊 Dashboard</h3>
                <p>Track all your predictions, soil reports, and chatbot activity in one place.</p>
                <span class="sa-badge">Analytics</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("View Dashboard", use_container_width=True, key="home_dash_btn"):
            st.session_state.current_page = "dashboard"
            st.rerun()

    st.markdown("---")
    st.markdown(
        """
        <div style="text-align:center; color: var(--sa-muted); padding: 0.5rem 0 1rem 0;">
            AgriSenseAI combines Machine Learning, RAG and Generative AI to support
            precision agriculture.
        </div>
        """,
        unsafe_allow_html=True,
    )
