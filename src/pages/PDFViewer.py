import streamlit as st
import base64
from src.utils import generate_pdf_from_json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
LOGO_PATH = str(ROOT_DIR / "src" / "utils" / "lambdai.png")


def main():
    # Custom CSS to fix buttons at the top
    st.markdown(
        """
        <style>
        .fixed-buttons {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            background-color: white;
            z-index: 1000;
            padding: 0px;
            box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
        }
        .content {
            margin-top: 80px; /* Push content down to avoid overlap with fixed buttons */
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Render fixed buttons
    st.markdown('<div class="fixed-buttons">', unsafe_allow_html=True)
    left_button, right_button = st.columns(2)
    with left_button:
        back_home_button()
    with right_button:
        back_chat_button()

    render_fullscreen_pdf()


# Define back home button
def back_home_button():
    if st.button("Back to Home", icon="🏡", use_container_width=True):
        st.session_state.curr_page = "home"
        st.rerun()


# Define button back to chat
def back_chat_button():
    if st.button("Back to Chat", icon="💬", use_container_width=True):
        st.session_state.curr_page = "assessment"
        st.rerun()


def render_fullscreen_pdf() -> None:
    summary_data = st.session_state.call_summary
    pdf_bytes = generate_pdf_from_json(summary_data, LOGO_PATH)
    b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

    # Display PDF in Streamlit
    pdf_display = f"""
        <iframe src="data:application/pdf;base64,{b64_pdf}" 
                width="100%"
                style="height: 100vh;"
                type="application/pdf"
                frameborder="0"
        </iframe>
        """
    st.markdown(pdf_display, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
