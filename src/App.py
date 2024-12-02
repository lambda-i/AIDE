import streamlit as st
from src.components import homepage, assessment, results

# Initialize session state
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"

# Page routing
if st.session_state.current_page == "home":
    homepage()
elif st.session_state.current_page == "assessment":
    assessment()
elif st.session_state.current_page == "results":
    results()