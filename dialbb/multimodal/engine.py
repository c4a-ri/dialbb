"""
mm_client Engine
マルチセッション対応のダイアログエンジン管理
"""
from datetime import datetime
from contextlib import closing
import json
from pathlib import Path
import time
import queue
import threading
import uuid
import wave
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Callable, cast

from dialbb.util.logger import get_logger
from .core import CoreDialogueEngine, DialogueEvent
from .asr.google_stt_client import run_stt_worker
from .main.dialbb_client import run_dialbb_worker
from .tts.speech_synthesizer import run_tts_worker

logger = get_logger(__name__)


@dataclass
class SessionConfig:
    """セッション設定"""
    dialbb_config: Optional[str] = None
    stt_key_file: Optional[str] = None
    loop_period: float = 0.1
    max_user_wait_time: float = 30.0
    sample_rate: int = 16000
    language_code: str = "ja-JP"
    audio_logging: bool = False


@dataclass
class DialogueSession:
    """セッション状態管理"""
    session_id: str
    engine: CoreDialogueEngine
    # キュー
    stt_event_queue: "queue.Queue" = field(default_factory=queue.Queue)
    dialbb_request_queue: "queue.Queue" = field(default_factory=queue.Queue)
    dialbb_response_queue: "queue.Queue" = field(default_factory=queue.Queue)
    tts_request_queue: "queue.Queue" = field(default_factory=queue.Queue)
    tts_result_queue: "queue.Queue" = field(default_factory=queue.Queue)
    tts_cancel_queue: "queue.Queue" = field(default_factory=queue.Queue)
    command_queue: "queue.Queue" = field(default_factory=queue.Queue)
    # WebSocket 音声入力キュー（クライアントからの PCM16 チャンクを STT へ渡す）
    audio_chunk_queue: "queue.Queue" = field(default_factory=queue.Queue)
    # イベント制御
    stop_event: threading.Event = field(default_factory=threading.Event)
    conversation_active_event: threading.Event = field(default_factory=threading.Event)
    stt_enabled_event: threading.Event = field(default_factory=threading.Event)
    audio_logging_enabled: bool = False
    audio_sample_rate: int = 16000
    audio_user_buffer: list["AudioChunk"] = field(default_factory=list)
    audio_log_queue: "queue.Queue[AudioLogEntry | None]" = field(default_factory=queue.Queue)
    audio_log_sequence: int = 0
    audio_lock: threading.Lock = field(default_factory=threading.Lock)
    tts_state_lock: threading.Condition = field(
        default_factory=lambda: threading.Condition(threading.Lock())
    )
    current_tts_utterance_id: int = 0
    current_tts_text: str = ""
    current_tts_total_segments: int = 0
    current_tts_played_segments: set[int] = field(default_factory=set)
    pending_tts_aux_data: dict[str, Any] = field(default_factory=dict)
    system_speaking: bool = False
    # ワーカースレッド
    workers: list = field(default_factory=list)
    # ステータス
    is_active: bool = False
    tts_cancel_requested: bool = False


@dataclass
class AudioLogEntry:
    sequence: int
    timestamp_ns: int
    source: str
    audio_format: str
    audio_bytes: bytes
    transcript: str | None = None
    sample_rate: int | None = None
    utterance_id: int | None = None
    segment_index: int | None = None
    segment_count: int | None = None


@dataclass
class AudioChunk:
    timestamp_ns: int
    audio_bytes: bytes


