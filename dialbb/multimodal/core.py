"""
mm_client Core Engine
会話状態管理・ロジックを担当するコアエンジン
Queue 依存を抽象化し、異なるUIやサーバから再利用可能
"""
import time
import threading
from dataclasses import dataclass, field
from queue import Empty, Queue
from threading import Event
from typing import Optional, Any, Callable, Dict

from dialbb.util.logger import get_logger
from .main.messages import (
    DialbbRequest,
    DialbbResponse,
    RecognitionEvent,
    RecognitionEventType,
    TtsRequest,
    TtsResult,
)

logger = get_logger(__name__)


@dataclass
class DialogueEvent:
    """対話イベント（UI/API を通じて外部へ通知）"""
    event_type: str  # "status", "chat", "tts_completed", "final", "error" など
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class CoreDialogueEngine:
    """
    会話の状態管理とロジック実装（Tkinter/API非依存）
    MultimodalMainModule から UI/worker 操作を分離した版
    """

    def __init__(self) -> None:
        self.session_id: str = ""
        # --- 状態変数 ---
        self.user_speaking: bool = False
        self.user_waiting: bool = False
        self.system_speaking: bool = False
        self.user_wait_start_time: Optional[float] = None
        self._barge_in_sent: bool = False
        self.is_final_response: bool = False
        # イベント通知コールバック
        self._event_callback: Optional[Callable[[DialogueEvent], None]] = None

    def set_event_callback(self, callback: Callable[[DialogueEvent], None]) -> None:
        """イベント通知用のコールバックを登録"""
        self._event_callback = callback

    def _emit_event(self, event: DialogueEvent) -> None:
        """イベントを外部へ通知"""
        if self._event_callback:
            self._event_callback(event)
        logger.debug("[CORE] Event: %s", event)

    def _reset_state(self) -> None:
        """対話開始・終了時に状態変数をリセット"""
        self.session_id = ""
        self.user_speaking = False
        self.user_waiting = False
        self.system_speaking = False
        self.user_wait_start_time = None
        self._barge_in_sent = False
        self.is_final_response = False

    @staticmethod
    def _drain(q: Queue) -> None:
        """キューに残留するメッセージを全て破棄"""
        while not q.empty():
            try:
                q.get_nowait()
            except Empty:
                break

    def process_start_command(
        self,
        stt_event_queue: Queue,
        dialbb_request_queue: Queue,
        dialbb_response_queue: Queue,
        tts_request_queue: Queue,
        tts_result_queue: Queue,
        conversation_active_event: Event,
        stt_enabled_event: Event,
        tts_cancel_queue: Optional[Queue] = None,
    ) -> None:
        """対話開始コマンドを処理"""
        del tts_request_queue
        logger.info("[CORE] start コマンド受信")
        self._emit_event(DialogueEvent(event_type="status", data={"message": "対話初期化中"}))
        self._reset_state()
        self._drain(stt_event_queue)
        self._drain(dialbb_request_queue)
        self._drain(dialbb_response_queue)
        self._drain(tts_result_queue)
        if tts_cancel_queue is not None:
            self._drain(tts_cancel_queue)
        conversation_active_event.set()
        stt_enabled_event.set()
        logger.info("[CORE] CORE->DialBB 初期化要求送信")
        self._emit_event(DialogueEvent(event_type="status", data={"message": "システム応答待ち"}))
        dialbb_request_queue.put(
            DialbbRequest(session_id="", user_text="", is_initial=True)
        )

    def process_end_command(
        self,
        stt_event_queue: Queue,
        dialbb_request_queue: Queue,
        dialbb_response_queue: Queue,
        tts_request_queue: Queue,
        tts_result_queue: Queue,
        conversation_active_event: Event,
        stt_enabled_event: Event,
        tts_cancel_queue: Optional[Queue] = None,
    ) -> None:
        """対話終了コマンドを処理"""
        logger.info("[CORE] end コマンド受信")
        self._emit_event(DialogueEvent(event_type="status", data={"message": "待機中"}))
        if tts_cancel_queue is not None:
            tts_cancel_queue.put("cancel")
        stt_enabled_event.clear()
        conversation_active_event.clear()
        self._reset_state()
        self._drain(stt_event_queue)
        self._drain(dialbb_request_queue)
        self._drain(dialbb_response_queue)
        self._drain(tts_request_queue)
        self._drain(tts_result_queue)

    def process_stt_event(
        self,
        stt_event: RecognitionEvent,
        conversation_active_event: Event,
        dialbb_request_queue: Queue,
        tts_cancel_queue: Optional[Queue] = None,
    ) -> None:
        """STT イベントを処理"""
        if not conversation_active_event.is_set():
            return

        if stt_event.event_type == RecognitionEventType.SPEECH_STARTED:
            logger.debug("[CORE] 音声区間開始")
            self.user_speaking = True
            self._emit_event(DialogueEvent(event_type="status", data={"message": "音声認識中"}))

        elif stt_event.event_type == RecognitionEventType.SPEECH_ENDED:
            logger.debug("[CORE] 音声区間終了")
            self.user_speaking = False

        elif stt_event.event_type == RecognitionEventType.PARTIAL_TRANSCRIPT:
            logger.debug("[CORE] 認識中... %s", stt_event.text)
            self._emit_event(DialogueEvent(event_type="status", data={"message": "音声認識中"}))
            logger.debug("[CORE] STT->CORE system_speaking: %s, is_final_response: %s, tts_cancel_queue: %s, _barge_in_sent: %s", self.system_speaking, self.is_final_response, tts_cancel_queue, self._barge_in_sent)
            if (
                self.system_speaking
                and not self.is_final_response
                and tts_cancel_queue is not None
                and not self._barge_in_sent
            ):
                tts_cancel_queue.put("cancel")
                self._barge_in_sent = True
                logger.info("[CORE] CORE->TTS cancel 送信（★barge-in）")

        elif stt_event.event_type == RecognitionEventType.FINAL_TRANSCRIPT:
            text = stt_event.text.strip()
            logger.info("[CORE] STT->CORE final: ★ %s", text)
            self._emit_event(DialogueEvent(event_type="status", data={"message": "応答生成中"}))
            self.user_speaking = False
            self.user_waiting = False
            self.user_wait_start_time = None
            aux_data: dict = (
                {"barge_in": True} if (self.system_speaking and not self.is_final_response) else {}
            )
            logger.info("[CORE] CORE->DialBB 発話要求送信")
            dialbb_request_queue.put(
                DialbbRequest(
                    session_id=self.session_id,
                    user_text=text,
                    aux_data=aux_data,
                )
            )
            if aux_data:
                logger.debug("[CORE] DialBB aux_data=%s", aux_data)
            if tts_cancel_queue is not None and not self.is_final_response:
                tts_cancel_queue.put("cancel")
                logger.debug("[CORE] CORE->TTS cancel 冪等送信")
            self._emit_event(DialogueEvent(event_type="chat", data={"role": "user", "text": text}))

        elif stt_event.event_type == RecognitionEventType.ERROR:
            logger.error("[CORE][STT ERROR] %s", stt_event.text)
            self._emit_event(
                DialogueEvent(event_type="error", data={"source": "STT", "message": stt_event.text})
            )

    def process_dialbb_response(
        self,
        dialbb_response: DialbbResponse,
        conversation_active_event: Event,
        tts_request_queue: Queue,
        stt_enabled_event: Event,
    ) -> None:
        """DialBB 応答を処理"""
        logger.info("[CORE] CORE<-DialBB 応答受信")
        logger.debug("[CORE] DialBB応答: %s", dialbb_response.system_text)
        self.session_id = dialbb_response.session_id
        if dialbb_response.is_final:
            self.is_final_response = True
            logger.info("[CORE] DialBB 最終応答を受信（対話終了予定）")

        if not conversation_active_event.is_set():
            logger.debug("[CORE] 対話停止中のため DialBB 応答を破棄します。")
            return

        if self.user_speaking and self.system_speaking:
            logger.debug("[CORE] バージイン中のため DialBB 応答を無視します。")
            return

        system_text = dialbb_response.system_text.strip()
        if not system_text:
            logger.info("[CORE] DialBB空応答: ユーザ発話待ちへ遷移")
            self._emit_event(DialogueEvent(event_type="status", data={"message": "音声入力待ち"}))
            self.user_waiting = True
            self.user_wait_start_time = time.monotonic()
            if not self.is_final_response:
                stt_enabled_event.set()
            return

        self.system_speaking = True
        self._emit_event(DialogueEvent(event_type="chat", data={"role": "system", "text": system_text}))
        logger.info("[CORE] CORE->TTS 合成要求送信. system_speaking=%s, is_final_response=%s", self.system_speaking, self.is_final_response)
        self._emit_event(DialogueEvent(event_type="status", data={"message": "音声合成中"}))
        tts_request_queue.put(TtsRequest(session_id=self.session_id, text=system_text))
        if self.is_final_response:
            logger.debug("[CORE] 最終応答再生中: 新規 STT 入力を無効化")
            stt_enabled_event.clear()

    def process_tts_result(
        self,
        tts_result: TtsResult,
        conversation_active_event: Event,
        stt_enabled_event: Event,
    ) -> None:
        """TTS 完了を処理"""
        logger.info("[CORE] CORE<-TTS 結果受信")
        if tts_result.completed:
            logger.info("[CORE] システム発話終了")
            self.system_speaking = False
            self._barge_in_sent = False

            if self.is_final_response:
                logger.info("[CORE] 最終応答の再生完了：対話終了に遷移")
                self._emit_event(DialogueEvent(event_type="status", data={"message": "対話終了"}))
                self._emit_event(DialogueEvent(event_type="final"))
                self._reset_state()
                conversation_active_event.clear()
            else:
                self._emit_event(DialogueEvent(event_type="status", data={"message": "音声入力待ち"}))
                self.user_waiting = True
                self.user_wait_start_time = time.monotonic()
                stt_enabled_event.set()
        else:
            logger.info("[CORE] システム発話中断またはエラー")
            logger.debug("[CORE] TTS結果詳細: %s", tts_result.text)
            if conversation_active_event.is_set():
                self._emit_event(DialogueEvent(event_type="status", data={"message": "音声入力待ち"}))
            self.system_speaking = False
            self._barge_in_sent = False

    def check_user_wait_timeout(
        self,
        conversation_active_event: Event,
        dialbb_request_queue: Queue,
        max_user_wait_time: float,
    ) -> None:
        """ユーザ発話待ちタイムアウトをチェック"""
        if (
            self.user_waiting
            and self.user_wait_start_time is not None
            and conversation_active_event.is_set()
            and not self.user_speaking
        ):
            elapsed_wait = time.monotonic() - self.user_wait_start_time
            if elapsed_wait > max_user_wait_time:
                logger.info("[CORE] CORE->DialBB user_silence 送信")
                logger.debug("[CORE] ユーザ発話待ちタイムアウト %.1f 秒", elapsed_wait)
                self._emit_event(
                    DialogueEvent(
                        event_type="status",
                        data={"message": "応答生成中（無音タイムアウト）"},
                    )
                )
                dialbb_request_queue.put(
                    DialbbRequest(
                        session_id=self.session_id,
                        user_text="user_silence",
                        is_initial=False,
                    )
                )
                self.user_waiting = False
                self.user_wait_start_time = None

    def run(
        self,
        stt_event_queue: Queue,
        dialbb_request_queue: Queue,
        dialbb_response_queue: Queue,
        tts_request_queue: Queue,
        tts_result_queue: Queue,
        conversation_active_event: Event,
        stt_enabled_event: Event,
        stop_event: Event,
        command_queue: Queue,
        tts_cancel_queue: Optional[Queue] = None,
        loop_period: float = 0.1,
        max_user_wait_time: float = 30.0,
    ) -> None:
        """メインループ（既存 MultimodalMainModule.run と同じロジック）"""
        logger.info("[CORE] run start: thread=%s", threading.current_thread().name)
        try:
            while not stop_event.is_set():
                loop_start = time.monotonic()

                # 1. コマンド処理
                try:
                    cmd = command_queue.get_nowait()
                    if cmd == "start":
                        self.process_start_command(
                            stt_event_queue,
                            dialbb_request_queue,
                            dialbb_response_queue,
                            tts_request_queue,
                            tts_result_queue,
                            conversation_active_event,
                            stt_enabled_event,
                            tts_cancel_queue,
                        )
                    elif cmd == "end":
                        self.process_end_command(
                            stt_event_queue,
                            dialbb_request_queue,
                            dialbb_response_queue,
                            tts_request_queue,
                            tts_result_queue,
                            conversation_active_event,
                            stt_enabled_event,
                            tts_cancel_queue,
                        )
                except Empty:
                    pass

                # 2. STT イベント処理
                while True:
                    try:
                        stt_event = stt_event_queue.get_nowait()
                    except Empty:
                        break
                    self.process_stt_event(
                        stt_event,
                        conversation_active_event,
                        dialbb_request_queue,
                        tts_cancel_queue,
                    )

                # 3. DialBB 応答処理
                while True:
                    try:
                        dialbb_response = dialbb_response_queue.get_nowait()
                    except Empty:
                        break
                    self.process_dialbb_response(
                        dialbb_response,
                        conversation_active_event,
                        tts_request_queue,
                        stt_enabled_event,
                    )

                # 4. TTS 完了処理
                while True:
                    try:
                        tts_result = tts_result_queue.get_nowait()
                    except Empty:
                        break
                    self.process_tts_result(
                        tts_result,
                        conversation_active_event,
                        stt_enabled_event,
                    )

                # 5. ユーザ発話待ちタイムアウト
                self.check_user_wait_timeout(
                    conversation_active_event,
                    dialbb_request_queue,
                    max_user_wait_time,
                )

                # ループ周期制御
                loop_end = time.monotonic()
                sleep_time = max(0, loop_period - (loop_end - loop_start))
                if sleep_time > 0:
                    time.sleep(sleep_time)
        finally:
            logger.info(
                "[CORE] run exit: thread=%s session_id=%s stop_event=%s active=%s system_speaking=%s user_waiting=%s",
                threading.current_thread().name,
                self.session_id,
                stop_event.is_set(),
                conversation_active_event.is_set(),
                self.system_speaking,
                self.user_waiting,
            )
