"""Small server for experimenting with GPT Realtime and DialBB."""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import logging
import os
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import uvicorn
import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-realtime"
REALTIME_SAMPLE_RATE = 24000
logger = logging.getLogger(__name__)


@dataclass
class PrototypeSession:
    session_id: str
    websocket: WebSocket | None = None
    realtime: Any = None
    processor: Any = None
    dialbb_session_id: str | None = None
    dialbb_lock: threading.Lock = field(default_factory=threading.Lock)
    closed: bool = False


class RealtimeConnection:
    def __init__(self, session: PrototypeSession, config_file: str) -> None:
        self.session = session
        self.config_file = config_file
        self.transcript = ""
        self.audio_chunks_received = 0
        self.initial_text = ""
        self.response_done = asyncio.Event()
        self.response_active = False
        self.response_pending = False
        self.response_lock = asyncio.Lock()
        self.audio_response_buffer = bytearray()
        self.audio_response_delta_count = 0

    async def connect(self) -> None:
        from dialbb.main import DialogueProcessor

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

        headers = {
            "Authorization": f"Bearer {api_key}",
        }
        try:
            self.session.realtime = await websockets.connect(
                REALTIME_URL,
                additional_headers=headers,
                max_size=None,
            )
        except TypeError:
            self.session.realtime = await websockets.connect(
                REALTIME_URL,
                extra_headers=headers,
                max_size=None,
            )

        await self.send({
            "type": "session.update",
            "session": {
                "type": "realtime",
                "model": "gpt-realtime",
                "output_modalities": ["audio"],
                "instructions": (
                    "あなたはDialBB音声チャットの中継役です。"
                    "ユーザーの発話ごとに必ず dialbb_turn ツールを呼び出してください。"
                    "ツールの結果に含まれる system_text を自然な音声で、そのままユーザーへ伝えてください。"
                    "ツール結果を勝手に要約・変更しないでください。"
                ),
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcm", "rate": REALTIME_SAMPLE_RATE},
                        "transcription": {"model": "gpt-4o-mini-transcribe", "language": "ja"},
                        "turn_detection": {
                            "type": "server_vad",
                            "create_response": False,
                            "interrupt_response": False,
                        },
                    },
                    "output": {
                        "format": {"type": "audio/pcm", "rate": REALTIME_SAMPLE_RATE},
                        "voice": "marin",
                    },
                },
                "tools": [{
                    "type": "function",
                    "name": "dialbb_turn",
                    "description": "ユーザーの発話をDialBBへ渡し、DialBBの応答を取得します。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_text": {"type": "string", "description": "ユーザーの確定発話"},
                        },
                        "required": ["user_text"],
                    },
                }],
                "tool_choice": "auto",
            },
        })

        self.session.processor = DialogueProcessor(self.config_file)
        initial = await asyncio.to_thread(
            self.session.processor.process,
            {"user_id": f"realtime-{self.session.session_id}"},
            True,
        )
        self.session.dialbb_session_id = str(initial["session_id"])
        self.initial_text = str(initial.get("system_utterance") or "").strip()

    async def start_initial_response(self) -> None:
        if not self.initial_text:
            return
        self.response_done.clear()
        await self.say_exactly(self.initial_text)
        try:
            await asyncio.wait_for(self.response_done.wait(), timeout=60.0)
        except TimeoutError:
            logger.warning("Initial Realtime response timed out: session=%s", self.session.session_id)

    async def send(self, event: dict[str, Any]) -> None:
        if self.session.realtime is not None:
            await self.session.realtime.send(json.dumps(event, ensure_ascii=False))

    async def append_audio(self, audio_data: str) -> None:
        if audio_data:
            self.audio_chunks_received += 1
            if self.audio_chunks_received == 1:
                logger.info("Realtime audio input started: session=%s", self.session.session_id)
            await self.send({"type": "input_audio_buffer.append", "audio": audio_data})

    async def say_exactly(self, text: str) -> None:
        await self.request_response({
            "input": [],
            "output_modalities": ["audio"],
            "instructions": f"次のDialBB応答をそのまま読み上げてください:\n{text}",
        })

    async def request_response(self, response: dict[str, Any] | None = None) -> None:
        async with self.response_lock:
            if self.response_active:
                self.response_pending = True
                return
            self.response_active = True
            await self.send({"type": "response.create", "response": response or {"output_modalities": ["audio"]}})

    async def handle_function_call(self, event: dict[str, Any]) -> None:
        call_id = str(event.get("call_id") or "")
        try:
            arguments = json.loads(str(event.get("arguments") or "{}"))
            user_text = str(arguments.get("user_text") or "").strip()
            if not user_text:
                raise ValueError("user_text is required")
            if self.session.processor is None or not self.session.dialbb_session_id:
                raise RuntimeError("DialBB session is not initialized")

            with self.session.dialbb_lock:
                response = await asyncio.to_thread(
                    self.session.processor.process,
                    {
                        "session_id": self.session.dialbb_session_id,
                        "user_id": f"realtime-{self.session.session_id}",
                        "user_utterance": user_text,
                    },
                    False,
                )
            self.session.dialbb_session_id = str(response["session_id"])
            await self.send({
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps({
                        "system_text": response.get("system_utterance", ""),
                        "is_final": bool(response.get("final", False)),
                        "aux_data": response.get("aux_data", {}),
                    }, ensure_ascii=False),
                },
            })
            await self.request_response()
        except (ValueError, TypeError, KeyError, RuntimeError, OSError) as exc:
            await self.send({
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps({"error": str(exc)}, ensure_ascii=False),
                },
            })
            await self.request_response()

    async def receive_loop(self) -> None:
        if self.session.realtime is None:
            return
        try:
            async for raw in self.session.realtime:
                event = json.loads(raw)
                event_type = event.get("type")
                if event_type == "response.created":
                    self.response_active = True
                    self.audio_response_buffer.clear()
                    self.audio_response_delta_count = 0
                elif event_type == "input_audio_buffer.speech_stopped":
                    await self.request_response()
                elif event_type in {"response.cancelled", "response.canceled"}:
                    self.response_active = False
                    logger.warning("Realtime response cancelled: session=%s event=%s", self.session.session_id, event)
                if event_type == "response.output_audio.delta":
                    delta = str(event.get("delta") or "")
                    if delta:
                        self.audio_response_buffer.extend(base64.b64decode(delta))
                        self.audio_response_delta_count += 1
                elif event_type == "response.output_audio.done":
                    if self.audio_response_buffer:
                        audio = base64.b64encode(self.audio_response_buffer).decode("ascii")
                        logger.info(
                            "Realtime audio response complete: session=%s deltas=%d bytes=%d",
                            self.session.session_id,
                            self.audio_response_delta_count,
                            len(self.audio_response_buffer),
                        )
                        await emit(self.session, "audio_data", {
                            "audio": audio,
                            "format": "pcm16",
                            "sample_rate": REALTIME_SAMPLE_RATE,
                        })
                        self.audio_response_buffer.clear()
                        self.audio_response_delta_count = 0
                elif event_type == "response.output_audio_transcript.delta":
                    self.transcript += str(event.get("delta") or "")
                elif event_type == "response.output_audio_transcript.done":
                    text = self.transcript.strip()
                    self.transcript = ""
                    if text:
                        await emit(self.session, "system_message", {"text": text})
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    text = str(event.get("transcript") or "").strip()
                    if text:
                        await emit(self.session, "user_message", {"text": text})
                elif event_type == "response.done":
                    self.response_active = False
                    self.response_done.set()
                    for output in (event.get("response") or {}).get("output", []):
                        if output.get("type") == "function_call" and output.get("name") == "dialbb_turn":
                            await self.handle_function_call(output)
                    if self.response_pending and not self.response_active:
                        self.response_pending = False
                        await self.request_response()
                elif event_type == "error":
                    message = str(event.get("error") or event)
                    logger.error("Realtime API error: session=%s %s", self.session.session_id, message)
                    await emit(self.session, "error", {"message": message})
        except (json.JSONDecodeError, OSError, RuntimeError):
            logger.exception("Realtime receive loop stopped: session=%s", self.session.session_id)

    async def close(self) -> None:
        if self.session.realtime is not None:
            await self.session.realtime.close()
            self.session.realtime = None


