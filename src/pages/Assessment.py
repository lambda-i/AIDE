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

OPENAI_API_KEY = st.secrets["api_keys"]["OPENAI_API_KEY"]

# Environment variables
host = os.getenv("HOST")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
PERSONAL_PHONE_NUMBER = os.getenv("PERSONAL_PHONE_NUMBER")

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
        # summary_data = generate_summary()
        summary_data = {
            "summary": "1. **Main Topics Discussed:**\n   - Management of cough, fever, and headache.\n   - Guidance on responding to chest pain.\n   - Urgent actions to take when vomiting blood.\n\n2. **Key Questions Asked:**\n   - What should be done for symptoms of cough, fever, and headache?\n   - How to respond to chest pain and when to seek urgent medical attention?\n   - What immediate actions should be taken after vomiting blood?\n\n3. **Important Information Provided:**\n   - For cough, fever, and headache: Stay hydrated, rest, and consider over-the-counter medications. Seek medical care if fever exceeds 39°C, symptoms worsen, or there are severe symptoms such as difficulty breathing.\n   - For chest pain: Assess pain severity; seek immediate medical attention if severe or accompanied by other serious symptoms (e.g., shortness of breath, sweating). For less severe pain, rest and consult a healthcare professional.\n   - For vomiting blood: This is a serious condition requiring prompt medical attention, suggesting a possible life-threatening condition. Immediate action includes contacting emergency services and avoiding food or drink until evaluated.",
            "timestamp": "2024-12-05T22: 27: 56.510682",
            "caller_number": "Unknown",
            "full_conversation": [
                {
                    "role": "user",
                    "content": "A user asked: 'I currently have a cough, fever, and headache. What should I do?' Please provide detailed advice on managing these symptoms, potential causes, and when it would be necessary to seek medical attention.",
                },
                {
                    "role": "assistant",
                    "content": "To manage your symptoms of cough, fever, and headache, ensure you stay hydrated, rest, and consider taking over-the-counter medications such as acetaminophen or ibuprofen for fever and pain relief. Potential causes for these symptoms include viral infections like the flu or colds, bacterial infections, or even sinusitis. Seek medical attention if your fever exceeds 39°C (102°F), symptoms worsen, if you experience severe headache or persistent cough, or if you have difficulty breathing.",
                },
                {
                    "role": "user",
                    "content": "A user asked: 'I currently have chest pain as well. Is there anything I should do?' Please provide guidance on how to respond to chest pain, including when it is urgent to seek medical attention.",
                },
                {
                    "role": "assistant",
                    "content": "If you are experiencing chest pain, it's crucial to assess its severity and associated symptoms. Seek immediate medical attention if the pain is severe, lasts more than a few minutes, is accompanied by shortness of breath, sweating, nausea, or radiates to the arm or jaw, as these could indicate a heart attack. For less severe pain, consider resting, taking deep breaths, and avoiding strenuous activities, but speaking to a healthcare professional is still advisable to determine the cause.",
                },
                {
                    "role": "user",
                    "content": "A user asked: 'I just vomited blood. What should I do?' Please provide urgent advice on the implications of vomiting blood and the immediate actions to take, including when to seek emergency medical help.",
                },
                {
                    "role": "assistant",
                    "content": "Vomiting blood is a serious condition that requires immediate medical attention. You should call emergency services or go to the nearest hospital right away, as it can indicate bleeding in the gastrointestinal tract, which could be life-threatening. While waiting for help, try to remain calm and avoid eating or drinking anything until evaluated by a healthcare professional to prevent further complications.",
                },
            ],
        }
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
