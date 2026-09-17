# GPT Realtime + DialBB prototype

This directory contains an intentionally small voice-chat path for trying GPT Realtime with an existing DialBB application. It does not change the Google STT/TTS multimodal server.

The prototype architecture is:

```text
mm_frontend --WebSocket--> realtime_prototype.server
							  ├─ WebSocket --> GPT Realtime API
							  └─ Function Call --> DialogueProcessor
```

This is a new server and does not use `dialbb.multimodal.server`. The existing Google STT/TTS path remains unchanged.

## Start the Gateway

Set `OPENAI_API_KEY`, then run:

```powershell
uv run --python 3.11 python -m dialbb.realtime_prototype.server path\to\config.yml --port 5010
```

The server keeps a `DialogueProcessor` per WebSocket session and exposes the DialBB turn as the `dialbb_turn` Realtime function. The browser sends 24 kHz mono PCM16 audio to the server, and the server forwards Realtime PCM16 audio deltas back to the browser.

## Start the frontend

```powershell
cd mm_frontend
npm install
npm run dev
```

After building the frontend, the Gateway can serve it directly:

```text
http://localhost:5010/?realtime=1
```

The `realtime=1` query is still required to select the Realtime prototype mode. The Vite development server can still be used separately during frontend development.

For a missing frontend build, run `npm run build` in `mm_frontend` before starting the Gateway.

## Scope

- Realtime server-side WebSocket connection
- Realtime VAD and audio input/output
- `dialbb_turn` Function Calling
- DialBB initial request and per-session turn state

Deliberately omitted for this prototype: audio logging, playback acknowledgements, explicit barge-in truncation, authentication, and production reconnect handling.
