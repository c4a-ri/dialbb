import re
from queue import Empty, Queue
from threading import Event
from typing import Optional

from dialbb.util.logger import get_logger
from mm_client.main.messages import (
    DialbbRequest,
    DialbbResponse,
    RecognitionEvent,
    RecognitionEventType,
    TtsRequest,
    TtsResult,
)


logger = get_logger(__name__)


class MultimodalMainModule:
    """Main module worker that mediates modules via queues."""

    def __init__(self, session_id: str = "phase1-session") -> None:
        self.session_id = session_id
        self.final_transcripts: list[str] = []

    def run(
        self,
        stt_event_queue: "Queue[RecognitionEvent]",
        dialbb_request_queue: "Queue[DialbbRequest]",
        dialbb_response_queue: "Queue[DialbbResponse]",
        tts_request_queue: "Queue[TtsRequest]",
        tts_result_queue: "Queue[TtsResult]",
        conversation_active_event: Event,
        stt_enabled_event: Event,
        stop_event: Event,
        chat_queue: Optional[Queue] = None,
    ) -> None:
        while not stop_event.is_set():
            # 1) DialBB から届いた応答を取り出して TTS へ流す。
            self._process_dialbb_responses(
                dialbb_response_queue=dialbb_response_queue,
                tts_request_queue=tts_request_queue,
                conversation_active_event=conversation_active_event,
                stt_enabled_event=stt_enabled_event,
                chat_queue=chat_queue,
            )
            # 2) TTS 完了通知を取り出して状態を更新（現状はログのみ）。
            self._process_tts_results(
                tts_result_queue=tts_result_queue,
                conversation_active_event=conversation_active_event,
                stt_enabled_event=stt_enabled_event,
            )

            try:
                # 3) STT イベントを待つ。timeout で定期的に stop_event を確認する。
                stt_event = stt_event_queue.get(timeout=0.1)
            except Empty:
                # STT 側から未着なら次ループへ。
                continue

            # 4) STT イベント内容に応じて対話要求送信/終了判定を行う。
            should_stop = self._handle_stt_event(
                event=stt_event,
                dialbb_request_queue=dialbb_request_queue,
                conversation_active_event=conversation_active_event,
                stt_enabled_event=stt_enabled_event,
                chat_queue=chat_queue,
            )
            if should_stop:
                # 5) 終了条件を満たしたため全スレッドへ停止を通知。
                stop_event.set()

    def _handle_stt_event(
        self,
        event: RecognitionEvent,
        dialbb_request_queue: "Queue[DialbbRequest]",
        conversation_active_event: Event,
        stt_enabled_event: Event,
        chat_queue: Optional[Queue] = None,
    ) -> bool:
        if not conversation_active_event.is_set() or not stt_enabled_event.is_set():
            # 対話停止中または音声入力停止中は STT イベントを破棄する。
            return False

        if event.event_type == RecognitionEventType.SPEECH_STARTED:
            # VAD 由来の発話開始通知。
            logger.info("[MAIN] 発話開始")
            return False

        if event.event_type == RecognitionEventType.SPEECH_ENDED:
            # VAD 由来の発話終了通知。
            logger.info("[MAIN] 発話終了")
            return False

        if event.event_type == RecognitionEventType.PARTIAL_TRANSCRIPT:
            # 中間結果は画面更新のみで、対話要求はまだ送らない。
            logger.info("認識中... %s", event.text)
            return False

        if event.event_type == RecognitionEventType.FINAL_TRANSCRIPT:
            text = event.text.strip()
            self.final_transcripts.append(text)
            logger.info("[MAIN] 確定結果: %s", text)

            # チャット表示用キューへユーザー発話を投入する。
            if chat_queue is not None:
                chat_queue.put(("user", text))

            # 終了ワードを検知したら stop_event を立てる。
            if re.search(r"\b(終了|ストップ|おしまい)\b", text, re.I):
                logger.info("[MAIN] 終了コマンドを検知。対話を停止します。")
                conversation_active_event.clear()
                stt_enabled_event.clear()
                return False

            # 終了でなければ DialBB へ問い合わせを送る。
            dialbb_request_queue.put(
                DialbbRequest(session_id=self.session_id, user_text=text)
            )
            return False

        if event.event_type == RecognitionEventType.ERROR:
            # STT エラーは対話を停止するが、アプリ全体は終了しない。
            logger.error("[MAIN][ERROR] %s", event.text)
            conversation_active_event.clear()
            stt_enabled_event.clear()
            return False

        return False

    def _process_dialbb_responses(
        self,
        dialbb_response_queue: "Queue[DialbbResponse]",
        tts_request_queue: "Queue[TtsRequest]",
        conversation_active_event: Event,
        stt_enabled_event: Event,
        chat_queue: Optional[Queue] = None,
    ) -> None:
        # キューが空になるまで処理し、応答を TTS キューへ橋渡しする。
        while True:
            try:
                dialbb_response = dialbb_response_queue.get_nowait()
            except Empty:
                return

            logger.info("[MAIN] DialBB応答: %s", dialbb_response.system_text)
            # DialBB 側で払い出された session_id を採用して以降の要求に使う。
            self.session_id = dialbb_response.session_id
            # チャット表示用キューへシステム応答を投入する。
            if chat_queue is not None and dialbb_response.system_text.strip():
                chat_queue.put(("system", dialbb_response.system_text.strip()))
            if not conversation_active_event.is_set():
                logger.info("[MAIN] 対話停止中のため DialBB 応答を破棄します。")
                continue
            if not dialbb_response.system_text.strip():
                logger.info("[MAIN] DialBB応答テキストが空のため、TTSへは送らず待機します。")
                stt_enabled_event.set()
                continue
            # TTS 再生中はマイク入力を一時停止し、ハウリング混入を防ぐ。
            stt_enabled_event.clear()
            # DialBB のテキスト応答を、そのまま TTS 要求へ変換する。
            tts_request_queue.put(
                TtsRequest(
                    session_id=dialbb_response.session_id,
                    text=dialbb_response.system_text,
                )
            )

    def _process_tts_results(
        self,
        tts_result_queue: "Queue[TtsResult]",
        conversation_active_event: Event,
        stt_enabled_event: Event,
    ) -> None:
        # 完了通知を取り出してログ出力する。
        while True:
            try:
                tts_result = tts_result_queue.get_nowait()
            except Empty:
                return

            if tts_result.completed:
                # 現状は完了ログのみ。必要ならここで UI 更新等を行う。
                logger.info("[MAIN] 音声合成完了: %s", tts_result.text)
                if conversation_active_event.is_set():
                    # 対話中のみ、合成完了後にマイク入力を再開する。
                    stt_enabled_event.set()
