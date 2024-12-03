import os
import streamlit as st
from openai import OpenAI

from dotenv import load_dotenv

load_dotenv()

client = OpenAI()
client.api_key = os.getenv("OPENAI_API_KEY")


# Main function to initialize the app
def assessment():
    if st.button("Continue to Results"):
        st.session_state.current_page = "results"
    initialise_chatbot()
    display_chat_history()
    handle_user_input()


def initialise_chatbot():
    # You might still want to keep this for OpenAI integration
    if "openai_model" not in st.session_state:  # Default model
        client = OpenAI()
        client.api_key = os.getenv("OPENAI_API_KEY")
        st.session_state["openai_model"] = client

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hi! How may I help you today!"}
        ]


# Function to display the chat history on the app
def display_chat_history():
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


# Function to handle user input and response generation
def handle_user_input():
    # Accept user input
    if prompt := st.chat_input("Ask me anything :)"):
        # Add user input to the chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate assistant's response
        generate_assistant_response(prompt)


# Function to generate and display assistant response using Flask
def generate_assistant_response(user_input):
    with st.chat_message("assistant"):
        # replace with API call from minibackend
        completion = client.chat.completions.create(
            model="gpt-4o-mini",  # Use the desired GPT model (e.g., gpt-3.5-turbo, gpt-4)
            messages=st.session_state["messages"],  # Provide the conversation history
            temperature=0.7,  # Controls creativity
            max_tokens=500,  # Limits the length of the response
        )
        # Extract and return the assistant's response
        response = completion.choices[0].message.content

        if response != None:
            # Add assistant response to the session state (chat history)
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.markdown(response)  # Display the assistant's response
        else:
            st.markdown("Error: Unable to get response from the server.")
