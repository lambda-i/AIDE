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

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []


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


def main():
    st.title("Voice Call Conversation")

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(f"[{message['timestamp']}] {message['content']}")

    # Run more test
    # Run test connection
    if st.button("Begin Stream"):
        asyncio.run(start_stream())

    # Run WebSocket connection in background
    if st.button("Connect to Call"):
        asyncio.run(connect_websocket())

    # Clear chat history
    if st.button("Clear History"):
        st.session_state.messages = []
        st.experimental_rerun()


if __name__ == "__main__":
    main()
