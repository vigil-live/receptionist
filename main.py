import asyncio
import base64
import json
import os
import audioop
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Optional, List

import httpx
import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from twilio.rest import Client
from twilio.twiml.voice_response import Connect, Stream, VoiceResponse

from database import init_db, get_transcriptions, get_transcriptions_by_call, save_transcription

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
FRIEND_PHONE_NUMBER = os.getenv("FRIEND_PHONE_NUMBER")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

calls_store: Dict[str, dict] = {}
call_counter: int = 0

conversation_histories: Dict[str, List[dict]] = {}

SYSTEM_PROMPT = """You are an emergency 911 AI dispatcher assistant. Human operators are temporarily unavailable, so you are handling the call.

Rules you MUST follow:
- Every reply is ONE short sentence only — never more.
- Speak calmly and clearly. Be warm but efficient.
- Ask only ONE question at a time to gather: location, nature of emergency, caller safety.
- Acknowledge the caller's emotion briefly before asking for info (e.g. "I understand, stay calm." or "You're doing great, help is coming.").
- Never say you're an AI unless directly asked.
- Never provide medical/legal advice beyond basic safety instructions.
- If situation is life-threatening, reassure them help is dispatched and ask them to stay on the line.
- Do not repeat yourself."""


async def geocode_address(address: str) -> tuple[Optional[float], Optional[float]]:
    if not address or address == "Unspecified Location":
        return None, None

    async with httpx.AsyncClient(timeout=8.0) as client:
        try:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": address, "format": "json", "limit": 1, "addressdetails": 1},
                headers={"User-Agent": "Vigil-Dispatch/1.0"},
            )
            results = resp.json()
            if results:
                lat = float(results[0]["lat"])
                lng = float(results[0]["lon"])
                print(f"[Nominatim] '{address}' -> ({lat}, {lng})")
                return lat, lng
        except Exception as exc:
            print(f"Nominatim failed for '{address}': {exc}")

        try:
            resp = await client.get(
                "https://photon.komoot.io/api/",
                params={"q": address, "limit": 1},
                headers={"User-Agent": "Vigil-Dispatch/1.0"},
            )
            features = resp.json().get("features", [])
            if features:
                coords = features[0]["geometry"]["coordinates"]
                lng, lat = float(coords[0]), float(coords[1])
                print(f"[Photon] '{address}' -> ({lat}, {lng})")
                return lat, lng
        except Exception as exc:
            print(f"Photon also failed for '{address}': {exc}")

    return None, None


async def analyze_with_groq(call_sid: str) -> None:
    call = calls_store.get(call_sid)
    if not call or not call["transcripts"]:
        return

    transcript_text = " ".join(call["transcripts"])

    prompt = f"""You are an emergency dispatch AI. Analyze this 911 call transcript and extract structured information.

Transcript: {transcript_text}

Caller phone: {call.get("from_number", "Unknown")}

Return ONLY valid JSON (no markdown fences, no extra text) with this exact structure:
{{
  "incident": "short incident title, e.g. House Fire, Car Accident, Medical Emergency",
  "severity": "critical|high|medium|low",
  "name": "caller full name or null if unknown",
  "location": {{
    "address": "full address or landmark name if stated in transcript, or Unspecified Location if not mentioned",
    "lat": null,
    "lng": null
  }},
  "summary": "2-3 sentence summary of the situation",
  "recommended_dispatch": ["police", "fire", "ambulance"]
}}

Severity: critical = life-threatening / in-progress violence, high = urgent injury risk,
medium = property damage / non-critical injury, low = minor / informational.
Always set lat and lng to null."""

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                },
            )
            data = resp.json()
            raw = data["choices"][0]["message"]["content"].strip()

            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            parsed = json.loads(raw)

            address = parsed.get("location", {}).get("address", "")
            lat, lng = await geocode_address(address)

            if lat is not None and lng is not None:
                parsed["location"]["lat"] = lat
                parsed["location"]["lng"] = lng
            else:
                prev = (calls_store[call_sid].get("groq_data") or {}).get("location", {})
                parsed["location"]["lat"] = prev.get("lat")
                parsed["location"]["lng"] = prev.get("lng")

            calls_store[call_sid]["groq_data"] = parsed
            print(
                f"Groq -> {call_sid}: {parsed.get('incident')} "
                f"[{parsed.get('severity')}] @ {parsed.get('location')}"
            )

    except Exception as exc:
        print(f"Groq analysis failed for {call_sid}: {exc}")


