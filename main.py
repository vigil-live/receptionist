import asyncio
import base64
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Optional

import httpx
import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from twilio.rest import Client
from twilio.twiml.voice_response import Connect, Stream, VoiceResponse

from database import init_db, get_transcriptions, save_transcription

load_dotenv()

TWILIO_ACCOUNT_SID  = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN   = os.getenv("TWILIO_AUTH_TOKEN")
FRIEND_PHONE_NUMBER = os.getenv("FRIEND_PHONE_NUMBER")
DEEPGRAM_API_KEY    = os.getenv("DEEPGRAM_API_KEY")
GROQ_API_KEY        = os.getenv("GROQ_API_KEY")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

calls_store: Dict[str, dict] = {}
call_counter: int = 0


async def _nominatim(address: str, client: httpx.AsyncClient) -> tuple[Optional[float], Optional[float]]:
    try:
        resp = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": address, "format": "json", "limit": 1},
            headers={"User-Agent": "Vigil-Dispatch/1.0"},
        )
        results = resp.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception as exc:
        print(f"Nominatim error: {exc}")
    return None, None


async def _photon(address: str, client: httpx.AsyncClient) -> tuple[Optional[float], Optional[float]]:
    try:
        resp = await client.get(
            "https://photon.komoot.io/api/",
            params={"q": address, "limit": 1},
            headers={"User-Agent": "Vigil-Dispatch/1.0"},
        )
        features = resp.json().get("features", [])
        if features:
            coords = features[0]["geometry"]["coordinates"]
            return float(coords[1]), float(coords[0])
    except Exception as exc:
        print(f"Photon error: {exc}")
    return None, None


async def geocode_address(address: str) -> tuple[Optional[float], Optional[float]]:
    if not address or address == "Unspecified Location":
        return None, None

    async with httpx.AsyncClient(timeout=8.0) as client:
        lat, lng = await _nominatim(address, client)
        if lat is not None:
            print(f"Nominatim -> '{address}' -> ({lat}, {lng})")
            return lat, lng

        lat, lng = await _photon(address, client)
        if lat is not None:
            print(f"Photon -> '{address}' -> ({lat}, {lng})")
            return lat, lng

    print(f"Both geocoders failed for '{address}'")
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
    "address": "the most specific location mentioned — full street address, business name + city, or landmark + city. Use 'Unspecified Location' only if truly no location is mentioned.",
    "lat": null,
    "lng": null
  }},
  "summary": "2-3 sentence summary of the situation",
  "recommended_dispatch": ["police", "fire", "ambulance"]
}}

