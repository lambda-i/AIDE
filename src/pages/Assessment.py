import streamlit as st
import websockets
import asyncio
import json
from datetime import datetime
import requests
import os
from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from datetime import datetime
import time
from utils.pdf_generate import create_medical_pdf
from pathlib import Path
import base64

load_dotenv()

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
CALL_STATUS_ENDPOINT = (
    "https://aide-app-8fddbaafae53.herokuapp.com/api/get-session-id"  # Dummy endpoint for call status
)
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

    if st.button("JUNWEI Call ended? Generate call summary here!"):
        summary_data = generate_summary()
        if summary_data:
            st.write(summary_data)  ## remove later

        file_name = create_medical_pdf(summary_data, LOGO_PATH)
        print(file_name)

        # Embed the PDF as a viewer
        with open(f"./{file_name}", "rb") as pdf_file:

            pdf_data = pdf_file.read()

            # Create a temporary file path for the PDF viewer
            temp_file_path = f"temp_{int(time.time())}.pdf"
            with open(temp_file_path, "wb") as temp_file:
                temp_file.write(pdf_data)

            # Embed the PDF viewer using HTML and iframe
            st.markdown(
                f"""
                <iframe src="data:application/pdf;base64,{base64.b64encode(pdf_data).decode('utf-8')}" 
                        width="700" 
                        height="500" 
                        type="application/pdf">
                </iframe>
                """,
                unsafe_allow_html=True,
            )


    ####

    # call_status = get_call_status()

    # # Poll until the call ends
    # if call_status != "ended":

    #     st.success("Call ended. Generating summary now...")

    #     # Wait for the summary and generate the PDF
    #     summary_data = wait_for_summary()
    #     st.write(summary_data)  ## remove later

    #     file_name = create_medical_pdf(summary_data, LOGO_PATH)
    #     print(file_name)

    #     # Embed the PDF as a viewer
    #     with open(f"./{file_name}", "rb") as pdf_file:

    #         pdf_data = pdf_file.read()

    #         # Create a temporary file path for the PDF viewer
    #         temp_file_path = f"temp_{int(time.time())}.pdf"
    #         with open(temp_file_path, "wb") as temp_file:
    #             temp_file.write(pdf_data)

    #         # Embed the PDF viewer using HTML and iframe
    #         st.markdown(
    #             f"""
    #             <iframe src="data:application/pdf;base64,{base64.b64encode(pdf_data).decode('utf-8')}" 
    #                     width="700" 
    #                     height="500" 
    #                     type="application/pdf">
    #             </iframe>
    #             """,
    #             unsafe_allow_html=True,
    #         )

        # st.success("PDF generated successfully!")

        # # Display the PDF in the frontend (as an embedded object)
        # with open(file_path, "rb") as pdf_file:
        #     pdf_data = "conversation_summary_medical.pdf".read()
        #     print(pdf_data)

        #     # Embed the PDF
        #     st.write("### Generated PDF Preview:")
        #     st.download_button(
        #         label="📄 Download Summary",
        #         data=pdf_data,
        #         file_name="conversation_summary_medical.pdf",
        #         mime="application/pdf",
        #     )


# Function to simulate polling the call status endpoint
def get_call_status():
    try:
        response = requests.get(CALL_STATUS_ENDPOINT)
        if response.status_code == 200:
            return response.json().get("status")  # Expecting { "status": "ended" }
    except requests.exceptions.RequestException as e:
        st.error(f"Error checking call status: {str(e)}")
    return "in_progress"


# Function to wait for summary generation
def wait_for_summary():
    st.write("Waiting for the summary to be ready...")
    root_dir = Path(__file__).resolve().parents[2]
    test_json_path = root_dir / "test.json"

    while True:
        try:
            response = requests.get(SUMMARY_ENDPOINT)
            if response.status_code == 404:  # For testing purposes
                # Load test JSON file
                with open(test_json_path, "r") as f:
                    test_data = json.load(f)
                return test_data
            elif response.status_code == 200:  # When endpoint is ready
                return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Error checking summary status: {str(e)}")
        time.sleep(2)  # Polling interval


def clear_conversation_history_button():
    if st.button("🗑️ Clear History", use_container_width=True):
        st.session_state.messages = []


def add_timestamp(message):
    current_datetime = datetime.now()
    formatted_datetime = current_datetime.strftime("%-d-%b-%y %H:%M")
    return f"[{formatted_datetime}]\n\n{message}"

# def render_pdf(pdf_path):
#     """Render a PDF file in Streamlit without sidebar and set zoom to 90%."""
#     with open(pdf_path, "rb") as f:
#         base64_pdf = base64.b64encode(f.read()).decode("utf-8")

#     # Add parameters to hide toolbar, navigation panes, and set zoom
#     pdf_display = f"""
#         <iframe 
#             src="data:application/pdf;base64,{base64_pdf}#toolbar=0&navpanes=0&zoom=90" 
#             width="100%" 
#             height="800" 
#             type="application/pdf">
#         </iframe>
#     """
#     st.markdown(pdf_display, unsafe_allow_html=True)

def generate_summary():
    try:
        # Step 1: Fetch the session ID
        session_response = requests.post("https://aide-app-8fddbaafae53.herokuapp.com/api/get-session-id")
        if session_response.status_code == 200:
            session_id = session_response.json().get("sessionId")
            
            if not session_id:
                st.error("Session ID could not be retrieved.")
                return None

            # Step 2: Use the session ID to fetch the conversation summary
            summary_response = requests.get(f"https://aide-app-8fddbaafae53.herokuapp.com/conversation-summary/{session_id}")
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
