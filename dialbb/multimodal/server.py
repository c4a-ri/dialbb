"""mm_client Server.

FastAPI による REST API + WebSocket サーバ。
"""

from __future__ import annotations

import argparse
import asyncio
from concurrent.futures import Future as ConcurrentFuture
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dialbb.util.logger import get_logger
from .core import DialogueEvent
from .engine import DialogueEngineManager, SessionConfig
from .main.messages import DialbbRequest

logger = get_logger(__name__)


class TextUtteranceRequest(BaseModel):
    text: str


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
    config_file: str | None = None,
    default_config: SessionConfig | None = None,
) -> tuple[FastAPI, DialogueEngineManager, WebSocketSessionHub]:
    """FastAPI アプリケーション及びエンジンマネージャを作成する。"""
    app = FastAPI(title="DialBB mm_client server")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if default_config is None:
        default_config = _load_config(config_file)

    session_hub = WebSocketSessionHub()

    def on_event(session_id: str, event: DialogueEvent) -> None:
        emit_data = {
            "event_type": event.event_type,
            "data": event.data,
            "timestamp": event.timestamp,
        }
        session_hub.emit_from_thread(session_id, "dialogue_event", emit_data)
        logger.debug("[SERVER] Event emitted: session=%s, type=%s", session_id, event.event_type)

    engine_manager = DialogueEngineManager(default_config, event_callback=on_event)
    app.state.engine_manager = engine_manager
    app.state.session_hub = session_hub

    @app.on_event("startup")
    async def on_startup() -> None:
        session_hub.attach_loop(asyncio.get_running_loop())

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "mm-client-server"}

    @app.post("/sessions", status_code=201)
    async def create_session() -> dict[str, str]:
        session_id = engine_manager.create_session()
        return {"session_id": session_id}

    @app.post("/sessions/{session_id}/start")
    async def start_session(session_id: str) -> dict[str, str]:
        success = engine_manager.start_session(session_id)
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

    @app.post("/sessions/{session_id}/utterance")
    async def send_utterance(session_id: str, body: TextUtteranceRequest) -> dict[str, str]:
        text = body.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="text is required")

        _enqueue_utterance(engine_manager, session_id, text)
        logger.info("[SERVER] テキスト発話受信: session=%s, text=%s", session_id, text)
        return {"status": "sent"}

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
                    await _handle_start_dialogue(websocket, engine_manager, session_id)
                elif action == "end_dialogue":
                    await _handle_end_dialogue(websocket, engine_manager, session_id)
                elif action == "send_text_utterance":
                    text = str(payload.get("text") or "").strip()
                    if not text:
                        await websocket.send_json(
                            {"event": "error", "payload": {"message": "text is required"}}
                        )
                        continue
                    _enqueue_utterance(engine_manager, session_id, text)
                    logger.info("[WEBSOCKET] Text utterance: session=%s, text=%s", session_id, text)
                elif action == "send_audio_chunk":
                    logger.debug("[WEBSOCKET] Audio chunk received: session=%s", session_id)
                else:
                    await websocket.send_json(
                        {"event": "error", "payload": {"message": "Unsupported action"}}
                    )
        except WebSocketDisconnect:
            logger.info("[WEBSOCKET] Client disconnected: session=%s", session_id)
        finally:
            await session_hub.disconnect(session_id, websocket)

    return app, engine_manager, session_hub


def _enqueue_utterance(
    engine_manager: DialogueEngineManager,
    session_id: str,
    text: str,
) -> None:
    session = engine_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.dialbb_request_queue.put(
        DialbbRequest(
            session_id=session.engine.session_id,
            user_text=text,
            aux_data={},
        )
    )


async def _handle_start_dialogue(
    websocket: WebSocket,
    engine_manager: DialogueEngineManager,
    session_id: str,
) -> None:
    success = engine_manager.start_session(session_id)
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


def _load_config(config_file: str | None = None) -> SessionConfig:
    """設定ファイルから SessionConfig を読み込む。"""
    config_path = Path(config_file or Path.cwd() / "config" / "mm_client_config.yml")
    config_path = config_path.expanduser().resolve()
    logger.info("[SERVER] 設定ファイル: %s", config_path)

    config_data: dict[str, Any] = {}
    if config_path.exists():
        with config_path.open(encoding="utf-8") as config_fp:
            config_data = yaml.safe_load(config_fp) or {}

    stt_cfg = config_data.get("stt") or {}
    dialbb_cfg = config_data.get("dialbb") or {}
    main_cfg = config_data.get("main") or {}

    stt_key = stt_cfg.get("key_file")
    if stt_key:
        stt_key_path = Path(stt_key).expanduser()
        if not stt_key_path.is_absolute():
            stt_key_path = config_path.parent / stt_key_path
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(stt_key_path.resolve())

    return SessionConfig(
        dialbb_config=dialbb_cfg.get("config_file"),
        stt_key_file=stt_cfg.get("key_file"),
        loop_period=float(main_cfg.get("loop_period", 0.1)),
        max_user_wait_time=float(main_cfg.get("max_user_wait_time", 30.0)),
        mic_gain=float(stt_cfg.get("mic_gain", 1.0)),
    )


def run_server(
    host: str = "0.0.0.0",
    port: int = 5000,
    config_file: str | None = None,
    debug: bool = False,
) -> None:
    """サーバを起動する。"""
    app, _, _ = create_app(config_file)
    logger.info("[SERVER] Starting mm_client_server on %s:%d", host, port)
    uvicorn.run(app, host=host, port=port, reload=debug)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DialBB mm_client server")
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=5000, help="Server port")
    parser.add_argument("--config", help="Config file path")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    run_server(
        host=args.host,
        port=args.port,
        config_file=args.config,
        debug=args.debug,
    )
