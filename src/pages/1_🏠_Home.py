import streamlit as st


def homepage():
    st.title("AI Disease Evaluator")
    st.write(
        "Welcome to the AI Disease Evaluator. This app helps assess your medical condition and provides a likelihood of diseases based on your inputs."
    )
    if st.button("Start Assessment"):
        st.session_state.current_page = "assessment"
