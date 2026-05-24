"""
mm_client Engine
マルチセッション対応のダイアログエンジン管理
"""
import queue
import threading
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable

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
    mic_gain: float = 1.0
    sample_rate: int = 16000
    language_code: str = "ja-JP"


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
    # イベント制御
    stop_event: threading.Event = field(default_factory=threading.Event)
    conversation_active_event: threading.Event = field(default_factory=threading.Event)
    stt_enabled_event: threading.Event = field(default_factory=threading.Event)
    # ワーカースレッド
    workers: list = field(default_factory=list)
    # ステータス
    is_active: bool = False


class DialogueEngineManager:
    """マルチセッション対応のダイアログエンジン管理"""

    def __init__(
        self,
        default_config: SessionConfig,
        event_callback: Optional[Callable[[str, DialogueEvent], None]] = None,
    ) -> None:
        self.default_config = default_config
        self.sessions: Dict[str, DialogueSession] = {}
        self.event_callback = event_callback
        self._lock = threading.Lock()

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
        workers = [
            # STT ワーカー
            threading.Thread(
                target=run_stt_worker,
                kwargs={
                    "stt_event_queue": session.stt_event_queue,
                    "stop_event": session.stop_event,
                    "listening_enabled_event": session.stt_enabled_event,
                    "sample_rate": config.sample_rate,
                    "chunk_ms": 100,
                    "language_code": config.language_code,
                    "mic_gain": config.mic_gain,
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
        for worker in workers:
            worker.start()
        return workers

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

            # end コマンドを送る
            session.command_queue.put("end")
            # 全ワーカーに停止シグナルを送る
            session.stop_event.set()
            # ワーカーの終了を待つ
            for worker in session.workers:
                worker.join(timeout=3.0)

            alive = [w for w in session.workers if w.is_alive()]
            if alive:
                logger.warning("[ENGINE] 未終了ワーカー: %s", [w.name for w in alive])

            session.is_active = False
            logger.info("[ENGINE] セッション停止完了: %s", session_id)
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

    def send_stt_event(self, session_id: str, event) -> bool:
        """STT イベントを送る（音声ストリーム API 用）"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        session.stt_event_queue.put(event)
        return True

    def get_session(self, session_id: str) -> Optional[DialogueSession]:
        """セッションを取得"""
        return self.sessions.get(session_id)

    def list_sessions(self) -> list:
        """アクティブなセッション一覧を返す"""
        with self._lock:
            return [s.session_id for s in self.sessions.values() if s.is_active]