class DialogueEngineManager:
    """マルチセッション対応のダイアログエンジン管理"""

    def __init__(
        self,
        default_config: SessionConfig,
        event_callback: Optional[Callable[[str, DialogueEvent], None]] = None,
        tts_audio_callback: Optional[Callable[[str, int, int, bytes], None]] = None,
    ) -> None:
        self.default_config = default_config
        self.sessions: Dict[str, DialogueSession] = {}
        self.event_callback = event_callback
        self.tts_audio_callback = tts_audio_callback
        self._lock = threading.Lock()

    @staticmethod
    def _split_tts_segments(text: str) -> list[str]:
        segments = [segment.strip() for segment in text.split("。") if segment.strip()]
        return [
            (segment + "。") if not segment.endswith(("。", "！", "？", "!", "?")) else segment
            for segment in segments
        ]

    def create_session(self) -> str:
        """新しいセッションを作成して session_id を返す"""
        session_id = str(uuid.uuid4())
        with self._lock:
            engine = CoreDialogueEngine()
            callback = self.event_callback
            if callback is not None:
                engine.set_event_callback(
                    lambda event: callback(session_id, event)
                )
            session = DialogueSession(
                session_id=session_id,
                engine=engine,
            )
            self.sessions[session_id] = session
            logger.info("[ENGINE] セッション作成: %s", session_id)
        return session_id

    def start_session(self, session_id: str, config: Optional[SessionConfig] = None) -> bool:
        """セッションを開始（ワーカーを起動）"""
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                logger.error("[ENGINE] セッション見つかりません: %s", session_id)
                return False

            if session.is_active:
                logger.warning("[ENGINE] セッションは既に起動済み: %s", session_id)
                return False

            cfg = config or self.default_config
            with session.tts_state_lock:
                session.tts_cancel_requested = False
                session.system_speaking = False
                session.current_tts_text = ""
                session.current_tts_total_segments = 0
                session.current_tts_played_segments.clear()
            session.audio_logging_enabled = cfg.audio_logging
            session.audio_sample_rate = cfg.sample_rate
            with session.audio_lock:
                session.audio_user_buffer.clear()
                session.audio_log_queue = queue.Queue()
                session.audio_log_sequence = 0
            # ワーカーを起動
            workers = self._start_workers(session, cfg)
            session.workers = workers
            session.is_active = True
            logger.info("[ENGINE] セッション起動完了: %s", session_id)

        # start コマンドを送る
        session.command_queue.put("start")
        return True

    def _start_workers(self, session: DialogueSession, config: SessionConfig) -> list:
        """セッションのワーカースレッドを起動"""
        # WebSocket 音声入力を STT へ渡す
        stt_audio_q = session.audio_chunk_queue
        # TTS 音声データをコールバック経由で返送
        tts_audio_cb = None
        if self.tts_audio_callback:
            _cb = self.tts_audio_callback
            _sid = session.session_id
            tts_audio_cb = lambda segment_index, segment_count, audio_bytes: _cb(  # noqa: E731
                _sid,
                segment_index,
                segment_count,
                audio_bytes,
            )
        workers = [
            # STT ワーカー
            threading.Thread(
                target=run_stt_worker,
                kwargs={
                    "stt_event_queue": session.stt_event_queue,
                    "stop_event": session.stop_event,
                    "listening_enabled_event": session.stt_enabled_event,
                    "sample_rate": config.sample_rate,
                    "language_code": config.language_code,
                    "audio_chunk_queue": stt_audio_q,
                },
                name=f"stt-worker-{session.session_id[:8]}",
                daemon=False,
            ),
            # DialBB ワーカー
            threading.Thread(
                target=run_dialbb_worker,
                kwargs={
                    "dialbb_request_queue": session.dialbb_request_queue,
                    "dialbb_response_queue": session.dialbb_response_queue,
                    "stop_event": session.stop_event,
                    "config_file": config.dialbb_config,
                    "error_queue": queue.Queue(),  # エラーキューは別途処理
                },
                name=f"dialbb-worker-{session.session_id[:8]}",
                daemon=False,
            ),
            # TTS ワーカー
            threading.Thread(
                target=run_tts_worker,
                kwargs={
                    "tts_request_queue": session.tts_request_queue,
                    "tts_result_queue": session.tts_result_queue,
                    "stop_event": session.stop_event,
                    "conversation_active_event": session.conversation_active_event,
                    "tts_cancel_queue": session.tts_cancel_queue,
                    "cancel_state_clear_callback": self.clear_tts_cancel_requested,
                    "audio_send_callback": tts_audio_cb,
                },
                name=f"tts-worker-{session.session_id[:8]}",
                daemon=False,
            ),
            # Core エンジン ワーカー
            threading.Thread(
                target=session.engine.run,
                kwargs={
                    "stt_event_queue": session.stt_event_queue,
                    "dialbb_request_queue": session.dialbb_request_queue,
                    "dialbb_response_queue": session.dialbb_response_queue,
                    "tts_request_queue": session.tts_request_queue,
                    "tts_result_queue": session.tts_result_queue,
                    "conversation_active_event": session.conversation_active_event,
                    "stt_enabled_event": session.stt_enabled_event,
                    "stop_event": session.stop_event,
                    "command_queue": session.command_queue,
                    "tts_cancel_queue": session.tts_cancel_queue,
                    "loop_period": config.loop_period,
                    "max_user_wait_time": config.max_user_wait_time,
                },
                name=f"core-engine-{session.session_id[:8]}",
                daemon=False,
            ),
        ]
        if config.audio_logging:
            workers.insert(3, self._build_audio_log_worker(session))
        for worker in workers:
            worker.start()
        return workers

    def _build_audio_log_worker(self, session: DialogueSession) -> threading.Thread:
        def _run() -> None:
            logger.info("[ENGINE] audio log worker start: session=%s", session.session_id)
            try:
                while not session.stop_event.is_set() or not session.audio_log_queue.empty():
                    try:
                        entry = session.audio_log_queue.get(timeout=0.1)
                    except queue.Empty:
                        continue

                    if entry is None:
                        continue

                    self._save_audio_log_entry(session, entry)
            finally:
                logger.info("[ENGINE] audio log worker exit: session=%s", session.session_id)

        return threading.Thread(
            target=_run,
            name=f"audio-log-worker-{session.session_id[:8]}",
            daemon=False,
        )

    def stop_session(self, session_id: str) -> bool:
        """セッションを停止"""
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                logger.error("[ENGINE] セッション見つかりません: %s", session_id)
                return False

            if not session.is_active:
                logger.warning("[ENGINE] セッションは既に停止: %s", session_id)
                return False

            logger.info("[ENGINE] セッション停止開始: %s", session_id)
            logger.info("[ENGINE] 停止対象ワーカー: %s", [worker.name for worker in session.workers])
            # end コマンドを送る
            session.command_queue.put("end")
            # 全ワーカーに停止シグナルを送る
            session.stop_event.set()
            # audio_chunk_queue のブロックを解除する（WebSocket音声モード時）
            session.audio_chunk_queue.put(None)
            # ワーカーの終了を待つ
            for worker in session.workers:
                logger.info(
                    "[ENGINE] join待ち: session=%s worker=%s alive_before=%s",
                    session_id,
                    worker.name,
                    worker.is_alive(),
                )
                worker.join(timeout=3.0)
                logger.info(
                    "[ENGINE] join結果: session=%s worker=%s alive_after=%s",
                    session_id,
                    worker.name,
                    worker.is_alive(),
                )

            self._save_audio_log(session)

            alive = [w for w in session.workers if w.is_alive()]
            if alive:
                logger.warning("[ENGINE] 未終了ワーカー: %s", [w.name for w in alive])
            else:
                logger.info("[ENGINE] 全ワーカー終了を確認: %s", session_id)

            logger.info(
                "[ENGINE] 現在の生存スレッド: %s",
                ", ".join(thread.name for thread in threading.enumerate()),
            )

            session.is_active = False
            logger.info("[ENGINE] セッション停止完了: %s", session_id)
        return True

    def _save_audio_log(self, session: DialogueSession) -> None:
        if not session.audio_logging_enabled:
            return
        logger.debug("[ENGINE] audio log stop requested: %s", session.session_id)

    def _save_audio_log_entry(self, session: DialogueSession, entry: AudioLogEntry) -> None:
        output_dir = Path.cwd() / "audio_logs" / session.session_id
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = output_dir / "manifest.jsonl"

        timestamp = datetime.fromtimestamp(entry.timestamp_ns / 1_000_000_000)
        base_name = f"{entry.sequence:06d}_{timestamp:%Y%m%d_%H%M%S_%f}_{entry.source}"

        if entry.audio_format == "wav":
            output_path = output_dir / f"{base_name}.wav"
            try:
                with closing(cast(wave.Wave_write, wave.open(str(output_path), "wb"))) as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(entry.sample_rate or session.audio_sample_rate)
                    wf.writeframes(entry.audio_bytes)
                self._append_manifest_entry(
                    manifest_path,
                    entry,
                    output_path.name,
                )
                logger.debug("[ENGINE] audio log saved: %s", output_path)
            except OSError as exc:
                logger.warning("[ENGINE] audio log save failed: %s", exc)
            return

        if entry.audio_format == "mp3":
            suffix = ""
            if entry.utterance_id is not None:
                suffix += f"_utt{entry.utterance_id:06d}"
            if entry.segment_index is not None and entry.segment_count is not None:
                suffix += f"_seg{entry.segment_index:02d}of{entry.segment_count:02d}"
            output_path = output_dir / f"{base_name}{suffix}.mp3"
            try:
                output_path.write_bytes(entry.audio_bytes)
                self._append_manifest_entry(
                    manifest_path,
                    entry,
                    output_path.name,
                )
                logger.debug("[ENGINE] audio log saved: %s", output_path)
            except OSError as exc:
                logger.warning("[ENGINE] audio log save failed: %s", exc)
            return

        logger.warning("[ENGINE] unknown audio format for log: %s", entry.audio_format)

    def _append_manifest_entry(self, manifest_path: Path, entry: AudioLogEntry, file_name: str) -> None:
        record = {
            "sequence": entry.sequence,
            "timestamp_ns": entry.timestamp_ns,
            "source": entry.source,
            "audio_format": entry.audio_format,
            "file_name": file_name,
            "transcript": entry.transcript,
            "utterance_id": entry.utterance_id,
            "segment_index": entry.segment_index,
            "segment_count": entry.segment_count,
        }
        try:
            with manifest_path.open("a", encoding="utf-8") as manifest_fp:
                manifest_fp.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.warning("[ENGINE] manifest save failed: %s", exc)

    def record_user_audio_chunk(self, session_id: str, audio_bytes: bytes) -> bool:
        session = self.sessions.get(session_id)
        if not session or not session.audio_logging_enabled:
            return False

        with session.audio_lock:
            session.audio_user_buffer.append(
                AudioChunk(
                    timestamp_ns=time.time_ns(),
                    audio_bytes=audio_bytes,
                )
            )
        return True

    def flush_user_audio_log(self, session_id: str, transcript: str) -> bool:
        session = self.sessions.get(session_id)
        if not session or not session.audio_logging_enabled:
            return False

        normalized_text = transcript.strip()
        if not normalized_text:
            with session.audio_lock:
                session.audio_user_buffer.clear()
            return False

        with session.audio_lock:
            audio_chunks = list(session.audio_user_buffer)
            session.audio_user_buffer.clear()

        if not audio_chunks:
            return False

        audio_bytes = b"".join(chunk.audio_bytes for chunk in audio_chunks)
        return self._record_audio_log(
            session_id,
            source="user",
            audio_format="wav",
            audio_bytes=audio_bytes,
            transcript=normalized_text,
        )

    def record_system_audio_chunk(
        self,
        session_id: str,
        audio_bytes: bytes,
        utterance_id: int,
        segment_index: int,
        segment_count: int,
    ) -> bool:
        return self._record_audio_log(
            session_id,
            source="system",
            audio_format="mp3",
            audio_bytes=audio_bytes,
            utterance_id=utterance_id,
            segment_index=segment_index,
            segment_count=segment_count,
        )

    def _record_audio_log(
        self,
        session_id: str,
        source: str,
        audio_format: str,
        audio_bytes: bytes,
        transcript: str | None = None,
        utterance_id: int | None = None,
        segment_index: int | None = None,
        segment_count: int | None = None,
    ) -> bool:
        session = self.sessions.get(session_id)
        if not session or not session.audio_logging_enabled:
            return False

        with session.audio_lock:
            session.audio_log_sequence += 1
            session.audio_log_queue.put(
                AudioLogEntry(
                    sequence=session.audio_log_sequence,
                    timestamp_ns=time.time_ns(),
                    source=source,
                    audio_format=audio_format,
                    audio_bytes=audio_bytes,
                    transcript=transcript,
                    sample_rate=session.audio_sample_rate if audio_format == "wav" else None,
                    utterance_id=utterance_id,
                    segment_index=segment_index,
                    segment_count=segment_count,
                )
            )
        return True

    def delete_session(self, session_id: str) -> bool:
        """セッションを削除"""
        with self._lock:
            if session_id not in self.sessions:
                return False
            session = self.sessions[session_id]
            if session.is_active:
                self.stop_session(session_id)
            del self.sessions[session_id]
            logger.info("[ENGINE] セッション削除: %s", session_id)
        return True

    def send_command(self, session_id: str, command: str) -> bool:
        """セッションへコマンドを送る"""
        session = self.sessions.get(session_id)
        if not session:
            logger.error("[ENGINE] セッション見つかりません: %s", session_id)
            return False
        session.command_queue.put(command)
        return True

    def send_stt_event(self, session_id: str, event: dict) -> bool:
        """STT イベントを送る（音声ストリーム API 用）"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        session.stt_event_queue.put(event)
        return True

    def get_session(self, session_id: str) -> Optional[DialogueSession]:
        """セッションを取得"""
        return self.sessions.get(session_id)

    def begin_tts_utterance(self, session_id: str, text: str) -> int | None:
        """システム発話の再生を開始する。"""
        session = self.sessions.get(session_id)
        if not session:
            return None

        with session.tts_state_lock:
            session.current_tts_utterance_id += 1
            session.current_tts_text = text
            session.current_tts_total_segments = len(self._split_tts_segments(text))
            session.current_tts_played_segments.clear()
            session.tts_cancel_requested = False
            session.system_speaking = True
            return session.current_tts_utterance_id

    def set_tts_cancel_requested(self, session_id: str, requested: bool) -> bool:
        """TTS 送信抑止フラグを更新する。"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        with session.tts_state_lock:
            session.tts_cancel_requested = requested
            if requested:
                session.system_speaking = False
        return True

    def is_tts_cancel_requested(self, session_id: str) -> bool:
        """TTS 送信抑止フラグの状態を返す。"""
        session = self.sessions.get(session_id)
        return bool(session and session.tts_cancel_requested)

    def clear_tts_cancel_requested(self, session_id: str) -> bool:
        """TTS 送信抑止フラグを解除する。"""
        return self.set_tts_cancel_requested(session_id, False)

    def record_tts_segment_playback_done(
        self,
        session_id: str,
        utterance_id: int,
        segment_index: int,
        segment_count: int,
    ) -> tuple[int, int, bool] | None:
        """セグメント再生完了を記録する。"""
        session = self.sessions.get(session_id)
        if not session:
            return None

        with session.tts_state_lock:
            if utterance_id != session.current_tts_utterance_id:
                return None

            session.current_tts_played_segments.add(segment_index)
            played_segments = len(session.current_tts_played_segments)
            if played_segments >= segment_count or session.tts_cancel_requested:
                session.system_speaking = False
            session.tts_state_lock.notify_all()
            return played_segments, segment_count, session.system_speaking

    def wait_for_tts_segment_playback_done(
        self,
        session_id: str,
        utterance_id: int,
        segment_index: int,
        timeout: float = 30.0,
    ) -> bool:
        """指定セグメントの再生完了、または cancel を待つ。"""
        session = self.sessions.get(session_id)
        if not session:
            return False

        deadline = time.monotonic() + timeout
        with session.tts_state_lock:
            while True:
                if utterance_id != session.current_tts_utterance_id:
                    return False
                if session.tts_cancel_requested:
                    return False
                if segment_index in session.current_tts_played_segments:
                    return True

                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    logger.warning(
                        "[ENGINE] playback ack timeout: session=%s utterance=%s segment=%d",
                        session_id,
                        utterance_id,
                        segment_index,
                    )
                    return False

                session.tts_state_lock.wait(timeout=remaining)

    def list_sessions(self) -> list:
        """アクティブなセッション一覧を返す"""
        with self._lock:
            return [s.session_id for s in self.sessions.values() if s.is_active]
