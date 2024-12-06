import streamlit as st
import websockets
import asyncio
import json
from datetime import datetime
import requests
import os
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
from streamlit_modal import Modal

load_dotenv()

# GET BACKEND URL
host = os.getenv("HOST")
AI_DOC_NUM = os.getenv("PERSONAL_PHONE_NUMBER")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def main():
    st.title("Voice Call Conversation")

    # Initialise memory context and openai client
    initialise_chatbot()
    display_chat_history()
    handle_user_input()

    left_button, right_button = st.columns(2)
    # Render the circle with a button
    with left_button:
        help_button()

    # Button for clearing conversatin history
    with right_button:
        clear_conversation_history_button()


def initialise_chatbot():
    # You might still want to keep this for OpenAI integration
    if "openai_model" not in st.session_state:  # Default model
        client = OpenAI()
        client.api_key = os.getenv("OPENAI_API_KEY")
        st.session_state["openai_model"] = client

    if "messages" not in st.session_state or len(st.session_state["messages"]) == 0:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hi! How may I help you today!"}
        ]

    st.session_state.show_help = False


# Function to display the chat history on the app
def display_chat_history():
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            message = message["content"]
            st.write(add_timestamp(message))


# Function to handle user input and response generation
def handle_user_input():
    # Accept user input
    if prompt := st.chat_input("Ask me anything :)"):
        # Add user input to the chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(add_timestamp(prompt))

        # Generate assistant's response
        generate_assistant_response()


# Function to generate and display assistant response using Flask
def generate_assistant_response():
    with st.chat_message("assistant"):
        # replace with API call from minibackend
        completion = st.session_state["openai_model"].chat.completions.create(
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
            st.write(add_timestamp(response))
        else:
            st.write(add_timestamp("Error: Unable to get response from the server."))


# Function to display the circle with a button
def help_button(ready=False):
    # Define a unique key for the button
    if st.button("Talk to AIDoc", icon="🚨", use_container_width=True):
        st.write("Circle button clicked!")
        st.session_state.show_help = not st.session_state.show_help
        toggle_help()
    print("Alert button pressed.")

    if ready:
        # Connection to AI Doc
        connect_to_aidoc()


# Function to test websocket connection with backend
def connect_to_aidoc():
    if st.button("Begin Stream"):
        asyncio.run(start_stream())

    # Run WebSocket connection in background
    if st.button("Connect to Call"):
        asyncio.run(connect_websocket())


def clear_conversation_history_button():
    # Clear chat history
    if st.button("Clear History", icon="🗑️", use_container_width=True):
        st.session_state.messages = []


# Adds date time to message to reply
def add_timestamp(message):
    # Get timestamp of message
    current_datetime = datetime.now()
    formatted_datetime = current_datetime.strftime("%-d-%b-%y %H:%M")
    # Output response with date & time
    return f"[{formatted_datetime}]\n\n{message}"


# Show popup
def toggle_help():
    modal = Modal(key="PH Modal", title="Talk to our AI Doc!")
    if st.session_state.show_help:
        with modal.container():
            st.markdown(f"### Alloy: {AI_DOC_NUM}")


async def start_stream():
    # Start asyncio loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Get session id from server
    SESSION_ID_URL = f"http://{host}/api/get-session-id"
    response = requests.get(SESSION_ID_URL)
    print(f"Reponse Received: {response.json()}")
    session_id = response.json()["sessionId"]
    st.session_state.session_id = session_id
    print(f"Session ID generated: {session_id}")

    try:
        await connect_to_stream(session_id)
    finally:
        loop.close()


async def connect_to_stream(session_id):
    STREAM_URI = f"ws://{host}/stream/{session_id}"

    async with websockets.connect(STREAM_URI) as websocket:
        try:
            while True:
                message = await websocket.recv()
                print(f"Received: {message}")  # Or handle message however needed
        except websockets.ConnectionClosed:
            print("Connection closed")


async def connect_websocket():
    uri = "ws://localhost:5050/stream/"
    async with websockets.connect(uri) as websocket:
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)

                # Handle different message types
                if "type" in data:
                    if (
                        data["type"]
                        == "conversation.item.input_audio_transcription.completed"
                    ):
                        # Add user message
                        st.session_state.messages.append(
                            {
                                "role": "user",
                                "content": data["transcription"],
                                "timestamp": datetime.now().strftime("%H:%M:%S"),
                            }
                        )
                    elif data["type"] == "response.content.done":
                        # Add assistant message
                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": data["content"],
                                "timestamp": datetime.now().strftime("%H:%M:%S"),
                            }
                        )

                st.experimental_rerun()

            except websockets.exceptions.ConnectionClosed:
                st.error("WebSocket connection closed. Reconnecting...")
                break
            except Exception as e:
                st.error(f"Error: {str(e)}")
                break


if __name__ == "__main__":
    main()
