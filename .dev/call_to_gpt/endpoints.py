import os
import json
import urllib.parse
from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
from twilio.twiml.voice_response import VoiceResponse, Connect, Redirect, Dial, Stream
import logging
import redis
from dotenv import load_dotenv

# Local imports
from services import (
    start_recording,
    handle_media_stream_service,
    create_session,
    get_additional_context,
)

load_dotenv()

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis configuration
redis_url = urllib.parse.urlparse(os.environ.get("REDIS_URL"))
redis_client = redis.Redis(
    host=redis_url.hostname,
    port=redis_url.port,
    password=redis_url.password,
    ssl=True,
    ssl_cert_reqs=None,
)

# Initialize FastAPI app
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Environment variables
PORT = int(os.getenv("PORT", 5050))
DEFAULT_INTRO = "Hello! How can i assist you today"
CUSTOMGPT_API_KEY = os.getenv("CUSTOMGPT_API_KEY")
PERSONAL_PHONE_NUMBER = os.getenv("PERSONAL_PHONE_NUMBER")


@app.get("/", response_class=HTMLResponse)
async def index_page():
    return "<h1>Twilio Media Stream Server is running!</h1>"


@app.api_route("/incoming-call", methods=["GET", "POST"])
async def handle_incoming_call(
    request: Request,
    background_tasks: BackgroundTasks,
    project_id: int,
    api_key: Optional[str] = CUSTOMGPT_API_KEY,
    phone_number: Optional[str] = None,
    introduction: Optional[str] = DEFAULT_INTRO,
):
    form_data = (
        await request.form() if request.method == "POST" else request.query_params
    )
    caller_number = form_data.get("From", "Unknown")
    session_id = create_session(api_key, project_id, caller_number)

    host = request.url.hostname
    call_id = form_data.get("CallSid")
    response = VoiceResponse()
    response.pause(length=1)
    connect = Connect()

    encoded_phone_number = urllib.parse.quote_plus(phone_number)
    encoded_introduction = urllib.parse.quote_plus(introduction)
    stream = Stream(
        url=f"wss://{host}/media-stream/project/{project_id}/session/{session_id}/{encoded_phone_number}/{encoded_introduction}"
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


@app.websocket(
    "/media-stream/project/{project_id}/session/{session_id}/{phone_number}/{introduction}"
)
async def handle_media_stream(
    websocket: WebSocket,
    project_id: int,
    session_id: str,
    phone_number: str,
    introduction: str,
):
    await handle_media_stream_service(
        websocket, project_id, session_id, phone_number, introduction
    )


# Optional: Add a main block for running the server if needed
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