async def emit(session: PrototypeSession, event_name: str, payload: dict[str, Any]) -> None:
    if session.websocket is not None and not session.closed:
        await session.websocket.send_json({"event": event_name, "payload": payload})


def create_app(config_file: str) -> FastAPI:
    app = FastAPI(title="DialBB GPT Realtime Prototype")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    sessions: dict[str, PrototypeSession] = {}

    @app.get("/gateway-info")
    async def root() -> dict[str, Any]:
        return {
            "service": "dialbb-gpt-realtime-prototype",
            "status": "ok",
            "message": "Gateway is running. Use the mm_frontend with ?realtime=1.",
            "health": "/health",
            "websocket": "/dialogue/ws/{session_id}",
        }

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "dialbb-gpt-realtime-prototype"}

    @app.post("/sessions", status_code=201)
    async def create_session() -> dict[str, str]:
        session_id = str(uuid.uuid4())
        sessions[session_id] = PrototypeSession(session_id=session_id)
        return {"session_id": session_id}

    @app.delete("/sessions/{session_id}")
    async def delete_session(session_id: str) -> dict[str, str]:
        session = sessions.pop(session_id, None)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        session.closed = True
        return {"status": "deleted"}

    @app.websocket("/dialogue/ws/{session_id}")
    async def dialogue_socket(websocket: WebSocket, session_id: str) -> None:
        session = sessions.get(session_id)
        if session is None:
            await websocket.close(code=1008, reason="Session not found")
            return
        await websocket.accept()
        session.websocket = websocket
        realtime: RealtimeConnection | None = None
        receiver: asyncio.Task[None] | None = None
        try:
            while True:
                payload = await websocket.receive_json()
                action = payload.get("action")
                if action == "start_dialogue":
                    try:
                        realtime = RealtimeConnection(session, config_file)
                        await realtime.connect()
                        receiver = asyncio.create_task(realtime.receive_loop())
                        await realtime.start_initial_response()
                    except (RuntimeError, OSError, ValueError) as exc:
                        await emit(session, "error", {"message": str(exc)})
                elif action == "send_audio_chunk" and realtime is not None:
                    await realtime.append_audio(str(payload.get("audio_data") or ""))
                elif action == "end_dialogue":
                    break
        except WebSocketDisconnect:
            pass
        finally:
            session.closed = True
            if receiver is not None:
                receiver.cancel()
            if realtime is not None:
                await realtime.close()
            sessions.pop(session_id, None)

    frontend_dist_dir = Path(__file__).resolve().parents[1] / "multimodal" / "static" / "mobile"
    if not frontend_dist_dir.is_dir():
        raise RuntimeError(
            f"Frontend build directory not found: {frontend_dist_dir}. "
            "Run `npm run build` in mm_frontend first."
        )
    app.mount("/", StaticFiles(directory=frontend_dist_dir, html=True), name="frontend")

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the DialBB GPT Realtime prototype server")
    parser.add_argument("config_file")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5010)
    args = parser.parse_args()
    load_dotenv()
    uvicorn.run(create_app(args.config_file), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
