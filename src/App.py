import streamlit as st
from pages import assessment
from pages import docs
from pages import pdfviewer

# Set page configuration to use a "wide" layout
st.set_page_config(
    page_title="AIDE",  # Page title
    layout="wide",  # Use wide layout to fit content better
    initial_sidebar_state="collapsed",  # Collapse sidebar for a cleaner look
)


def main():
    initialise_session_state()
    if st.session_state.curr_page == "home":
        App()
    elif st.session_state.curr_page == "assessment":
        assessment()
    elif st.session_state.curr_page == "docs":
        docs()
    elif st.session_state.curr_page == "pdfviewer":
        pdfviewer()


def App():
    st.title("Welcome to AIDE")
    # Button to switch to the "assessment" page
    left_button, right_button = st.columns(2)
    with left_button:
        if st.button("Lets Get Started!", icon="😎", use_container_width=True):
            st.session_state.curr_page = "assessment"
            st.rerun()

    with right_button:
        if st.button("Read Our Project Guide!", icon="📃", use_container_width=True):
            st.session_state.curr_page = "docs"
            st.rerun()


def initialise_session_state():
    if "curr_page" not in st.session_state:
        st.session_state["curr_page"] = "home"


if __name__ == "__main__":
    main()