async def get_ai_response(call_sid: str, caller_message: str) -> str:
    history = conversation_histories.setdefault(call_sid, [])
    history.append({"role": "user", "content": caller_message})
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history[-12:]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": messages,
                    "temperature": 0.4,
                    "max_tokens": 80,
                },
            )
            data = resp.json()
            ai_text = data["choices"][0]["message"]["content"].strip()

            for punct in [". ", "! ", "? "]:
                idx = ai_text.find(punct)
                if idx != -1:
                    ai_text = ai_text[: idx + 1]
                    break

            history.append({"role": "assistant", "content": ai_text})
            print(f"[AI -> {call_sid}] {ai_text}")
            return ai_text

    except Exception as exc:
        print(f"Groq conversation failed for {call_sid}: {exc}")
        return "I'm here with you — can you tell me your location?"


async def text_to_speech_mulaw(text: str) -> Optional[bytes]:
    url = "https://api.deepgram.com/v1/speak"
    params = {
        "model": "aura-asteria-en",
        "encoding": "linear16",
        "sample_rate": "8000",
        "container": "none",
    }
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"text": text}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, params=params, headers=headers, json=payload)
            if resp.status_code != 200:
                print(f"[TTS] Deepgram error {resp.status_code}: {resp.text[:200]}")
                return None

            pcm_bytes = resp.content
            mulaw_bytes = audioop.lin2ulaw(pcm_bytes, 2)
            return mulaw_bytes

    except Exception as exc:
        print(f"[TTS] Error: {exc}")
        return None


def chunk_mulaw(mulaw_bytes: bytes, chunk_size: int = 160) -> List[bytes]:
    return [mulaw_bytes[i: i + chunk_size] for i in range(0, len(mulaw_bytes), chunk_size)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    transcriptions = get_transcriptions()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "transcriptions": transcriptions},
    )


@app.post("/incoming-call")
async def incoming_call(request: Request):
    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    from_number = form_data.get("From", "Unknown")

    global call_counter
    call_counter += 1

    print(f"Incoming call! CallSid={call_sid} From={from_number}")

    calls_store[call_sid] = {
        "call_sid": call_sid,
        "call_number": call_counter,
        "from_number": from_number,
        "status": "active",
        "started_at": datetime.utcnow().isoformat(),
        "transcripts": [],
        "groq_data": None,
        "dispatched": [],
    }

    conversation_histories[call_sid] = []

    host = request.headers.get("host")
    response = VoiceResponse()
    connect = Connect()
    stream = Stream(url=f"wss://{host}/media-stream")
    stream.parameter(name="callSid", value=call_sid)
    connect.append(stream)
    response.append(connect)

    print(f"TwiML returned streaming to wss://{host}/media-stream")
    return Response(content=str(response), media_type="application/xml")


app.routes[:] = [r for r in app.routes if getattr(r, "path", None) != "/media-stream"]


