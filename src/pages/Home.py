import streamlit as st


def main():
    homepage()


def homepage():
    st.title("AI Disease Evaluator")
    st.write(
        "Welcome to the AI Disease Evaluator. This app helps assess your medical condition and provides a likelihood of diseases based on your inputs."
    )
    if st.button("Lets Get Started!", icon="😎", use_container_width=True):
        st.session_state.curr_page = "assessment"
        st.rerun()


if __name__ == "__main__":
    main()
