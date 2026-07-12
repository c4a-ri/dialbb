"""mm_client Server.

FastAPI による REST API + WebSocket サーバ。
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import binascii
from concurrent.futures import Future as ConcurrentFuture
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from dialbb.util.logger import get_logger
from .core import DialogueEvent
from .engine import DialogueEngineManager, SessionConfig
from .tts.speech_synthesizer import split_tts_segments

logger = get_logger(__name__)


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
                logger.info("[SERVER] user audio log flushed on final transcript: session=%s", session_id)
        logger.debug("[SERVER] Event handled: session=%s, type=%s", session_id, event.event_type)

    def on_tts_audio(session_id: str, segment_index: int, segment_count: int, audio_bytes: bytes) -> None:
        """TTS 合成音声を送信し、再生完了 ack まで待つ。"""
        if engine_manager.is_tts_cancel_requested(session_id):
            logger.debug(
                "[SERVER] TTS audio dropped by cancel flag: session=%s segment=%d/%d bytes=%d",
                session_id,
                segment_index,
                segment_count,
                len(audio_bytes),
            )
            return
        session = engine_manager.get_session(session_id)
        utterance_id = 0
        if session:
            with session.tts_state_lock:
                utterance_id = session.current_tts_utterance_id
        engine_manager.record_system_audio_chunk(
            session_id,
            audio_bytes,
            utterance_id,
            segment_index,
            segment_count,
        )
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        session_hub.emit_from_thread(
            session_id,
            "audio_data",
            {
                "audio": audio_b64,
                "format": "mp3",
                "utterance_id": utterance_id,
                "segment_index": segment_index,
                "segment_count": segment_count,
            },
        )
        logger.debug(
            "[SERVER] TTS audio emitted: session=%s utterance=%s segment=%d/%d bytes=%d",
            session_id,
            utterance_id,
            segment_index,
            segment_count,
            len(audio_bytes),
        )

        if not engine_manager.wait_for_tts_segment_playback_done(
            session_id,
            utterance_id,
            segment_index,
        ):
            logger.info(
                "[SERVER] playback wait interrupted: session=%s utterance=%s segment=%d/%d",
                session_id,
                utterance_id,
                segment_index,
                segment_count,
            )
            return

        logger.debug(
            "[SERVER] playback ack confirmed: session=%s utterance=%s segment=%d/%d",
            session_id,
            utterance_id,
            segment_index,
            segment_count,
        )

    engine_manager = DialogueEngineManager(
        default_config,
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
        logger.info("[SERVER] shutdown 開始")
        active_sessions = engine_manager.list_sessions()
        logger.info("[SERVER] shutdown 対象セッション: %s", active_sessions)
        for session_id in active_sessions:
            session = engine_manager.get_session(session_id)
            if session and session.is_active:
                logger.info("[SERVER] active session を停止: %s", session_id)
                engine_manager.stop_session(session_id)
        logger.info(
            "[SERVER] shutdown 時の生存スレッド: %s",
            ", ".join(thread.name for thread in threading.enumerate()),
        )
        logger.info("[SERVER] shutdown 完了")

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
                                # バージインは STT の partial/final で判定する。
                                # 生の音声チャンク到着だけでは割り込みキャンセルしない。
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
                    logger.info(
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

    return app, engine_manager, session_hub


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
    config_path = Path(config_file or "config.yml").expanduser().resolve()
    logger.info("[SERVER] 設定ファイル: %s", config_path)

    config_data: dict[str, Any] = {}
    if config_path.exists():
        with config_path.open(encoding="utf-8") as config_fp:
            config_data = yaml.safe_load(config_fp) or {}

    mm_config = config_data.get("multimodal") or {}
    stt_cfg = mm_config.get("stt") or {}
    main_cfg = mm_config.get("main") or {}

    stt_key = stt_cfg.get("key_file")
    if stt_key:
        stt_key_path = Path(stt_key).expanduser()
        if not stt_key_path.is_absolute():
            stt_key_path = config_path.parent / stt_key_path
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(stt_key_path.resolve())

    return SessionConfig(
        dialbb_config=config_file,
        stt_key_file=stt_cfg.get("key_file"),
        loop_period=float(main_cfg.get("loop_period", 0.1)),
        max_user_wait_time=float(main_cfg.get("max_user_wait_time", 30.0)),
        audio_logging=bool(main_cfg.get("audio_logging", False)),
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


def main() -> None:
    """CLI entry point for mm_client server."""
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


if __name__ == "__main__":
    main()
