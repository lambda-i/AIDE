import streamlit as st
import base64
from pathlib import Path


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

    render_fullscreen_pdf("./conversation_summary_medical.pdf")


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


def render_fullscreen_pdf(pdf_path: str, height_percentage: int = 100) -> None:
    """
    Render a PDF file in Streamlit that takes up the entire viewport.

    Args:
        pdf_path: Path to the PDF file
        height_percentage: Percentage of viewport height to use (default: 100)
    """
    # Validate PDF path
    if not Path(pdf_path).is_file():
        st.error(f"PDF file not found: {pdf_path}")
        return

    # Hide Streamlit's default elements
    hide_streamlit_style = """
        <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            .block-container {
                padding-top: 0;
                padding-bottom: 10;
                padding-left: 5;
                padding-right: 5;
            }
            .stApp {
                margin: 0;
                padding: 0;
            }
            iframe {
                border: none !important;
            }
            /* Custom scrollbar styles */
            ::-webkit-scrollbar {
                width: 10px;
                height: 10px;
            }
            ::-webkit-scrollbar-track {
                background: #f1f1f1;
            }
            ::-webkit-scrollbar-thumb {
                background: #888;
                border-radius: 5px;
            }
            ::-webkit-scrollbar-thumb:hover {
                background: #555;
            }
        </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

    try:
        # Read and encode PDF
        with open(pdf_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode("utf-8")

        # Calculate viewport height in pixels
        # Use JavaScript to get actual viewport height
        js_height = """
            <script>
                window.addEventListener('load', function() {
                    // Get viewport height
                    var vh = window.innerHeight;
                    // Update iframe height
                    var iframe = document.querySelector('iframe');
                    iframe.style.height = vh + 'px';
                });
                // Handle resize events
                window.addEventListener('resize', function() {
                    var vh = window.innerHeight;
                    var iframe = document.querySelector('iframe');
                    iframe.style.height = vh + 'px';
                });
            </script>
        """

        # Create PDF viewer with additional parameters for better viewing
        pdf_display = f"""
            <div style="display: flex; justify-content: center; width: 100%; height: 100vh; margin: 0; padding: 0;">
                <iframe 
                    src="data:application/pdf;base64,{base64_pdf}#toolbar=0&navpanes=0&scrollbar=0&view=FitH"
                    width="100%"
                    style="height: 100vh;"
                    type="application/pdf"
                    frameborder="0"
                >
                </iframe>
            </div>
            {js_height}
        """

        st.markdown(pdf_display, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error rendering PDF: {str(e)}")


if __name__ == "__main__":
    main()
