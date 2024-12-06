import streamlit as st
import websockets
import asyncio
import json
from datetime import datetime
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# GET BACKEND URL
host = os.getenv("HOST")
AI_DOC_NUM = os.getenv("PERSONAL_PHONE_NUMBER")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []


def main():
    st.title("Voice Call Conversation")

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(f"[{message['timestamp']}] {message['content']}")

    # Button for clearing conversatin history
    clear_conversation_history_button()

    # Render the circle with a button
    help_button()


# Function to handle user input and response generation
def handle_user_input():
    # Accept user input
    if prompt := st.chat_input("Ask me anything :)"):
        # Add user input to the chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        display_user_message(prompt)

        # Generate assistant's response
        generate_assistant_response(prompt)


# Function to display user message
def display_user_message(prompt):
    with st.chat_message("user"):
        st.markdown(prompt)


# Function to generate and display assistant response using Flask
def generate_assistant_response(user_input):
    with st.chat_message("assistant"):
        # Call the Flask API
        response = requests.post(
            "https://aira-77ad510980a9.herokuapp.com/api/get_response",
            json={"user_input": user_input},
        )

        if response.status_code == 200:
            response_data = response.json()
            assistant_response = response_data.get("response")

            # Add assistant response to the session state (chat history)
            st.session_state.messages.append(
                {"role": "assistant", "content": assistant_response}
            )
            st.markdown(assistant_response)  # Display the assistant's response
        else:
            st.markdown("Error: Unable to get response from the server.")


# Function to display the circle with a button
def help_button(ready=False):
    # Define a unique key for the button
    if st.button("Talk to AIDoc", key="circle_button", icon="🚨"):
        st.write("Circle button clicked!")
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
    if st.button("Clear History"):
        st.session_state.messages = []
        st.experimental_rerun()


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