@app.websocket("/media-stream")
async def media_stream_final(websocket: WebSocket):
    await websocket.accept()
    print("[WS] Twilio media stream connected")

    call_sid: Optional[str] = None
    stream_sid: Optional[str] = None
    tts_queue: asyncio.Queue = asyncio.Queue()
    ai_speaking = asyncio.Event()

    deepgram_url = (
        "wss://api.deepgram.com/v1/listen"
        "?encoding=mulaw"
        "&sample_rate=8000"
        "&channels=1"
        "&model=nova-2"
        "&smart_format=true"
        "&interim_results=true"
        "&utterance_end_ms=1000"
        "&vad_events=true"
    )

    try:
        async with websockets.connect(
            deepgram_url,
            additional_headers={"Authorization": f"Token {DEEPGRAM_API_KEY}"},
        ) as deepgram_ws:
            print("[WS] Connected to Deepgram STT")

            async def task_twilio_inbound():
                nonlocal call_sid, stream_sid
                try:
                    async for raw in websocket.iter_text():
                        msg = json.loads(raw)
                        event = msg.get("event")

                        if event == "start":
                            start_data = msg.get("start", {})
                            cp = start_data.get("customParameters", {})
                            call_sid = cp.get("callSid") or start_data.get("callSid")
                            stream_sid = start_data.get("streamSid")
                            if call_sid and call_sid in calls_store:
                                calls_store[call_sid]["tts_queue"] = tts_queue
                            print(f"[WS] Stream start: call={call_sid} stream={stream_sid}")
                            asyncio.create_task(_greet())

                        elif event == "media":
                            if not ai_speaking.is_set():
                                audio = base64.b64decode(msg["media"]["payload"])
                                await deepgram_ws.send(audio)

                        elif event == "stop":
                            print(f"[WS] Stream stop: call={call_sid}")
                            if call_sid and call_sid in calls_store:
                                calls_store[call_sid]["status"] = "resolved"
                                calls_store[call_sid]["ended_at"] = datetime.utcnow().isoformat()
                            await deepgram_ws.send(json.dumps({"type": "CloseStream"}))
                            await tts_queue.put(None)
                            break

                except WebSocketDisconnect:
                    print("[WS] Twilio disconnected")
                except Exception as exc:
                    print(f"[WS] task_twilio_inbound error: {exc}")

            async def task_tts_sender():
                frame_interval = 0.018
                try:
                    while True:
                        item = await tts_queue.get()
                        if item is None:
                            ai_speaking.clear()
                            print("[TTS] AI finished speaking")
                            continue
                        msg = json.dumps({
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {"payload": item},
                        })
                        await websocket.send_text(msg)
                        await asyncio.sleep(frame_interval)
                except Exception as exc:
                    print(f"[TTS sender] Error: {exc}")

            async def task_deepgram_inbound():
                pending_analysis: Optional[asyncio.Task] = None
                current_utterance: List[str] = []

                try:
                    async for raw in deepgram_ws:
                        result = json.loads(raw)
                        msg_type = result.get("type")

                        if msg_type == "SpeechStarted":
                            print(f"[STT] Speech started (call={call_sid})")
                            continue

                        if msg_type == "UtteranceEnd":
                            if current_utterance and not ai_speaking.is_set():
                                full_text = " ".join(current_utterance).strip()
                                current_utterance.clear()
                                if full_text:
                                    asyncio.create_task(
                                        _handle_turn(full_text, pending_analysis)
                                    )
                            continue

                        if msg_type != "Results":
                            continue

                        alts = result.get("channel", {}).get("alternatives", [])
                        if not alts:
                            continue

                        transcript = alts[0].get("transcript", "").strip()
                        is_final = result.get("is_final", False)

                        if not transcript:
                            continue

                        if is_final:
                            current_utterance.append(transcript)
                            save_transcription(transcript, call_sid=call_sid, role="caller")
                            if call_sid and call_sid in calls_store:
                                calls_store[call_sid]["transcripts"].append(transcript)
                                if pending_analysis and not pending_analysis.done():
                                    pending_analysis.cancel()
                                pending_analysis = asyncio.create_task(
                                    analyze_with_groq(call_sid)
                                )

                except Exception as exc:
                    print(f"[STT] task_deepgram_inbound error: {exc}")

            async def _greet():
                await asyncio.sleep(1.0)
                greeting = "nine-one-one, what's your emergency?"
                await _speak(greeting)
                save_transcription(greeting, call_sid=call_sid, role="assistant")

            async def _handle_turn(caller_text: str, pending_analysis):
                print(f"[Turn] caller said: {caller_text}")
                ai_text = await get_ai_response(call_sid, caller_text)
                await _speak(ai_text)
                save_transcription(ai_text, call_sid=call_sid, role="assistant")

            async def _speak(text: str):
                nonlocal stream_sid
                if not stream_sid:
                    return

                mulaw = await text_to_speech_mulaw(text)
                if not mulaw:
                    return

                ai_speaking.set()

                frames = chunk_mulaw(mulaw, chunk_size=160)
                for frame in frames:
                    b64 = base64.b64encode(frame).decode()
                    await tts_queue.put(b64)

                await tts_queue.put(None)

            t1 = asyncio.create_task(task_twilio_inbound())
            t2 = asyncio.create_task(task_tts_sender())
            t3 = asyncio.create_task(task_deepgram_inbound())

            done, pending = await asyncio.wait(
                [t1, t2, t3],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for t in pending:
                t.cancel()

    except Exception as exc:
        print(f"[WS] Fatal error: {exc}")

    print(f"[WS] Session ended (call={call_sid})")


@app.post("/transfer-call")
async def transfer_call(request: Request):
    body = await request.json()
    call_sid = body.get("call_sid")

    if not call_sid or call_sid not in calls_store:
        return {"error": "Call not found."}

    response = VoiceResponse()
    response.dial(FRIEND_PHONE_NUMBER)

    twilio_client.calls(call_sid).update(twiml=str(response))
    calls_store[call_sid]["status"] = "transferred"
    calls_store[call_sid]["ended_at"] = datetime.utcnow().isoformat()

    return {"status": "transferred", "to": FRIEND_PHONE_NUMBER}


@app.post("/dispatch")
async def dispatch_unit(request: Request):
    body = await request.json()
    call_sid = body.get("call_sid")
    unit_type = body.get("type")

    if not call_sid or call_sid not in calls_store:
        return {"error": "Call not found."}

    dispatched = calls_store[call_sid].setdefault("dispatched", [])
    if unit_type not in dispatched:
        dispatched.append(unit_type)
    calls_store[call_sid]["status"] = "dispatched"

    return {"status": "dispatched", "type": unit_type, "call_sid": call_sid}


@app.get("/api/calls")
async def get_calls():
    result = []
    for call_sid, call in calls_store.items():
        groq = call.get("groq_data") or {}

        db_rows = get_transcriptions_by_call(call_sid)
        transcript_entries = [
            {"role": r["role"], "text": r["text"], "time": r["created_at"]}
            for r in db_rows
        ]

        try:
            started = datetime.fromisoformat(call["started_at"])
            ended_at = call.get("ended_at")
            end_time = datetime.fromisoformat(ended_at) if ended_at else datetime.utcnow()
            duration = int((end_time - started).total_seconds())
        except Exception:
            duration = 0

        raw_location = groq.get("location", {})
        location = {
            "address": raw_location.get("address") or "Unspecified Location",
            "lat": raw_location.get("lat"),
            "lng": raw_location.get("lng"),
        }

        result.append({
            "id": call_sid,
            "call_sid": call_sid,
            "call_number": call.get("call_number", 0),
            "phone": call["from_number"],
            "name": groq.get("name"),
            "incident": groq.get("incident", "Incoming call"),
            "severity": groq.get("severity", "medium"),
            "status": call["status"],
            "location": location,
            "callDuration": duration,
            "dispatched": call.get("dispatched", []),
            "transcript": transcript_entries,
            "summary": groq.get("summary", ""),
            "recommended_dispatch": groq.get("recommended_dispatch", []),
        })

    return result


@app.get("/transcriptions")
async def api_transcriptions():
    return get_transcriptions()