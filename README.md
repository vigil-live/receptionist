## Inspiration

In an emergency, every second matters. Yet over 30% of 911 calls spend 25+ seconds on hold. With a nationwide shortage of 911 operators only worsening, how can we let critical information slip through our emergency infrastructure? We built Vigil so that no emergency goes unheard.

## How we built it

Twilio provisions our live phone number and streams raw audio to our FastAPI backend over a WebSocket connection. The moment a call comes in, we return a TwiML response that pipes audio directly into our media stream endpoint:
```python
connect = Connect()
stream = Stream(url=f"wss://{host}/media-stream")
stream.parameter(name="callSid", value=call_sid)
connect.append(stream)
response.append(connect)
```
From there, we spin up three concurrent async tasks:
- one ingesting Twilio's media stream;
- one feeding audio frames to Deepgram's Nova-2 speech-to-text model in real time;
- and one sending synthesized audio back to the caller.

When Deepgram fires an `UtteranceEnd` event (i.e., when it notices the caller makes a natural pause), we pass the full transcript to Groq's LLaMA 3.3 70B.
That response gets converted to μ-law audio via Deepgram's Aura TTS, chunked into 160-byte frames, and streamed back through the same WebSocket:

```python
mulaw_bytes = audioop.lin2ulaw(pcm_bytes, 2)
frames = chunk_mulaw(mulaw_bytes, chunk_size=160)
for frame in frames:
    b64 = base64.b64encode(frame).decode()
    await tts_queue.put(b64)
```
In parallel, a lighter LLaMA 3.1 8B model continuously reanalyzes the growing transcript to extract structured incident data (severity, caller name, incident type, and location). That address gets geocoded against Nominatim and Photon and filtered to a Northern Virginia bounding box. The structured output drives our Next.js operator dashboard in real time.

## Challenges we ran into

Getting all these services to actually talk to each other was way harder than we expected. A huge chunk of our time was just figuring out how to pipe μ-law audio from Twilio into Deepgram and back out again without everything falling apart. The documentation wasn't always helpful, and a lot of it was outdated, but once we cracked the audio streaming pipeline, the rest of the project came together pretty fast.

## Accomplishments and what's next

We built a real, working demo in just 24 (slightly excruciating) hours! Messing around with myriad tools most of our team was unfamiliar with was daunting, but by the end of the event, we desgined the entire workflow from dialing the number to collecting vital information to easing the emergency receptionist experience. The demo truly displayed to us the viability of the design, and we're excited to see what's possible in the future!

```
See ya! Salban & Ritwik & Aarya & Aneesh
```
