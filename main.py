import os
import json
import base64
import asyncio
import websockets
import urllib.parse
from fastapi import (
    FastAPI,
    WebSocket,
    Request,
    WebSocketDisconnect,
    status,
    BackgroundTasks,
)
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect, Redirect, Dial, Stream
from dotenv import load_dotenv
from customgpt_client import CustomGPT
import uuid
import logging
import time
import redis
from datetime import datetime

from openai import OpenAI
from qdrant_client import QdrantClient
import pymupdf4llm
from src.assets.prompts import DEFAULT_INTRO, SYSTEM_MESSAGE

load_dotenv()

##############################################################
##############################################################
################### INITIALISING ENV VARS ####################
##############################################################
##############################################################

redis_url = urllib.parse.urlparse(os.environ.get("REDISCLOUD_URL"))
account_sid = os.environ["TWILIO_ACCOUNT_SID"]
auth_token = os.environ["TWILIO_AUTH_TOKEN"]
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing the OpenAI API key. Please set it in the .env file.")
PORT = int(os.getenv("PORT", 5050))
PERSONAL_PHONE_NUMBER = os.getenv("PERSONAL_PHONE_NUMBER")

##############################################################
##############################################################
################### INITIALISING CLIENTS #####################
##############################################################
##############################################################

client_openai = OpenAI()

vectordb_client = QdrantClient(
    url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY")
)

redis_client = redis.Redis(
    host=redis_url.hostname,
    port=redis_url.port,
    password=redis_url.password,
    ssl=True,
    ssl_cert_reqs=None,
)

twilio_client = Client(account_sid, auth_token)

app = FastAPI()

##############################################################
##############################################################
################# INITIALISING LOCAL VARS ####################
##############################################################
##############################################################

CURR_SESSION_ID = None  # Track current session for frontend to join
active_connections = []

conversation_histories = {}  # for session history

conversation_summaries = {}  # for summaries
session_caller_numbers = {}

# LOGGER
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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MOUNT TYPING SOUND
current_dir = os.path.dirname(__file__)
mp3_file_path = os.path.join(current_dir, "static", "typing.wav")
app.mount("/static", StaticFiles(directory="static"), name="static")


# Takes in the call from Twilio and Streams it into OPENAI RealTime API
@app.api_route("/incoming-call", methods=["GET", "POST"])
async def handle_incoming_call(
    request: Request,
    background_tasks: BackgroundTasks,
    # project_id: int,
    api_key: Optional[str] = OPENAI_API_KEY,
    phone_number: Optional[str] = None,
    introduction: Optional[str] = DEFAULT_INTRO,
):
    logger.info(f"Introduction: {introduction}")
    form_data = (
        await request.form() if request.method == "POST" else request.query_params
    )
    caller_number = form_data.get("From", "Unknown")
    logger.info(f"Caller: {caller_number}")
    # session_id = create_session(api_key, project_id, caller_number)
    session_id = create_session(api_key, caller_number)
    CURR_SESSION_ID = session_id
    session_caller_numbers[session_id] = caller_number  # check
    # logger.info(f"Project::{project_id}")
    logger.info(f"Incoming call handled. Session ID: {session_id}")
    host = request.url.hostname
    call_id = form_data.get("CallSid")
    response = VoiceResponse()
    response.pause(length=1)
    connect = Connect()
    phone_number = PERSONAL_PHONE_NUMBER
    encoded_phone_number = urllib.parse.quote_plus(phone_number)
    encoded_introduction = urllib.parse.quote_plus(introduction)
    stream = Stream(
        url=f"wss://{host}/media-stream/session/{session_id}/{encoded_phone_number}/{encoded_introduction}"
    )
    stream.parameter(name="api_key", value=api_key)
    connect.append(stream)
    response.append(connect)
    if phone_number:
        phone_number = urllib.parse.quote_plus(phone_number)
    response.redirect(
        url=f"https://{host}/end-stream/{session_id}?phone_number={phone_number}"
    )
    background_tasks.add_task(start_recording, call_id, session_id, host)
    return HTMLResponse(content=str(response), media_type="application/xml")


