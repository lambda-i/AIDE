import streamlit as st
import json
from datetime import datetime
import requests
import os
from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from datetime import datetime
from pathlib import Path
import time

load_dotenv()

OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
QDRANT_URL = st.secrets["QDRANT_URL"]
QDRANT_API_KEY = st.secrets["QDRANT_API_KEY"]
PERSONAL_PHONE_NUMBER = st.secrets["PERSONAL_PHONE_NUMBER"]

# Get the absolute path to the project root directory
ROOT_DIR = Path(__file__).resolve().parents[2]
LOGO_PATH = str(ROOT_DIR / "src" / "utils" / "lambdai.png")

# Initialize OpenAI and Qdrant clients
client = OpenAI()
client.api_key = OPENAI_API_KEY
vectordb_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# END POINTS
CALL_STATUS_ENDPOINT = "https://aide-app-8fddbaafae53.herokuapp.com/api/get-session-id"  # Dummy endpoint for call status
SUMMARY_ENDPOINT = "http://example.com/summary"  # Dummy endpoint for summary generation


def main():
    header, home = st.columns([4, 1])
    with header:
        st.title("Voice Call Conversation with RAG")
    with home:
        if st.button("Back to Home", icon="🏠"):
            st.session_state.curr_page = "home"
            st.rerun()

    initialise_chatbot()
    display_chat_history()
    handle_user_input()

    left_button, right_button = st.columns(2)
    with left_button:
        help_button()

    with right_button:
        clear_conversation_history_button()


def initialise_chatbot():
    if "openai_model" not in st.session_state:
        st.session_state["openai_model"] = client

    if "messages" not in st.session_state or len(st.session_state["messages"]) == 0:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hi! How may I help you today!"}
        ]


def display_chat_history():
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(add_timestamp(message["content"]))


def handle_user_input():
    if prompt := st.chat_input("Ask me anything :)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(add_timestamp(prompt))
        generate_assistant_response(prompt)


def generate_assistant_response(user_input):
    with st.chat_message("assistant"):
        response = rag_system(user_input)
        if response:
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.write(add_timestamp(response))
        else:
            st.write(add_timestamp("Error: Unable to get a response."))


def rag_system(user_query):
    retrieved_contexts = query_qdrant(user_query)
    context_text = "\n".join(retrieved_contexts)

    messages = [
        {
            "role": "system",
            "content": "You are an AI doctor specializing in respiratory diseases. Respond to the user in a professional and conversational way. Provide clear, empathetic, and helpful guidance. Not too structured.",
        },
        {"role": "system", "content": f"Retrieved Context: {context_text}"},
        {"role": "user", "content": user_query},
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini", messages=messages, temperature=0.7
    )
    return response.choices[0].message.content.strip()


def query_qdrant(query_text):
    query_embedding = get_embedding(query_text)
    search_result = vectordb_client.search(
        collection_name="respiratory_disease_guide",
        query_vector=query_embedding,
        limit=5,
    )
    return [hit.payload["text"] for hit in search_result]


def get_embedding(text, model="text-embedding-3-small"):
    text = text.replace("\n", " ")
    return client.embeddings.create(input=[text], model=model).data[0].embedding


# Define the help button
def help_button():
    if st.button("🚨 Talk to AIDoc", use_container_width=True):
        call_assistance_dialog()  # Trigger the dialog when the button is pressed


@st.dialog("Call Assistance", width="large")
def call_assistance_dialog():
    st.write("Ready to initiate the call?")

    # Display the predefined phone number
    st.success(f"Call the number from your phone: {PERSONAL_PHONE_NUMBER}")

    if st.button(
        "Call ended? View & Download Call Summary Here!",
        icon="⬇️",
        use_container_width=True,
    ):
        summary_data = generate_summary()
        if summary_data:
            time.sleep(3)
            if "call_summary" not in st.session_state:
                st.session_state["call_summary"] = ""
            st.session_state.call_summary = summary_data
            st.session_state.curr_page = "pdfviewer"
            st.rerun()
        else:
            st.error("Unable to Generate Call Summary.")


# Function to simulate polling the call status endpoint
def get_call_status():
    try:
        response = requests.get(CALL_STATUS_ENDPOINT)
        if response.status_code == 200:
            return response.json().get("status")  # Expecting { "status": "ended" }
    except requests.exceptions.RequestException as e:
        st.error(f"Error checking call status: {str(e)}")
    return "in_progress"


def clear_conversation_history_button():
    if st.button("🗑️ Clear History", use_container_width=True):
        st.session_state.messages = []


def add_timestamp(message):
    current_datetime = datetime.now()
    formatted_datetime = current_datetime.strftime("%-d-%b-%y %H:%M")
    return f"[{formatted_datetime}]\n\n{message}"


def generate_summary():
    try:
        # Step 1: Fetch the session ID
        session_response = requests.post(
            "https://aide-app-8fddbaafae53.herokuapp.com/api/get-session-id"
        )
        if session_response.status_code == 200:
            session_id = session_response.json().get("sessionId")

            if not session_id:
                st.error("Session ID could not be retrieved.")
                return None

            # Step 2: Use the session ID to fetch the conversation summary
            summary_response = requests.get(
                f"https://aide-app-8fddbaafae53.herokuapp.com/conversation-summary/{session_id}"
            )
            if summary_response.status_code == 200:
                return summary_response.json()  # Return the JSON summary

            st.error("Failed to retrieve conversation summary.")
        else:
            st.error("Failed to generate session ID.")
    except requests.exceptions.RequestException as e:
        st.error(f"Error checking summary status: {str(e)}")

    return None


if __name__ == "__main__":
    main()