Severity: critical = life-threatening / in-progress violence, high = urgent injury risk,
medium = property damage / non-critical injury, low = minor / informational.
Always set lat and lng to null — they will be filled in separately."""

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

            old_groq = call.get("groq_data") or {}
            old_loc  = old_groq.get("location") or {}
            old_addr = old_loc.get("address", "")
            old_lat  = old_loc.get("lat")
            old_lng  = old_loc.get("lng")

            new_address = parsed.get("location", {}).get("address", "")

            if new_address == old_addr and old_lat is not None:
                print(f"Address unchanged ('{new_address}') — keeping existing pin")
                parsed["location"]["lat"] = old_lat
                parsed["location"]["lng"] = old_lng
            else:
                lat, lng = await geocode_address(new_address)

                if lat is not None:
                    parsed["location"]["lat"] = lat
                    parsed["location"]["lng"] = lng
                elif old_lat is not None:
                    print(f"'{new_address}' failed geocoding — keeping previous pin @ '{old_addr}'")
                    parsed["location"]["lat"] = old_lat
                    parsed["location"]["lng"] = old_lng
                else:
                    parsed["location"]["lat"] = None
                    parsed["location"]["lng"] = None

            calls_store[call_sid]["groq_data"] = parsed
            print(f"Groq -> {call_sid}: {parsed.get('incident')} [{parsed.get('severity')}] @ {parsed.get('location')}")

    except Exception as exc:
        print(f"Groq analysis failed for {call_sid}: {exc}")


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
    form_data   = await request.form()
    call_sid    = form_data.get("CallSid")
    from_number = form_data.get("From", "Unknown")

    global call_counter
    call_counter += 1

    print(f"Incoming call! CallSid={call_sid}  From={from_number}")

    calls_store[call_sid] = {
        "call_sid":    call_sid,
        "call_number": call_counter,
        "from_number": from_number,
        "status":      "active",
        "started_at":  datetime.utcnow().isoformat(),
        "transcripts": [],
        "groq_data":   None,
        "dispatched":  [],
    }

    host = request.headers.get("host")
    response = VoiceResponse()
    connect  = Connect()
    stream   = Stream(url=f"wss://{host}/media-stream")
    stream.parameter(name="callSid", value=call_sid)
    connect.append(stream)
    response.append(connect)

    print(f"TwiML returned — streaming to wss://{host}/media-stream")
    return Response(content=str(response), media_type="application/xml")


@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    await websocket.accept()
    print("Twilio audio stream connected")

    call_sid: Optional[str] = None

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
        async with websockets.connect(
            deepgram_url,
            additional_headers={"Authorization": f"Token {DEEPGRAM_API_KEY}"},
        ) as deepgram_ws:

            async def forward_audio_to_deepgram():
                nonlocal call_sid
                try:
                    async for raw_message in websocket.iter_text():
                        msg   = json.loads(raw_message)
                        event = msg.get("event")

                        if event == "start":
                            start_data    = msg.get("start", {})
                            custom_params = start_data.get("customParameters", {})
                            call_sid      = custom_params.get("callSid") or start_data.get("callSid")

                        elif event == "media":
                            audio_bytes = base64.b64decode(msg["media"]["payload"])
                            await deepgram_ws.send(audio_bytes)

                        elif event == "stop":
                            if call_sid and call_sid in calls_store:
                                calls_store[call_sid]["status"]   = "resolved"
                                calls_store[call_sid]["ended_at"] = datetime.utcnow().isoformat()
                            await deepgram_ws.send(json.dumps({"type": "CloseStream"}))
                            break

                except WebSocketDisconnect:
                    pass

            async def receive_transcripts_from_deepgram():
                pending_groq_task: Optional[asyncio.Task] = None
                try:
                    async for raw_message in deepgram_ws:
                        result = json.loads(raw_message)

                        if result.get("type") != "Results":
                            continue

                        alternatives = result.get("channel", {}).get("alternatives", [])
                        if not alternatives:
                            continue

                        transcript = alternatives[0].get("transcript", "").strip()
                        is_final   = result.get("is_final", False)

                        if transcript and is_final:
                            save_transcription(transcript, call_sid=call_sid)

                            if call_sid and call_sid in calls_store:
                                calls_store[call_sid]["transcripts"].append(transcript)

                                if pending_groq_task and not pending_groq_task.done():
                                    pending_groq_task.cancel()
                                pending_groq_task = asyncio.create_task(
                                    analyze_with_groq(call_sid)
                                )

                except Exception:
                    pass

            task_a = asyncio.create_task(forward_audio_to_deepgram())
            task_b = asyncio.create_task(receive_transcripts_from_deepgram())

            done, pending = await asyncio.wait(
                [task_a, task_b],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()

    except Exception:
        pass


@app.post("/transfer-call")
async def transfer_call(request: Request):
    body     = await request.json()
    call_sid = body.get("call_sid")

    if not call_sid or call_sid not in calls_store:
        return {"error": "Call not found."}

    response = VoiceResponse()
    response.dial(FRIEND_PHONE_NUMBER)

    twilio_client.calls(call_sid).update(twiml=str(response))
    calls_store[call_sid]["status"]   = "transferred"
    calls_store[call_sid]["ended_at"] = datetime.utcnow().isoformat()

    return {"status": "transferred", "to": FRIEND_PHONE_NUMBER}


@app.post("/dispatch")
async def dispatch_unit(request: Request):
    body      = await request.json()
    call_sid  = body.get("call_sid")
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

        transcript_entries = [
            {"role": "caller", "text": chunk, "time": ""}
            for chunk in call["transcripts"]
        ]

        try:
            started  = datetime.fromisoformat(call["started_at"])
            ended_at = call.get("ended_at")
            end_time = datetime.fromisoformat(ended_at) if ended_at else datetime.utcnow()
            duration = int((end_time - started).total_seconds())
        except Exception:
            duration = 0

        raw_location = groq.get("location", {})
        location = {
            "address": raw_location.get("address") or "Unspecified Location",
            "lat":     raw_location.get("lat"),
            "lng":     raw_location.get("lng"),
        }

        result.append({
            "id":                   call_sid,
            "call_sid":             call_sid,
            "call_number":          call.get("call_number", 0),
            "phone":                call["from_number"],
            "name":                 groq.get("name"),
            "incident":             groq.get("incident", "Incoming call"),
            "severity":             groq.get("severity", "medium"),
            "status":               call["status"],
            "location":             location,
            "callDuration":         duration,
            "dispatched":           call.get("dispatched", []),
            "transcript":           transcript_entries,
            "summary":              groq.get("summary", ""),
            "recommended_dispatch": groq.get("recommended_dispatch", []),
        })

    return result


@app.get("/transcriptions")
async def api_transcriptions():
    return get_transcriptions()