import asyncio
import base64
import json
import os
from contextlib import asynccontextmanager
from typing import Optional

import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream

from database import init_db, save_transcription, get_transcriptions

# ─────────────────────────────────────────────
# Load environment variables from .env
# ─────────────────────────────────────────────
load_dotenv()

TWILIO_ACCOUNT_SID  = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN   = os.getenv("TWILIO_AUTH_TOKEN")
FRIEND_PHONE_NUMBER = os.getenv("FRIEND_PHONE_NUMBER")
DEEPGRAM_API_KEY    = os.getenv("DEEPGRAM_API_KEY")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# ─────────────────────────────────────────────
# State: track the current active call's SID
# ─────────────────────────────────────────────
active_call_sid: Optional[str] = None

# ─────────────────────────────────────────────
# App startup: initialize the database
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")


# ─────────────────────────────────────────────
# Route 1: Serve the website
# ─────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    transcriptions = get_transcriptions()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "transcriptions": transcriptions}
    )


# ─────────────────────────────────────────────
# Route 2: Twilio Webhook
# Twilio POSTs here when your number receives a call.
# ─────────────────────────────────────────────
@app.post("/incoming-call")
async def incoming_call(request: Request):
    global active_call_sid

    # Grab the unique ID for this call from Twilio's POST body
    form_data = await request.form()
    active_call_sid = form_data.get("CallSid")
    print(f"📞 Incoming call! CallSid: {active_call_sid}")

    # Build TwiML response
    # The <Connect><Stream> tells Twilio:
    #   "Open a WebSocket to this URL and start streaming audio there"
    # The host header will be your ngrok domain (e.g., abc123.ngrok.io)
    host = request.headers.get("host")
    response = VoiceResponse()
    connect = Connect()
    connect.stream(url=f"wss://{host}/media-stream")
    response.append(connect)

    print(f"📋 Returning TwiML, streaming to wss://{host}/media-stream")
    return Response(content=str(response), media_type="application/xml")


# ─────────────────────────────────────────────
# Route 3: WebSocket — receive Twilio audio stream
#
# Twilio connects here after reading the TwiML above.
# It sends JSON messages containing base64-encoded audio.
# We forward the raw audio bytes to Deepgram.
# ─────────────────────────────────────────────
@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    await websocket.accept()
    print("🎙️ Twilio audio stream connected!")

    # Deepgram WebSocket URL — we specify the audio format here.
    # mulaw = telephone audio encoding  |  8000 = 8kHz sample rate
    # nova-2 = Deepgram's best general model
    # smart_format = adds punctuation automatically
    # interim_results=false = only return final (complete) transcripts
    deepgram_url = (
        "wss://api.deepgram.com/v1/listen"
        "?encoding=mulaw"
        "&sample_rate=8000"
        "&channels=1"
        "&model=nova-2"
        "&smart_format=true"
        "&interim_results=false"
    )

    try:
        # Open a WebSocket connection TO Deepgram
        async with websockets.connect(
            deepgram_url,
            additional_headers={"Authorization": f"Token {DEEPGRAM_API_KEY}"}
        ) as deepgram_ws:
            print("🔗 Connected to Deepgram!")

            # ── Coroutine A: Twilio → Deepgram ──
            # Read audio chunks from Twilio, decode base64, send raw bytes to Deepgram
            async def forward_audio_to_deepgram():
                try:
                    async for raw_message in websocket.iter_text():
                        msg = json.loads(raw_message)
                        event = msg.get("event")

                        if event == "connected":
                            print("   Twilio stream connected event received.")

                        elif event == "start":
                            print(f"   Stream started: {msg.get('start', {})}")

                        elif event == "media":
                            # Decode base64 audio and send raw mulaw bytes to Deepgram
                            audio_bytes = base64.b64decode(msg["media"]["payload"])
                            await deepgram_ws.send(audio_bytes)

                        elif event == "stop":
                            print("   Twilio stream stopped.")
                            # Tell Deepgram we're done sending audio
                            await deepgram_ws.send(json.dumps({"type": "CloseStream"}))
                            break

                except WebSocketDisconnect:
                    print("   Twilio WebSocket disconnected.")
                except Exception as e:
                    print(f"   Error in forward_audio_to_deepgram: {e}")

            # ── Coroutine B: Deepgram → Database ──
            # Read transcripts from Deepgram, save finals to SQLite
            async def receive_transcripts_from_deepgram():
                try:
                    async for raw_message in deepgram_ws:
                        result = json.loads(raw_message)

                        # Deepgram sends various message types; we want "Results"
                        if result.get("type") != "Results":
                            continue

                        # Extract the transcript text
                        alternatives = result.get("channel", {}).get("alternatives", [])
                        if not alternatives:
                            continue

                        transcript = alternatives[0].get("transcript", "").strip()
                        is_final   = result.get("is_final", False)

                        # Only save final (complete) transcripts, not partials
                        if transcript and is_final:
                            print(f"📝 Transcript: {transcript}")
                            save_transcription(transcript, call_sid=active_call_sid)

                except Exception as e:
                    print(f"   Error in receive_transcripts_from_deepgram: {e}")

            # Run both coroutines concurrently.
            # When either one finishes (call ends or error), cancel the other.
            task_a = asyncio.create_task(forward_audio_to_deepgram())
            task_b = asyncio.create_task(receive_transcripts_from_deepgram())

            done, pending = await asyncio.wait(
                [task_a, task_b],
                return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()

    except Exception as e:
        print(f"❌ WebSocket/Deepgram error: {e}")

    print("🔴 Media stream closed.")


# ─────────────────────────────────────────────
# Route 4: Transfer the active call
#
# Called when you click the Transfer button in the browser.
# Uses Twilio REST API to send new TwiML to the active call.
# ─────────────────────────────────────────────
@app.post("/transfer-call")
async def transfer_call():
    global active_call_sid

    if not active_call_sid:
        return {"error": "No active call to transfer."}

    print(f"🔀 Transferring call {active_call_sid} to {FRIEND_PHONE_NUMBER}")

    # Build TwiML that dials your friend
    response = VoiceResponse()
    response.dial(FRIEND_PHONE_NUMBER)

    # Push this new TwiML directly to the active call via Twilio REST API
    # This INTERRUPTS the current stream and dials the friend instead
    twilio_client.calls(active_call_sid).update(twiml=str(response))

    return {"status": "transferred", "to": FRIEND_PHONE_NUMBER}


# ─────────────────────────────────────────────
# Route 5: API endpoint for transcriptions (used by JS polling)
# ─────────────────────────────────────────────
@app.get("/transcriptions")
async def api_transcriptions():
    return get_transcriptions()