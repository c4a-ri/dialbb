"""mm_client Server.

REST API and WebSocket server powered by FastAPI.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import binascii
from concurrent.futures import Future as ConcurrentFuture
import queue
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast
from dotenv import load_dotenv

import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from dialbb.util.logger import get_logger
from .core import DialogueEvent
from .engine import DialogueEngineManager, Settings
from .tts.speech_synthesizer import (
    TTS_AUDIO_FORMAT,
    TTS_SAMPLE_RATE_HZ,
    split_tts_audio_chunks,
    split_tts_segments,
)

logger = get_logger(__name__)
TTS_CHUNK_BUFFER_WINDOW = 3

@dataclass
class SessionConnections:
    sockets: set[WebSocket] = field(default_factory=set)


class WebSocketSessionHub:

    def __init__(self) -> None:
        self._connections: dict[str, SessionConnections] = {}
        self._lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            session_connections = self._connections.setdefault(session_id, SessionConnections())
            session_connections.sockets.add(websocket)

    async def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            session_connections = self._connections.get(session_id)
            if not session_connections:
                return
            session_connections.sockets.discard(websocket)
            if not session_connections.sockets:
                self._connections.pop(session_id, None)

    async def emit_to_session(self, session_id: str, event_name: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            sockets = list(self._connections.get(session_id, SessionConnections()).sockets)

        disconnected: list[WebSocket] = []
        for websocket in sockets:
            try:
                await websocket.send_json({"event": event_name, "payload": payload})
            except (RuntimeError, WebSocketDisconnect):
                disconnected.append(websocket)

        for websocket in disconnected:
            await self.disconnect(session_id, websocket)

    def emit_from_thread(self, session_id: str, event_name: str, payload: dict[str, Any]) -> None:
        if self._loop is None:
            logger.debug("[SERVER] event loop is not attached yet; drop event=%s", event_name)
            return
        future = asyncio.run_coroutine_threadsafe(
            self.emit_to_session(session_id, event_name, payload),
            self._loop,
        )
        future.add_done_callback(self._log_emit_failure)

    @staticmethod
    def _log_emit_failure(future: ConcurrentFuture[None]) -> None:
        exception = future.exception()
        if exception is not None:
            logger.error(
                "[SERVER] failed to emit websocket event",
                exc_info=(type(exception), exception, exception.__traceback__),
            )


def create_app(
        config_file: str,
        debug: bool,
        audio_logging: bool
) -> FastAPI:
    """
    Creates FastAPI app and engine manager.
    """

    app = FastAPI(title="DialBB MM Server")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    settings: Settings = _determine_settings(config_file, debug, audio_logging)

    session_hub = WebSocketSessionHub()

    def on_event(session_id: str, event: DialogueEvent) -> None:
        if event.event_type == "chat" and event.data.get("role") == "system":
            utterance_id = engine_manager.begin_tts_utterance(session_id, str(event.data.get("text") or ""))
            logger.info(
                "[SERVER] system utterance start: session=%s utterance_id=%s segments=%d text=%s",
                session_id,
                utterance_id,
                len(split_tts_segments(str(event.data.get("text") or ""))),
                event.data.get("text"),
            )
        elif event.event_type == "chat" and event.data.get("role") == "user":
            transcript = str(event.data.get("text") or "")
            if engine_manager.flush_user_audio_log(session_id, transcript):
                logger.info(f"[SERVER] user audio log flushed on final transcript: session=%s", session_id)
        logger.debug("[SERVER] Event handled: session=%s, type=%s", session_id, event.event_type)

    def on_tts_audio(session_id: str, segment_index: int, segment_count: int, audio_bytes: bytes) -> bool:
        """Send synthesized speech in buffered 100ms chunks and wait for final playback."""
        if engine_manager.is_tts_cancel_requested(session_id):
            logger.debug(
                "[SERVER] TTS audio dropped by cancel flag: session=%s segment=%d/%d bytes=%d",
                session_id,
                segment_index,
                segment_count,
                len(audio_bytes),
            )
            return False
        audio_chunks = split_tts_audio_chunks(audio_bytes)
        if not audio_chunks:
            logger.warning("[SERVER] empty TTS audio ignored: session=%s", session_id)
            return False

        session = engine_manager.get_session(session_id)
        utterance_id = 0
        if session:
            with session.tts_state_lock:
                utterance_id = session.current_tts_utterance_id
                session.current_tts_total_segments = len(audio_chunks)

        total_chunks = len(audio_chunks)
        for chunk_index, chunk_bytes in enumerate(audio_chunks, start=1):
            if engine_manager.is_tts_cancel_requested(session_id):
                logger.info(
                    "[SERVER] cancel detected, stop sending remaining chunks: session=%s utterance=%s next_chunk=%d/%d",
                    session_id,
                    utterance_id,
                    chunk_index,
                    total_chunks,
                )
                return False

            engine_manager.record_system_audio_chunk(
                session_id,
                chunk_bytes,
                utterance_id,
                chunk_index,
                total_chunks,
                audio_format=TTS_AUDIO_FORMAT,
                sample_rate=TTS_SAMPLE_RATE_HZ,
            )
            audio_b64 = base64.b64encode(chunk_bytes).decode("utf-8")
            session_hub.emit_from_thread(
                session_id,
                "audio_data",
                {
                    "audio": audio_b64,
                    "format": TTS_AUDIO_FORMAT,
                    "utterance_id": utterance_id,
                    "segment_index": chunk_index,
                    "segment_count": total_chunks,
                },
            )
            logger.debug(
                "[SERVER] TTS audio emitted: session=%s utterance=%s chunk=%d/%d bytes=%d",
                session_id,
                utterance_id,
                chunk_index,
                total_chunks,
                len(chunk_bytes),
            )

            ack_target = chunk_index - TTS_CHUNK_BUFFER_WINDOW
            if ack_target <= 0:
                continue

            if not engine_manager.wait_for_tts_segment_playback_done(
                session_id,
                utterance_id,
                ack_target,
            ):
                logger.info(
                    "[SERVER] playback wait interrupted: session=%s utterance=%s chunk=%d/%d ack_target=%d",
                    session_id,
                    utterance_id,
                    chunk_index,
                    total_chunks,
                    ack_target,
                )
                return False

            logger.debug(
                "[SERVER] buffered playback ack confirmed: session=%s utterance=%s chunk=%d/%d ack_target=%d",
                session_id,
                utterance_id,
                chunk_index,
                total_chunks,
                ack_target,
            )

        if not engine_manager.wait_for_tts_segment_playback_done(
            session_id,
            utterance_id,
            total_chunks,
        ):
            logger.info(
                "[SERVER] final playback wait interrupted: session=%s utterance=%s final_chunk=%d/%d",
                session_id,
                utterance_id,
                total_chunks,
                total_chunks,
            )
            return False

        logger.debug(
            "[SERVER] final playback ack confirmed: session=%s utterance=%s total_chunks=%d",
            session_id,
            utterance_id,
            total_chunks,
        )
        return True

    engine_manager = DialogueEngineManager(
        settings=settings,
        event_callback=on_event,
        tts_audio_callback=cast(Any, on_tts_audio),
    )
    app.state.engine_manager = engine_manager
    app.state.session_hub = session_hub

    @app.on_event("startup")
    async def on_startup() -> None:
        session_hub.attach_loop(asyncio.get_running_loop())

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        logger.info("[SERVER] shutdown started")
        active_sessions = engine_manager.list_sessions()
        logger.info("[SERVER] session to shutdown: %s", active_sessions)
        for session_id in active_sessions:
            session = engine_manager.get_session(session_id)
            if session and session.is_active:
                logger.info("[SERVER] halting active session: %s", session_id)
                engine_manager.stop_session(session_id)
        logger.info(
            "[SERVER] threads alive at shutdown: %s",
            ", ".join(thread.name for thread in threading.enumerate()),
        )
        logger.info("[SERVER] shutdown finished")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "mm-client-server"}

    @app.post("/sessions", status_code=201)
    async def create_session() -> dict[str, str]:
        session_id = engine_manager.create_session()
        return {"session_id": session_id}

    @app.post("/sessions/{session_id}/start")
    async def start_session(session_id: str) -> dict[str, str]:
        success = engine_manager.start_session(session_id, settings)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to start session")
        return {"status": "started"}

    @app.post("/sessions/{session_id}/stop")
    async def stop_session(session_id: str) -> dict[str, str]:
        success = engine_manager.stop_session(session_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to stop session")
        return {"status": "stopped"}

    @app.delete("/sessions/{session_id}")
    async def delete_session(session_id: str) -> dict[str, str]:
        success = engine_manager.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"status": "deleted"}

    @app.get("/sessions")
    async def list_sessions() -> dict[str, list[str]]:
        return {"sessions": engine_manager.list_sessions()}

    @app.websocket("/dialogue/ws/{session_id}")
    async def dialogue_socket(websocket: WebSocket, session_id: str) -> None:
        session = engine_manager.get_session(session_id)
        if not session:
            await websocket.close(code=1008, reason="Session not found")
            return

        await session_hub.connect(session_id, websocket)
        logger.info("[WEBSOCKET] Client connected: session=%s", session_id)
        await websocket.send_json({"event": "joined_session", "payload": {"session_id": session_id}})

        try:
            while True:
                payload = await websocket.receive_json()
                action = payload.get("action")
                if action == "start_dialogue":
                    await _handle_start_dialogue(websocket, engine_manager, session_id, settings)
                elif action == "end_dialogue":
                    await _handle_end_dialogue(websocket, engine_manager, session_id)
                elif action == "cancel_tts":
                    _request_tts_cancel(engine_manager, session_id)
                    logger.info("[WEBSOCKET] TTS cancel requested: session=%s", session_id)
                elif action == "send_audio_chunk":
                    audio_b64 = str(payload.get("audio_data") or "")
                    if audio_b64:
                        try:
                            audio_bytes = base64.b64decode(audio_b64)
                            _session = engine_manager.get_session(session_id)
                            # logger.info("[WEBSOCKET] Audio chunk received: session=%s, bytes=%d", session_id, len(audio_bytes))
                            if _session:
                                _session.audio_chunk_queue.put(audio_bytes)
                                engine_manager.record_user_audio_chunk(session_id, audio_bytes)
                                # Determine barge-in from STT partial/final events.
                                # Do not cancel on raw audio chunk arrival alone.
                        except (ValueError, binascii.Error):
                            logger.warning("[WEBSOCKET] Invalid audio chunk: session=%s", session_id)
                    else:
                        logger.debug("[WEBSOCKET] Audio chunk received (empty): session=%s", session_id)
                elif action == "tts_segment_playback_done":
                    utterance_id = int(payload.get("utterance_id") or 0)
                    segment_index = int(payload.get("segment_index") or 0)
                    segment_count = int(payload.get("segment_count") or 0)
                    if utterance_id <= 0 or segment_index <= 0 or segment_count <= 0:
                        await websocket.send_json(
                            {"event": "error", "payload": {"message": "invalid tts playback ack"}}
                        )
                        continue

                    result = engine_manager.record_tts_segment_playback_done(
                        session_id,
                        utterance_id,
                        segment_index,
                        segment_count,
                    )
                    if result is None:
                        logger.info(
                            "[WEBSOCKET] stale playback ack ignored: session=%s utterance=%s segment=%s/%s",
                            session_id,
                            utterance_id,
                            segment_index,
                            segment_count,
                        )
                        continue

                    played_segments, total_segments, system_speaking = result
                    logger.debug(
                        "[WEBSOCKET] playback done: session=%s utterance=%s segment=%d/%d played=%d/%d speaking=%s",
                        session_id,
                        utterance_id,
                        segment_index,
                        segment_count,
                        played_segments,
                        total_segments,
                        system_speaking,
                    )
                else:
                    await websocket.send_json(
                        {"event": "error", "payload": {"message": "Unsupported action"}}
                    )
        except WebSocketDisconnect:
            logger.info("[WEBSOCKET] Client disconnected: session=%s", session_id)
        finally:
            await session_hub.disconnect(session_id, websocket)

    return app


def _request_tts_cancel(engine_manager: DialogueEngineManager, session_id: str) -> None:
    if not engine_manager.set_tts_cancel_requested(session_id, True):
        raise HTTPException(status_code=404, detail="Session not found")

    session = engine_manager.get_session(session_id)
    if session:
        session.tts_cancel_queue.put("cancel")


async def _handle_start_dialogue(
        websocket: WebSocket,
        engine_manager: DialogueEngineManager,
        session_id: str,
        settings: Settings
) -> None:
    success = engine_manager.start_session(session_id, settings)
    if not success:
        await websocket.send_json(
            {"event": "error", "payload": {"message": "Failed to start dialogue"}}
        )
        return
    logger.info("[WEBSOCKET] Dialogue started: %s", session_id)


async def _handle_end_dialogue(
    websocket: WebSocket,
    engine_manager: DialogueEngineManager,
    session_id: str,
) -> None:
    success = engine_manager.stop_session(session_id)
    if not success:
        await websocket.send_json(
            {"event": "error", "payload": {"message": "Failed to stop dialogue"}}
        )
        return
    logger.info("[WEBSOCKET] Dialogue stopped: %s", session_id)


def _determine_settings(config_file: str, debug: bool, audio_logging: bool) -> Settings:
    """Load SessionConfig from a configuration file."""
    config_path = Path(config_file).expanduser().resolve()
    logger.info(f"[SERVER] reading config file {config_path}")

    config: dict[str, Any] = {}
    if config_path.exists():
        with config_path.open(encoding="utf-8") as config_fp:
            config = yaml.safe_load(config_fp) or {}

    return Settings(
        config_file=config_file,
        config=config,
        cycle=float(config.get("cycle", 0.1)),
        user_timeout=float(config.get("user_timeout", 30.0)),
        audio_logging=bool(config.get("audio_logging", False)),
    )


def _parse_factory_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("config")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--audio_logging", action="store_true")
    args, _ = parser.parse_known_args(argv)
    return args


def create_configured_app() -> FastAPI:
    args = _parse_factory_args(sys.argv[1:])
    return create_app(args.config, args.debug, args.audio_logging)


def run_server(config_file: str, host: str, port: int, debug: bool, audio_logging: bool) -> None:
    """Start the server."""

    logger.info("[SERVER] Starting mm_client_server on %s:%d", host, port)
    uvicorn.run(
        "dialbb.multimodal.server:create_configured_app",
        host=host,
        port=port,
        reload=debug,
        factory=True,
    )


def main() -> None:
    """CLI entry point for mm_client server."""

    env_path = Path.cwd() / ".env"
    load_dotenv(env_path)

    parser = argparse.ArgumentParser(description="DialBB mm_client server")
    parser.add_argument("config", help="Config file path", )
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=5000, help="Server port")
    parser.add_argument("--debug", action="store_true", help="Toggle debug mode")
    parser.add_argument("--audio_logging", action="store_true", help="Enable audio logging")
    args = parser.parse_args()

    run_server(
        args.config,
        host=args.host,
        port=args.port,
        debug=args.debug,
        audio_logging=args.audio_logging
    )


if __name__ == "__main__":
    main()
