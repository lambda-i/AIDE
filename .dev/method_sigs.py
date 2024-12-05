@app.websocket("/media-stream/session/{session_id}/{phone_number}/{introduction}")
async def handle_media_stream(
    websocket: WebSocket, session_id: str, phone_number: str, introduction: str
):
    await websocket.accept()
    termination_event = asyncio.Event()

    async with websockets.connect(
        "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01",
        extra_headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1",
        },
    ) as openai_ws:
        try:
            stream_sid = None 
            await send_session_update(openai_ws, phone_number, introduction)

            async def check_timeout():
                pass 
            
            asyncio.create_task(check_timeout())

            async def receive_from_twilio():
                pass
            
            async def send_to_twilio():
                pass
            
            await asyncio.gather(receive_from_twilio(), send_to_twilio())
        finally:
            try:
                await clear_buffer(websocket, openai_ws, stream_sid)
                await openai_ws.close()
                await websocket.close()