@app.post("/log-recording/{session_id}")
async def log_recording(session_id: str, request: Request):
    form_data = await request.form()
    recording_url = form_data.get("RecordingUrl")
    if recording_url:
        logger.info(f"Recording for session {session_id}: {recording_url}")
    else:
        logger.warning(f"No recording URL received for session {session_id}")
    return {"status": "Recording logged"}


@app.api_route("/end-stream/{session_id}", methods=["GET", "POST"])
async def handle_end_call(
    request: Request,
    session_id: Optional[str] = None,
    phone_number: Optional[str] = None,
):
    state = redis_client.get(session_id)
    if state:
        state = state.decode("utf-8")
    logger.info(f"Ending Stream with state: {state}")
    response = VoiceResponse()
    if state == "transfer":
        dial = Dial()
        dial.number(phone_number)
        response.append(dial)
    else:
        response.hangup()

    return HTMLResponse(content=str(response), media_type="application/xml")


# RealTime
@app.websocket("/media-stream/session/{session_id}/{phone_number}/{introduction}")
async def handle_media_stream(
    websocket: WebSocket, session_id: str, phone_number: str, introduction: str
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

            async def check_timeout():
                logger.info(f"Checking inactivity. Session ID: {session_id}")
                try:
                    while not termination_event.is_set():
                        current_time = time.time()
                        diff = current_time - start_time
                        if diff > 300:
                            logger.info(
                                f"Session timeout after 30 seconds of inactivity. Session ID: {session_id}"
                            )
                            termination_event.set()
                            await clear_buffer(websocket, openai_ws, stream_sid)
                            await websocket.close()
                            break
                        await asyncio.sleep(5)
                except Exception as e:
                    raise e

            asyncio.create_task(check_timeout())

            async def receive_from_twilio():
                nonlocal stream_sid, start_time, api_key
                while not termination_event.is_set():
                    try:
                        message = await websocket.receive_text()
                        data = json.loads(message)
                        if data["event"] == "media" and openai_ws.open:
                            audio_append = {
                                "type": "input_audio_buffer.append",
                                "audio": data["media"]["payload"],
                            }
                            await openai_ws.send(json.dumps(audio_append))
                        elif data["event"] == "start":
                            api_key = data["start"]["customParameters"]["api_key"]
                            stream_sid = data["start"]["streamSid"]
                            start_time = time.time()
                            logger.info(f"Incoming stream has started {stream_sid}")
                        elif data["event"] == "dtmf":
                            digit = data["dtmf"]["digit"]
                            logger.info(f"DTMF received: {digit}")
                            if digit == "0":
                                redis_client.set(session_id, "transfer")
                                logger.info("DTMF '0' detected, redirecting call...")
                                termination_event.set()
                                await websocket.close()
                                break
                    except WebSocketDisconnect:
                        logger.info(
                            f"Twilio WebSocket disconnected. Session ID: {session_id}"
                        )
                        await asyncio.sleep(5)
                        await generate_conversation_summary(session_id)
                        # await get_conversation_summary(session_id)
                        summary = await get_conversation_summary(session_id)
                        print(
                            f"Conversation Summary for Session {session_id}: {summary}"
                        )
                        print(
                            f"Conversation History for Session {session_id}: {conversation_histories[session_id]}"
                        )
                        break
                    except RuntimeError as e:
                        if "WebSocket is not connected" in str(e):
                            logger.info(
                                f"WebSocket connection lost. Session ID: {session_id}"
                            )
                            break
                        logger.error(f"Runtime error in receive_from_twilio: {e}")
                        break
                    except Exception as e:
                        logger.error(f"Error in receive_from_twilio: {e}")
                        break

            async def send_to_twilio():
                nonlocal stream_sid, start_time
                try:
                    async for openai_message in openai_ws:
                        try:
                            response = json.loads(openai_message)
                            start_time = time.time()
                            if response["type"] in LOG_EVENT_TYPES:
                                logger.info(
                                    f"Received event: {response['type']}::{response}"
                                )
                            if response["type"] == "session.updated":
                                logger.info(f"Session updated successfully: {response}")
                            if response["type"] == "input_audio_buffer.speech_started":
                                logger.info(f"Input Audio Detected::{response}")
                                await clear_buffer(websocket, openai_ws, stream_sid)

                            # Handle new user messages
                            if response.get("type") == "conversation.item.create":
                                item = response.get("item", {})
                                if item.get("type") == "message" and item.get("role") == "user":
                                    user_text_parts = [c["text"] for c in item["content"] if c["type"] == "text"]
                                    user_text = " ".join(user_text_parts)
                                    conversation_histories[session_id].append({"role": "user", "content": user_text})

                            if response[
                                "type"
                            ] == "response.audio.delta" and response.get("delta"):
                                try:
                                    audio_payload = base64.b64encode(
                                        base64.b64decode(response["delta"])
                                    ).decode("utf-8")
                                    audio_delta = {
                                        "event": "media",
                                        "streamSid": stream_sid,
                                        "media": {"payload": audio_payload},
                                    }
                                    await websocket.send_json(audio_delta)
                                    start_time = time.time()
                                except asyncio.TimeoutError:
                                    logger.error(
                                        "Timeout while sending audio data to Twilio"
                                    )
                                except Exception as e:
                                    logger.error(f"Error processing audio data: {e}")
                            if (
                                response["type"]
                                == "response.function_call_arguments.done"
                            ):
                                try:
                                    function_name = response["name"]
                                    call_id = response["call_id"]
                                    arguments = json.loads(response["arguments"])
                                    if function_name == "get_additional_context":
                                        await play_typing(websocket, stream_sid)
                                        logger.info("CustomGPT Started")
                                        start_time = time.time()
                                        # Store the user's query
                                        conversation_histories[session_id].append(
                                            {
                                                "role": "user",
                                                "content": arguments["query"],
                                            }
                                        )
                                        result = get_additional_context(
                                            arguments["query"], api_key, session_id
                                        )
                                        logger.info(
                                            f"Clear Audio::Additional Context gained"
                                        )
                                        await clear_buffer(
                                            websocket, openai_ws, stream_sid
                                        )
                                        end_time = time.time()
                                        elapsed_time = end_time - start_time
                                        logger.info(
                                            f"get_additional_context execution time: {elapsed_time:.4f} seconds"
                                        )
                                        function_response = {
                                            "type": "conversation.item.create",
                                            "item": {
                                                "type": "function_call_output",
                                                "call_id": call_id,
                                                "output": result,
                                            },
                                        }
                                        await openai_ws.send(
                                            json.dumps(function_response)
                                        )
                                        await openai_ws.send(
                                            json.dumps({"type": "response.create"})
                                        )
                                    elif function_name == "call_support":
                                        logger.info(
                                            "Detected Term for calling support..."
                                        )
                                        redis_client.set(session_id, "transfer")
                                        termination_event.set()
                                        raise Exception("Close Stream")

                                except json.JSONDecodeError as e:
                                    logger.error(
                                        f"Error in json decode in function_call: {e}::{response}"
                                    )
                                except Exception as e:
                                    logger.error(f"Error in function_call.done: {e}")
                                    raise Exception("Close Stream")

                        except json.JSONDecodeError as e:
                            logger.error(
                                f"Error in json decode of response: {e}::{openai_message}"
                            )

                except WebSocketDisconnect:
                    logger.info(
                        f"OpenAI WebSocket disconnected. Session ID: {session_id}"
                    )
                    await generate_conversation_summary(session_id)  # check
                except Exception as e:
                    logger.error(f"Error in send_to_twilio: {e}")
                    await generate_conversation_summary(session_id)  # check
                    raise Exception("Close Stream")

            await asyncio.gather(receive_from_twilio(), send_to_twilio())
        except websockets.exceptions.ConnectionClosed:
            logger.error(
                f"WebSocket connection closed unexpectedly. Session ID: {session_id}"
            )
        except Exception as e:
            logger.error(f"Unexpected error in handle_media_stream: {e}")

        finally:
            try:
                await clear_buffer(websocket, openai_ws, stream_sid)
                await openai_ws.close()
                await websocket.close()
            except Exception:
                logger.info(f"WebSocket connection closed. Session ID: {session_id}")


def start_recording(call_id: str, session_id: str, host: str):
    # Delay the recording by 3 seconds
    time.sleep(2)
    # Start the recording
    try:
        recording = twilio_client.calls(call_id).recordings.create(
            recording_status_callback=f"https://{host}/log-recording/{session_id}",
            recording_status_callback_event=["in-progress", "completed"],
            recording_channels="dual",
        )
        logger.info(
            f"Recording started for Call SID: {call_id} with Recording SID: {recording.sid}"
        )
    except Exception as e:
        logger.error(f"Failed to start recording for Call SID: {call_id}. Error: {e}")


### VECTOR BASED RAG
def get_additional_context(query, api_key, session_id):
    # Initialize conversation history for new sessions
    if session_id not in conversation_histories:
        conversation_histories[session_id] = []

    custom_persona = """
    You are an AI assistant tasked with answering user queries based on a knowledge base. The user query is transcribed from voice audio, so there may be transcription errors.

    When responding to the user query, follow these guidelines:
    1. Match the query to the knowledge base using both phonetic and semantic similarity.
    2. Attempt to answer even if the match isn't perfect, as long as it seems reasonably close.

    Provide a concise answer, limited to three sentences.
    """

    # Set API key
    client_openai.api_key = api_key

    # Retry logic
    tries = 0
    max_retries = 2
    while tries <= max_retries:
        try:
            logger.info(f"OpenAI API query sent:: {query}")
            # Retrieve contexts from the Qdrant vector database
            retrieved_contexts = query_qdrant(query)
            context_text = "\n".join(retrieved_contexts)
            logger.info(f"Qdrant context retrieved: {context_text}")

            # Construct the conversation messages
            messages = [
                {"role": "system", "content": custom_persona},
                {"role": "system", "content": f"Retrieved Context: {context_text}"},
                {"role": "user", "content": query},
            ]

            # Add conversation history
            messages.extend(conversation_histories[session_id])

            # Add current query
            messages.append({"role": "user", "content": query})

            response = client_openai.chat.completions.create(
                model="gpt-4o-mini", messages=messages
            )

            logger.info(f"OpenAI response: {response}")
            assistant_response = response.choices[0].message.content.strip()

            # Upload KB fetching summaries to history
            conversation_histories[session_id].append(
                {"role": "assistant", "content": assistant_response}
            )

            return assistant_response
            # TODO: Ensure that this assistantresponse is the same as the one from CustomGPT
        except Exception as e:
            logger.error(f"Get Additional Context failed::Try {tries}::Error: {str(e)}")
            time.sleep(2)  # Wait before retrying
        tries += 1

    return "Sorry, I didn't get your query."


# def create_session(api_key, project_id, caller_number):
def create_session(api_key, caller_number):

    client_openai.api_key = api_key

    # Generate a unique session ID
    session_id = str(uuid.uuid4())
    logger.info(f"Session Created for caller {caller_number}: {session_id}")

    # Initialize conversation history for this session
    conversation_histories[session_id] = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]

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
                    "description": "Elaborate on the user's original query, providing additional context, specificity, and clarity to create a more detailed, expert-level question. The function should transform a simple query into a richer and more informative version that is suitable for an expert to answer.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The elaborated user query. This should fully describe the user's original question, adding depth, context, and clarity. Tailor the expanded query as if the user were asking an expert in the relevant field, providing necessary background or related subtopics that may help inform the response. Start with 'Please use your knowledge base'",
                            }
                        },
                        "required": ["query"],
                    },
                },
                {
                    "type": "function",
                    "name": "call_support",
                    "description": "The purpose of the call_support function is to help user when the agent is unable to answer query multiple times and they request transfer to a live agent or support but do not provide enough detail for effective assistance.",
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


##############################################################
##############################################################
################### VOICE RAG COMPONENT ######################
##############################################################
##############################################################


def get_embedding(text, model="text-embedding-3-small"):
    text = text.replace("\n", " ")
    return client_openai.embeddings.create(input=[text], model=model).data[0].embedding


def query_qdrant(query_text):
    query_embedding = get_embedding(query_text)
    search_result = vectordb_client.search(
        collection_name="respiratory_disease_guide",
        query_vector=query_embedding,
        limit=5,
    )
    return [hit.payload["text"] for hit in search_result]


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

    # Generate the response using ChatCompletion endpoint
    response = client_openai.chat.completions.create(
        model="gpt-4o-mini", messages=messages, max_tokens=200, temperature=0.7
    )

    return response.choices[0].message.content.strip()


async def generate_conversation_summary(session_id):
    """Generate a summary of the conversation for a given session."""
    if (
        session_id not in conversation_histories
        or not conversation_histories[session_id]
    ):
        return None

    try:
        # Format the conversation for summarization
        formatted_convo = "\n".join(
            [
                f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                for msg in conversation_histories[session_id]
                if msg["role"] in ["user", "assistant"]
            ]
        )

        # Use OpenAI to generate a summary
        summary_prompt = f"""
                            Please provide a concise summary of this conversation, highlighting:
                            1. Main topics discussed
                            2. Key questions asked
                            3. Important information provided

                            Conversation:
                            {formatted_convo}
                        """

        summary_response = client_openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant tasked with summarizing conversations.",
                },
                {"role": "user", "content": summary_prompt},
            ],
        )

        summary = summary_response.choices[0].message.content.strip()

        # Store the summary (you can modify this to store in a database)
        conversation_summaries[session_id] = {
            "summary": summary,
            "timestamp": datetime.now().isoformat(),
            "caller_number": session_caller_numbers.get(session_id, "Unknown"),
            "full_conversation": conversation_histories[session_id],
        }

        return summary
    except Exception as e:
        logger.error(f"Error generating conversation summary: {e}")
        return None


