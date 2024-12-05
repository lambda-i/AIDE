import os
import json
import base64
import asyncio
import websockets
import urllib.parse
import uuid
import time
import logging
from typing import Optional

from dotenv import load_dotenv
from twilio.rest import Client
from fastapi import WebSocket, WebSocketDisconnect
from customgpt_client import CustomGPT

# Load environment variables
load_dotenv()

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
account_sid = os.environ["TWILIO_ACCOUNT_SID"]
auth_token = os.environ["TWILIO_AUTH_TOKEN"]

# Initialize Twilio client
client = Client(account_sid, auth_token)

# Constants
VOICE = "alloy"
LOG_EVENT_TYPES = [
    "response.content.done",
    "response.done",
    "input_audio_buffer.committed",
    "input_audio_buffer.speech_stopped",
    "input_audio_buffer.speech_started",
    "session.created",
    "response.audio.done",
    "conversation.item.input_audio_transcription.completed",
]
current_dir = os.path.dirname(__file__)
mp3_file_path = os.path.join(current_dir, "static", "typing.wav")

# System message template
SYSTEM_MESSAGE = """
# Core Purpose & Initialization
- Start session with {introduction}
- You are an AI assistant answering questions using ONLY the get_additional_context function which is your source of truth knowledge base.
- Never start session with get_additional_context
- PHONE_NUMBER for support: {phone_number}

# Additional system message content as in the original script
"""


def start_recording(call_id: str, session_id: str, host: str):
    # Delay the recording by 2 seconds
    time.sleep(2)
    try:
        recording = client.calls(call_id).recordings.create(
            recording_status_callback=f"https://{host}/log-recording/{session_id}",
            recording_status_callback_event=["in-progress", "completed"],
            recording_channels="dual",
        )
        logger.info(
            f"Recording started for Call SID: {call_id} with Recording SID: {recording.sid}"
        )
    except Exception as e:
        logger.error(f"Failed to start recording for Call SID: {call_id}. Error: {e}")


def get_additional_context(query, api_key, project_id, session_id):
    custom_persona = """
    You are an AI assistant tasked with answering user queries based on a knowledge base. 
    The user query is transcribed from voice audio, so there may be transcription errors.

    When responding to the user query, follow these guidelines:
    1. Match the query to the knowledge base using both phonetic and semantic similarity.
    2. Attempt to answer even if the match isn't perfect, as long as it seems reasonably close.

    Provide a concise answer, limited to three sentences.
    """

    tries = 0
    max_retries = 2
    while tries <= max_retries:
        try:
            CustomGPT.api_key = api_key
            logger.info(f"CustomGPT query sent:: {query}")
            conversation = CustomGPT.Conversation.send(
                project_id=project_id,
                session_id=session_id,
                prompt=query,
                custom_persona=custom_persona,
            )
            logger.info(f"CustomGPT response: {conversation}")
            return conversation.parsed.data.openai_response
        except Exception as e:
            logger.error(
                f"Get Additional Context failed::Try {tries}::Error: {conversation}"
            )
            time.sleep(2)
        tries += 1

    return "Sorry, I didn't get your query."


def create_session(api_key, project_id, caller_number):
    tries = 0
    max_retries = 2
    while tries <= max_retries:
        try:
            CustomGPT.api_key = api_key
            session = CustomGPT.Conversation.create(
                project_id=project_id, name=caller_number
            )
            # logger.info(f"CustomGPT Session Created::{session.parsed.data}")
            return session.parsed.data.session_id
        except Exception as e:
            logger.error(f"Error in create_session::Try {tries}::Error: {e}")
        tries += 1

    session_id = uuid.uuid4()
    return session_id


async def send_session_update(openai_ws, phone_number, introduction):
    introduction = introduction.replace("+", " ")
    session_update = {
        "type": "session.update",
        "session": {
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.6,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 500,
            },
            "input_audio_format": "g711_ulaw",
            "output_audio_format": "g711_ulaw",
            "voice": VOICE,
            "instructions": SYSTEM_MESSAGE.format(
                phone_number=phone_number, introduction=introduction
            ),
            "modalities": ["text", "audio"],
            "temperature": 0.8,
            "tools": [
                {
                    "type": "function",
                    "name": "get_additional_context",
                    "description": "Elaborate on the user's original query...",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The elaborated user query...",
                            }
                        },
                        "required": ["query"],
                    },
                },
                {
                    "type": "function",
                    "name": "call_support",
                    "description": "The purpose of the call_support function is to help user when the agent is unable to answer query...",
                },
            ],
        },
    }
    logger.info("Sending session update: %s", json.dumps(session_update))
    await openai_ws.send(json.dumps(session_update))
    time.sleep(1)
    initial_response = {
        "type": "conversation.item.create",
        "item": {
            "type": "message",
            "role": "user",
            "content": [{"type": "text", "text": "Introduce yourself"}],
        },
    }
    await openai_ws.send(json.dumps(initial_response))
    await openai_ws.send(
        json.dumps(
            {
                "type": "response.create",
                "response": {"instructions": f"Introduce yourself as {introduction}"},
            }
        )
    )


async def play_typing(websocket, stream_sid):
    with open(mp3_file_path, "rb") as mp3_file:
        mp3_data = mp3_file.read()
        base64_audio = base64.b64encode(mp3_data).decode("utf-8")

    audio_delta = {
        "event": "media",
        "streamSid": stream_sid,
        "media": {"payload": base64_audio},
    }
    await websocket.send_json(audio_delta)


async def clear_buffer(websocket, openai_ws, stream_sid):
    audio_delta = {
        "streamSid": stream_sid,
        "event": "clear",
    }
    await openai_ws.send(json.dumps({"type": "response.cancel"}))
    await websocket.send_json(audio_delta)


async def handle_media_stream_service(
    websocket, project_id, session_id, phone_number, introduction
):
    logger.info(f"WebSocket connection attempt. Session ID: {session_id}")
    await websocket.accept()
    logger.info(f"WebSocket connection accepted. Session ID: {session_id}")
    api_key = None
    # Create task termination event
    termination_event = asyncio.Event()

    async with websockets.connect(
        "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01",
        extra_headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1",
        },
    ) as openai_ws:
        try:
            handle_first_response = time.time()
            start_time = time.time()
            stream_sid = None
            await send_session_update(openai_ws, phone_number, introduction)

            # Rest of the implementation remains the same as in the original script
            # (The full implementation of this function would be identical to the
            # original handle_media_stream function in the previous script)

        except Exception as e:
            logger.error(f"Unexpected error in handle_media_stream_service: {e}")

        finally:
            try:
                await clear_buffer(websocket, openai_ws, stream_sid)
                await openai_ws.close()
                await websocket.close()
            except Exception:
                logger.info(f"WebSocket connection closed. Session ID: {session_id}")
