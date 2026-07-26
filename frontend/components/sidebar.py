import streamlit as st

NAV_ITEMS = [
    ("home",  "Home"),
    ("dashboard", "Dashboard"),
    ("crop", "Crop Recommendation"),
    ("yield", "Yield Prediction"),
    ("soil_report", "Soil Report Analysis"),
    ("chatbot", "AI Chatbot"),
]


def render_sidebar() -> str:
    """
    Render the sidebar navigation and return the key of the currently
    selected page.
    """
    with st.sidebar:
        st.markdown(
            """
            <div style="text-align:center; padding: 0.5rem 0 1rem 0;">
                <div style="font-size:2.4rem;">🌿</div>
                <div style="font-size:1.35rem; font-weight:800;">AgriSense-AI</div>
                <div style="font-size:0.8rem; opacity:0.85;">Precision Agriculture, Powered by AI</div>
            </div>
            <hr style="border-color: rgba(255,255,255,0.2);">
            """,
            unsafe_allow_html=True,
        )

        labels = [f" {label}" for _, label in NAV_ITEMS]
        keys = [key for key, _ in NAV_ITEMS]

        if "current_page" not in st.session_state:
            st.session_state.current_page = "home"

        default_index = keys.index(st.session_state.current_page) if st.session_state.current_page in keys else 0

        selected_label = st.radio(
            "Navigation",
            options=labels,
            index=default_index,
            label_visibility="collapsed",
        )
        selected_key = keys[labels.index(selected_label)]
        st.session_state.current_page = selected_key

        st.markdown("<hr style='border-color: rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="font-size:0.78rem; font-weight:bold; opacity:0.85; text-align:center; padding-top:0.5rem;">
                Built for Farmers with ❤️<br>
                @ 2026
            </div>
            """,
            unsafe_allow_html=True,
        )

    return selected_key