@app.get("/conversation-summary/{session_id}")
async def get_conversation_summary(session_id: str):
    """API endpoint to retrieve conversation summary."""
    if session_id in conversation_summaries:
        return conversation_summaries[session_id]
    return {"error": "Session not found"}


##############################################################
##############################################################
############# SENDING CONVERSATION TO FRONTEND ###############
##############################################################
##############################################################


@app.get("/api/get-session-id")
async def generate_session():
    try:
        return JSONResponse(content={"sessionId": CURR_SESSION_ID})
    except:
        session_id = str(uuid.uuid4())
        return JSONResponse(content={"sessionId": session_id})


@app.websocket("/stream/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    active_connections[session_id] = websocket

    try:
        while True:
            data = await websocket.receive_text()
            # Handle any incoming messages from frontend
    except Exception as e:
        print(f"Error: {e}")
    finally:
        del active_connections[session_id]


# In your existing handle_media_stream function, add:
async def send_to_frontend(session_id: str, message: str):
    if session_id in active_connections:
        await active_connections[session_id].send_text(message)


"""
# Use it in your OpenAI handler:
if stream_sid in active_connections:
    await send_to_frontend(session_id, openai_response)
"""


@app.get("/test")
async def test_endpoint():
    return JSONResponse(content={"message": "Hello from the backend!"})
